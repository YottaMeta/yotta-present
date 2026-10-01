# -*- coding: utf-8 -*-
"""test_yotta_card.py — 元呈（yotta-present）R3 SVG 整卡自测套件（v0.7.0）。

覆盖：三形态 × 明暗主题 / 4 场景模板 / 确定性折行（不溢出）/ XML 转义 /
可编辑结构自检（text-as-text + 语义 id + 无脚本外链）/ 品牌 token（色 / logo / 拒绝面）/
present() 集成与保真降级 / CLI（--svg / --json / --list-cards / 错误路径）/ MCP。

运行：python scripts/test_yotta_card.py
说明：本测试只在本地生成临时文件，不联网、不依赖其它库。
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import yotta_card as ycard  # noqa: E402
import yotta_present as yp  # noqa: E402
import yotta_present_mcp as m  # noqa: E402

PASS = 0
FAIL = 0
FAILED = []

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

SAMPLE_CONCLUSION = {
    "title": "元呈 0.7.0 发布",
    "grade": "success",
    "verdict": "全链收口，候选零漂移",
    "bullets": ["R3 三形态开源", "可编辑 SVG"],
    "metrics": [{"label": "回归", "value": 233, "unit": "项"}, {"label": "下载", "value": 2182, "unit": "次", "tone": "up"}],
    "notes": ["示例数据"],
}
SAMPLE_METRICS = {
    "title": "本周数据快报",
    "metrics": [{"label": "新增安装", "value": 186, "unit": "次", "tone": "up"},
                {"label": "活跃技能", "value": 27, "unit": "个"}],
}
SAMPLE_TABLE = {
    "title": "方案对比",
    "headers": ["维度", "方案 A", "方案 B"],
    "rows": [["部署", "本地零依赖", "需云服务"], ["成本", "免费", "按次计费"]],
}


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok  %s" % name)
    else:
        FAIL += 1
        FAILED.append(name)
        print("  FAIL %s  %s" % (name, detail))


def _card_raises(fn):
    try:
        fn()
        return False
    except ycard.CardError:
        return True
    except Exception:  # noqa: BLE001
        return True


def _present_raises(fn):
    try:
        fn()
        return False
    except yp.PresentError:
        return True
    except Exception:  # noqa: BLE001
        return True


def _run_cli(args, inp=None):
    script = str(_HERE / "yotta_present.py")
    py = yp._resolve_test_python()
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run([py, script] + args, input=inp, capture_output=True,
                          text=True, encoding="utf-8", env=env, timeout=60)


def run_constants():
    print("== v0.7.0 R3 常量与模板 ==")
    check("R3_FORMS = 3", tuple(ycard.R3_FORMS) == ("conclusion", "metrics", "table"))
    check("CARDS 4 个", set(ycard.CARDS) == {"release", "weekly", "compare", "risk"}, str(sorted(ycard.CARDS)))
    check("等级文案与 GRADE_META 对齐",
          all(ycard.GRADE_TEXT.get(k) == v["text"] for k, v in yp.GRADE_META.items()))
    check("模板 form 合法", all(t.get("form") in ycard.R3_FORMS for t in ycard.CARDS.values()))


def run_render():
    print("== v0.7.0 R3 三形态 × 明暗主题 ==")
    samples = {"conclusion": SAMPLE_CONCLUSION, "metrics": SAMPLE_METRICS, "table": SAMPLE_TABLE}
    heights = {}
    for form, content in samples.items():
        for theme in ("light", "dark"):
            meta = ycard.render(form, content, theme=theme)
            svg = meta["svg"]
            ok, problems = ycard.check_editable(svg)
            check("%s/%s 结构自检" % (form, theme), ok, str(problems))
            try:
                ElementTree.fromstring(svg)
                xml_ok = True
            except ElementTree.ParseError:
                xml_ok = False
            check("%s/%s XML 合法" % (form, theme), xml_ok)
            check("%s/%s 文本可编辑（<text>/<tspan>）" % (form, theme),
                  "<text" in svg and "<tspan" in svg and "<path" not in svg)
            check("%s/%s 语义分层 id" % (form, theme),
                  all(('id="%s"' % i) in svg for i in ("card-header", "card-body", "card-title")))
            check("%s/%s data URI" % (form, theme), meta["data_uri"].startswith("data:image/svg+xml;base64,"))
            heights[(form, theme)] = meta["height"]
    check("light 背景 token", 'fill="#ffffff"' in ycard.render("conclusion", SAMPLE_CONCLUSION)["svg"])
    check("dark 背景 token", 'fill="#1E2329"' in ycard.render("conclusion", SAMPLE_CONCLUSION, theme="dark")["svg"])
    check("高度随内容变化", heights[("metrics", "light")] != heights[("table", "light")])
    check("未知形态拒绝", _card_raises(lambda: ycard.render("report", {"title": "t"})))


def run_templates():
    print("== v0.7.0 R3 场景模板 ==")
    cases = [("release", "conclusion", SAMPLE_CONCLUSION),
             ("weekly", "metrics", SAMPLE_METRICS),
             ("compare", "table", SAMPLE_TABLE),
             ("risk", "conclusion", {"title": "风险报告", "grade": "danger", "verdict": "2 项高危",
                                      "rows": [["项", "等级"], ["明文口令", "高"]]})]
    for slug, form, content in cases:
        meta = ycard.render(form, content, card=slug)
        check("%s 模板生效" % slug, meta["template"] == slug and meta["form"] == form)
        check("%s 结构自检" % slug, ycard.check_editable(meta["svg"])[0])
    weekly = ycard.render("metrics", SAMPLE_METRICS, card="weekly")["svg"]
    check("weekly kicker/title 默认值", "WEEKLY" in weekly and "数据快报" in weekly)
    check("未知模板拒绝", _card_raises(lambda: ycard.render("conclusion", SAMPLE_CONCLUSION, card="nope")))


def run_wrap():
    print("== v0.7.0 R3 确定性折行 ==")
    lines, trunc = ycard.wrap_text("超长中文标题" * 20, 200, 16, max_lines=3)
    check("CJK 折行不超宽", all(ycard.text_width(l, 16) <= 200 + 1e-6 for l in lines), str([ycard.text_width(l, 16) for l in lines]))
    check("折行截断加省略号", trunc and lines[-1].endswith("…"))
    lines2, _ = ycard.wrap_text("Supercalifragilisticexpialidocious" * 4, 120, 12, max_lines=2)
    check("英文长词不超宽", all(ycard.text_width(l, 12) <= 120 + 1e-6 for l in lines2))
    meta = ycard.render("conclusion", {"title": "标题" * 40, "verdict": "结论" * 60})
    check("超长标题/结论多行渲染", meta["svg"].count("</tspan>") > 3)
    check("超长渲染仍合法", ycard.check_editable(meta["svg"])[0])


def run_escape():
    print("== v0.7.0 R3 XML 转义与自检 ==")
    evil = "</text><script>alert(1)</script>"
    meta = ycard.render("table", {"title": evil, "rows": [[evil, "<b>x</b>"], ["a", "b"]]})
    svg = meta["svg"]
    check("无裸 <script>", "<script" not in svg.lower())
    check("尖括号已转义", "&lt;/text&gt;" in svg and "&lt;b&gt;" in svg)
    check("转义后自检通过", ycard.check_editable(svg)[0])
    ontext = ycard.render("conclusion", {"title": "x", "verdict": " onerror=alert(1) 与 onclick= 说明"})["svg"]
    check("正文 on* 字样不误报", ycard.check_editable(ontext)[0])
    bad_ok, bad_problems = ycard.check_editable('<svg id="r3-card"><script>x</script><g id="card-header"/><g id="card-body"/><text id="card-title">t</text></svg>')
    check("自检能抓 script", (not bad_ok) and any("script" in p for p in bad_problems))


def run_brand():
    print("== v0.7.0 R3 品牌 token ==")
    with tempfile.TemporaryDirectory(prefix="yotta-card-brand-") as tmp:
        png = Path(tmp) / "logo.png"
        png.write_bytes(PNG_1PX)
        brand = Path(tmp) / "brand.json"
        brand.write_text(json.dumps({"name": "示例品牌", "primary": "#123456", "accent": "#22B8A6",
                                     "footer": "示例品牌 · 页脚", "logo": "logo.png"}, ensure_ascii=False),
                         encoding="utf-8")
        meta = ycard.render("conclusion", SAMPLE_CONCLUSION, card="release", brand=str(brand))
        svg = meta["svg"]
        check("logo 内嵌 data URI", 'href="data:image/png;base64,' in svg)
        check("品牌 footer 渲染", 'id="card-footer-text"' in svg and "示例品牌 · 页脚" in svg)
        check("品牌主色生效", "#123456" in svg)
        check("品牌 accent 生效（kicker）", "#22b8a6" in svg or "#22B8A6" in svg)
        check("品牌卡结构自检", ycard.check_editable(svg)[0])

        mono = Path(tmp) / "mono.json"
        mono.write_text(json.dumps({"name": "元阁"}, ensure_ascii=False), encoding="utf-8")
        check("无 logo 用 monogram", 'id="card-brand-monogram"' in ycard.render("conclusion", SAMPLE_CONCLUSION, brand=str(mono))["svg"])

        bom = Path(tmp) / "bom.json"
        bom.write_text("\ufeff" + json.dumps({"name": "BOM 品牌"}, ensure_ascii=False), encoding="utf-8")
        check("品牌文件容忍 UTF-8 BOM", "BOM 品牌" in ycard.render("conclusion", SAMPLE_CONCLUSION, brand=str(bom))["svg"])

        svg_logo = Path(tmp) / "logo.svg"
        svg_logo.write_text("<svg/>", encoding="utf-8")
        svg_brand = Path(tmp) / "svg-logo.json"
        svg_brand.write_text(json.dumps({"logo": "logo.svg"}), encoding="utf-8")
        check("SVG logo 拒绝", _card_raises(lambda: ycard.render("conclusion", SAMPLE_CONCLUSION, brand=str(svg_brand))))

        big = Path(tmp) / "big.png"
        big.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 300000)
        big_brand = Path(tmp) / "big.json"
        big_brand.write_text(json.dumps({"logo": "big.png"}), encoding="utf-8")
        check("超大 logo 拒绝", _card_raises(lambda: ycard.render("conclusion", SAMPLE_CONCLUSION, brand=str(big_brand))))

        bad_color = Path(tmp) / "bad-color.json"
        bad_color.write_text('{"primary": "red"}', encoding="utf-8")
        check("坏色值拒绝", _card_raises(lambda: ycard.render("conclusion", SAMPLE_CONCLUSION, brand=str(bad_color))))

        unknown = Path(tmp) / "unknown.json"
        unknown.write_text(json.dumps({"name": "x", "nope": 1}), encoding="utf-8")
        meta_u = ycard.render("conclusion", SAMPLE_CONCLUSION, brand=str(unknown))
        check("未知字段进 warnings", any("nope" in w for w in meta_u["brand_warnings"]))

        missing = Path(tmp) / "missing.json"
        check("品牌文件不存在友好报错", _card_raises(lambda: ycard.render("conclusion", SAMPLE_CONCLUSION, brand=str(missing))))


def run_integration():
    print("== v0.7.0 R3 present() 集成 ==")
    r = yp.present(SAMPLE_CONCLUSION, channel="r3", form="conclusion", card="release")
    check("channel=r3", r.get("channel") == "r3")
    check("card meta 含 svg", bool(r.get("card", {}).get("svg")))
    check("未触发降级", r.get("fallback") is None, str(r.get("fallback")))
    check("markdown 含整卡图", "![元呈 0.7.0 发布](" in r["markdown"])
    check("markdown 保留可复制文本", "全链收口，候选零漂移" in r["markdown"])
    check("text 含整卡行", "整卡（R3 · conclusion）" in r["text"])
    check("保真校验通过", r["fidelity"]["content_preserved"] and r["fidelity"]["requested_form_preserved"])

    rm = yp.present(SAMPLE_METRICS, channel="r3", card="weekly")
    check("无 --form 时按模板出卡", rm["form"] == "metrics" and rm["card"]["template"] == "weekly")
    check("weekly markdown 含指标表", "新增安装" in rm["markdown"] and "186" in rm["markdown"])

    check("R3 不支持形态报错", _present_raises(lambda: yp.present({"title": "t"}, channel="r3", form="report")))
    check("R3 metrics 缺数据报错", _present_raises(lambda: yp.present({"title": "t"}, channel="r3", form="metrics")))
    check("R3 table 缺数据报错", _present_raises(lambda: yp.present({"title": "t"}, channel="r3", form="table")))
    check("--card 需 R3", _present_raises(lambda: yp.present(SAMPLE_CONCLUSION, card="release")))
    check("--brand 需 R3", _present_raises(lambda: yp.present(SAMPLE_CONCLUSION, brand="x.json")))
    check("R3 与 --template 不兼容", _present_raises(lambda: yp.present(SAMPLE_CONCLUSION, channel="r3", template="faq")))
    check("R2 仍拒绝", _present_raises(lambda: yp.present({"title": "t"}, channel="r2")))

    mixed = {"title": "t", "verdict": "v", "metrics": [{"label": "a", "value": 1}], "rows": [["x", "y"]]}
    rf = yp.present(mixed, channel="r3", form="conclusion")
    check("未承载内容触发保真降级", rf.get("fallback") is not None and rf["fidelity"]["content_preserved"])
    check("降级仍带整卡图", "![" in rf["markdown"] and bool(rf.get("card", {}).get("svg")))


def run_cli():
    print("== v0.7.0 R3 CLI ==")
    with tempfile.TemporaryDirectory(prefix="yotta-card-cli-") as tmp:
        svg_path = Path(tmp) / "card.svg"
        rc = _run_cli(["--content", json.dumps(SAMPLE_CONCLUSION, ensure_ascii=False),
                       "--channel", "r3", "--form", "conclusion", "--card", "release", "--svg", str(svg_path)])
        check("CLI r3 退出 0 且写出 SVG", rc.returncode == 0 and svg_path.is_file(), rc.stderr[:200])
        if svg_path.is_file():
            check("CLI 写出的 SVG 可编辑", ycard.check_editable(svg_path.read_text(encoding="utf-8"))[0])
        rcj = _run_cli(["--content", json.dumps(SAMPLE_METRICS, ensure_ascii=False),
                        "--channel", "r3", "--card", "weekly", "--json"])
        try:
            payload = json.loads(rcj.stdout)
        except ValueError:
            payload = {}
        check("--json 含 card.svg", bool(payload.get("card", {}).get("svg")), rcj.stdout[:200])
        rcl = _run_cli(["--list-cards"])
        check("--list-cards 列出 4 模板", rcl.returncode == 0 and all(k in rcl.stdout for k in ("release", "weekly", "compare", "risk")))
        rcb = _run_cli(["--content", '{"title": "t"}', "--card", "release"])
        check("--card 无 r3 退出 2", rcb.returncode == 2 and "仅用于 R3" in rcb.stderr)
        bad = Path(tmp) / "bad.json"
        bad.write_text('{"primary": "red"}', encoding="utf-8")
        rcbad = _run_cli(["--content", '{"title": "t", "verdict": "v"}', "--channel", "r3", "--brand", str(bad)])
        check("坏品牌文件退出 2 + 人话提示", rcbad.returncode == 2 and "品牌色" in rcbad.stderr)
        rc2 = _run_cli(["--content", '{"title": "t"}', "--channel", "r2"])
        check("r2 仍退出 2", rc2.returncode == 2 and "尚未开放" in rc2.stderr)


def run_mcp():
    print("== v0.7.0 R3 MCP ==")
    resp = m.handle_message({
        "jsonrpc": "2.0", "id": 70, "method": "tools/call",
        "params": {"name": "present_result", "arguments": {
            "content": json.dumps(SAMPLE_METRICS, ensure_ascii=False),
            "options": {"channel": "r3", "card": "weekly"},
        }},
    })
    payload = json.loads(resp["result"]["content"][0]["text"])
    check("MCP r3 无错误", resp["result"]["isError"] is False)
    check("MCP r3 返回 card.svg", bool(payload.get("card", {}).get("svg")))
    check("MCP r3 channel 回读", payload.get("channel") == "r3")
    check("MCP r3 markdown 可复制", "新增安装" in payload.get("markdown", ""))


def run():
    run_constants()
    run_render()
    run_templates()
    run_wrap()
    run_escape()
    run_brand()
    run_integration()
    run_cli()
    run_mcp()


if __name__ == "__main__":
    run()
    print("\n结果：%d 通过 / %d 失败" % (PASS, FAIL))
    if FAILED:
        print("失败项：%s" % ", ".join(FAILED))
        sys.exit(1)
    print("全部通过 ✓")
