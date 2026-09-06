# -*- coding: utf-8 -*-
"""test_yotta_chart.py — yotta-present（元呈）SVG 渲染内核自测套件。

覆盖：12 种图表渲染（SVG 骨架 / data URI / 文件写入）/ 参数归一化 / XML 转义
防注入 / 数值边界（空数据 / 全 0 / 负值）。

运行：python scripts/test_yotta_chart.py
说明：本测试只在本地生成临时 SVG，不联网、不依赖其它库。
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import yotta_chart as yc  # noqa: E402

PASS = 0
FAIL = 0
FAILED = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok  %s" % name)
    else:
        FAIL += 1
        FAILED.append(name)
        print("  FAIL %s  %s" % (name, detail))


def run():
    print("== 内核：常量与工具 ==")
    check("CHART_TYPES = 12", len(yc.CHART_TYPES) == 12, str(yc.CHART_TYPES))
    check("VERSION 存在", bool(yc.VERSION))
    check("转义 & < >", yc._e('&<>"\'') == "&amp;&lt;&gt;&quot;&apos;")
    check("nice ticks 有序", all(a < b for a, b in zip(yc._nice_ticks(0, 10), yc._nice_ticks(0, 10)[1:])))

    print("== 内核：12 种图表渲染 ==")
    tmpdir = tempfile.mkdtemp(prefix="yotta-present-test-")
    samples = {
        "bar": {"labels": ["A", "B", "C"], "data": [3, 5, 2]},
        "line": {"labels": ["A", "B", "C"], "data": [1, 4, 2]},
        "pie": {"labels": ["A", "B", "C"], "data": [3, 5, 2]},
        "radar": {"labels": ["x", "y", "z"], "data": [[4, 5, 3]]},
        "scatter": {"data": [[1, 2], [3, 4], [5, 1]]},
        "histogram": {"data": [1, 2, 2, 3, 3, 3, 4, 5]},
        "funnel": {"labels": ["a", "b", "c"], "data": [100, 40, 10]},
        "waterfall": {"data": [100, 20, -30, 90]},
        "word_cloud": {"data": [{"text": "安全", "weight": 9}, {"text": "本地", "weight": 3}]},
        "sankey": {"data": {"nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                            "links": [{"source": "a", "target": "b", "value": 5}]}},
        "spreadsheet": {"data": [["x", "y"], [1, 2]], "headers": ["列1", "列2"]},
        "treemap": {"data": [{"label": "甲", "value": 40}, {"label": "乙", "value": 10}]},
    }
    for c in yc.CHART_TYPES:
        params = dict(samples.get(c, {"data": [1, 2, 3]}))
        params.setdefault("title", "测试 " + c)
        r = yc.render(c, params)
        check("%s 渲染为 SVG" % c, r["svg"].startswith("<svg"))
        check("%s 有 data_uri" % c, r["data_uri"].startswith("data:image/svg+xml;base64,"))
        check("%s 无默认写文件" % c, r["path"] is None)
        out = os.path.join(tmpdir, c + ".svg")
        r2 = yc.render(c, dict(params, out=out))
        check("%s 写文件成功" % c, os.path.isfile(out) and os.path.getsize(out) > 200)
        with open(out, "r", encoding="utf-8") as f:
            head = f.read(3)
        check("%s 文件无 BOM" % c, head != "\ufeff")

    print("== 内核：参数归一化 / 边界 ==")
    check("data 字符串逗号拆分", yc.render("bar", {"data": "1,2,3"})["svg"].startswith("<svg"))
    check("data JSON 字符串", yc.render("pie", {"data": "[5,3]"})["svg"].startswith("<svg"))
    check("空数据不崩", yc.render("bar", {"data": []})["svg"].startswith("<svg"))
    check("全 0 不崩", yc.render("bar", {"data": [0, 0]})["svg"].startswith("<svg"))
    check("负值不崩", yc.render("waterfall", {"data": [10, -5, 5]})["svg"].startswith("<svg"))
    check("未知图表抛错", _raises(lambda: yc.render("nope", {})))
    check("宽度钳制", yc.render("bar", {"data": [1], "width": 99999})["width"] <= 2400)
    check("XML 注入被转义", "<script>" not in yc.render("bar", {"data": [1], "title": "<script>alert(1)</script>"})["svg"])

    print("== S7-M2 主题 token（色板 token 化）==")
    check("THEMES = light/dark", yc.THEMES == ["light", "dark"])
    check("light/dark 主题表齐", set(yc.THEME["themes"]) == {"light", "dark"})
    check("light/dark 色板表齐", set(yc.THEME["chart_palettes"]) == {"light", "dark"})
    check("PALETTES / DARK_PALETTES 5 套同名", set(yc.PALETTES) == set(yc.DARK_PALETTES) and len(yc.PALETTES) == 5)
    check("语义色名含 GRADE 四档 + neutral",
          {"success", "warn", "danger", "info", "neutral"} <= set(yc.THEME.get("semantic", {})))
    cok, _ = yc.check_contrast()
    check("WCAG 对比度自查全过 (>=4.5)", cok)
    r_light = yc.render("bar", {"labels": ["A", "B"], "data": [3, 5], "title": "t", "theme": "light"})
    check("light svg 白底", 'fill="#ffffff"' in r_light["svg"], r_light["svg"][:160])
    r_dark = yc.render("bar", {"labels": ["A", "B"], "data": [3, 5], "title": "t", "theme": "dark"})
    check("dark svg 深底", 'fill="#1E2329"' in r_dark["svg"], r_dark["svg"][:160])
    check("dark meta.theme", r_dark["meta"]["theme"] == "dark")
    check("dark 无残留占位符", not any(mk in r_dark["svg"] for mk in yc._T_MARKERS))
    r_unk = yc.render("bar", {"labels": ["A", "B"], "data": [3, 5], "theme": "bogus"})
    check("未知主题回退 light", r_unk["meta"]["theme"] == "light" and 'fill="#ffffff"' in r_unk["svg"])
    out = os.path.join(tmpdir, "dark-bar.svg")
    yc.render("bar", {"labels": ["A", "B"], "data": [3, 5], "theme": "dark", "out": out})
    with open(out, "r", encoding="utf-8") as f:
        svg_file = f.read()
    check("dark 写文件含深底", 'fill="#1E2329"' in svg_file)

    shutil.rmtree(tmpdir, ignore_errors=True)


def _raises(fn):
    try:
        fn()
        return False
    except Exception:  # noqa: BLE001
        return True


if __name__ == "__main__":
    run()
    print("\n结果：%d 通过 / %d 失败" % (PASS, FAIL))
    if FAILED:
        print("失败项：%s" % ", ".join(FAILED))
        sys.exit(1)
    print("全部通过 ✓")
