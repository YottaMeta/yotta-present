# -*- coding: utf-8 -*-
"""test_yotta_present.py — 元呈（yotta-present）呈现核心自测套件。

覆盖：标准内容对象归一化 / 8 形态渲染（Markdown + 纯文本）/ 确定性判断兜底 /
--form 显式指定 / 表格变体 / QA 解析 / 图表形态（本地 SVG + data URI）/
CLI（--file / --text / --both / --out / --json / --list-forms / 退出码）/
MCP（initialize / tools.list / tools.call / 错误路径 / stdio 端到端）。

运行：python scripts/test_yotta_present.py
说明：本测试只在本地生成临时 SVG / 文件，不联网、不依赖其它库。
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
import yotta_present as yp  # noqa: E402
import yotta_present_mcp as m  # noqa: E402

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


def _raises(fn):
    try:
        fn()
        return False
    except yp.PresentError:
        return True
    except Exception:  # noqa: BLE001
        return True


def _run_cli(args, inp=None):
    script = str(_HERE / "yotta_present.py")
    py = os.environ.get("YOTTA_TEST_PYTHON", sys.executable)
    return subprocess.run([py, script] + args, input=inp, capture_output=True,
                          text=True, encoding="utf-8", timeout=60)


def run():
    print("== 常量与工具 ==")
    check("VERSION 存在", bool(yp.VERSION))
    check("FORMS = 8", len(yp.FORMS) == 8, str(yp.FORMS))
    check("FORM_DESC 完整", all(f in yp.FORM_DESC for f in yp.FORMS))
    check("GRADE_META 4 级", set(yp.GRADE_META) == {"success", "warn", "danger", "info"})

    print("== 归一化 ==")
    d = yp.normalize_content({"title": 1, "verdict": 2})
    check("标量转字符串", d["title"] == "1" and d["verdict"] == "2")
    d2 = yp.normalize_content('{"title": "t", "bullets": ["a", 1]}')
    check("JSON 字符串归一", d2["title"] == "t" and d2["bullets"] == ["a", "1"])
    d3 = yp.normalize_content({"title": "x"}, title_override="覆盖")
    check("title 覆盖", d3["title"] == "覆盖")
    d4 = yp.normalize_content({"metrics": [{"label": "A", "value": 3.0}]})
    check("metrics 数值格式化", d4["metrics"][0]["value"] == "3")
    d5 = yp.normalize_content({"metrics": [{"label": "A", "value": 3.14159}]})
    check("metrics 浮点两位", d5["metrics"][0]["value"] == "3.14")
    check("metrics 缺 value 报错", _raises(lambda: yp.normalize_content({"metrics": [{"label": "A"}]})))
    check("metrics 非对象报错", _raises(lambda: yp.normalize_content({"metrics": ["x"]})))
    check("rows 非法项报错", _raises(lambda: yp.normalize_content({"rows": [123]})))
    check("bullets 非数组报错", _raises(lambda: yp.normalize_content({"bullets": "x"})))
    check("chart_data 非对象报错", _raises(lambda: yp.normalize_content({"chart_data": [1]})))
    check("空内容报错", _raises(lambda: yp.normalize_content("  ")))
    check("JSON 顶层非对象报错", _raises(lambda: yp.normalize_content("[1,2]")))
    check("坏 JSON 报错", _raises(lambda: yp.normalize_content("{bad")))
    txt = yp.normalize_content("# 标题\n\n> 头条\n\n- 要点一\n- 要点二\n\n第一段。\n第二段。")
    check("纯文本解析标题", txt.get("title") == "标题")
    check("纯文本解析头条", txt.get("headline") == "头条")
    check("纯文本解析要点", txt.get("bullets") == ["要点一", "要点二"])
    check("纯文本解析正文", len(txt.get("body", [])) == 2)
    chk = yp.normalize_content("- [x] 完成\n- [ ] 事项")
    check("复选框解析保留", chk["bullets"] == ["[x] 完成", "[ ] 事项"])

    print("== 确定性判断兜底 ==")
    def form_of(c):
        return yp.decide_form(yp.normalize_content(c))[0]
    check("chart_data → chart", form_of({"chart_data": {"chart": "bar", "data": [1, 2]}}) == "chart")
    check("rows+title+metrics → report", form_of({"title": "t", "rows": [[1, 2]], "metrics": [{"label": "a", "value": 1}]}) == "report")
    check("rows → table", form_of({"rows": [["a", "b"], [1, 2]]}) == "table")
    check("rows 键值对 → table", form_of({"rows": [["键", "值"], ["a", "b"]]}) == "table")
    check("rows QA → qa", form_of({"rows": [{"问题": "q", "回答": "a"}]}) == "qa")
    check("metrics+verdict → conclusion", form_of({"metrics": [{"label": "a", "value": 1}], "verdict": "v"}) == "conclusion")
    check("metrics 仅 → metrics", form_of({"metrics": [{"label": "a", "value": 1}, {"label": "b", "value": 2}]}) == "metrics")
    check("bullets QA → qa", form_of({"bullets": ["问：a", "答：b"]}) == "qa")
    check("bullets+headline → conclusion", form_of({"bullets": ["a"], "headline": "h"}) == "conclusion")
    check("bullets 仅 → checklist", form_of({"bullets": ["a", "b", "c"]}) == "checklist")
    check("body → prose", form_of({"body": ["一段文字"]}) == "prose")
    check("verdict 仅 → conclusion", form_of({"verdict": "v"}) == "conclusion")
    check("grade 仅 → conclusion", form_of({"grade": "warn"}) == "conclusion")
    check("title 仅 → prose", form_of({"title": "t"}) == "prose")
    check("空对象 → prose 兜底", form_of({}) == "prose")
    check("form 显式指定", form_of({"form": "report", "bullets": ["a"]}) == "report")
    check("form 非法报错", _raises(lambda: yp.decide_form({"form": "nope"})))


    print("== warnings / explain（问题反馈修复 P2/P4）==")
    rw1 = yp.present({"columns": ["a", "b"], "rows": [[1, 2]]})
    check("table columns 有 warning", any("columns" in w for w in rw1.get("warnings", [])), str(rw1.get("warnings")))
    rw2 = yp.present("结论文字\n\n- 点1", form="conclusion")
    check("conclusion Markdown 有 warning", any("grade / verdict" in w for w in rw2.get("warnings", [])), str(rw2.get("warnings")))
    rw3 = yp.present({"title": "t", "grade": "success", "verdict": "通过", "bullets": ["b1"]}, form="conclusion")
    check("正常 conclusion 无 warning", "warnings" not in rw3, str(rw3.get("warnings")))
    rq = yp.present({"rows": [{"a": 1}]}, form="qa")
    check("qa 非标准列有 warning", any("qa 的 rows" in w for w in rq.get("warnings", [])), str(rq.get("warnings")))
    re1 = yp.present({"title": "t", "grade": "success", "verdict": "通过"}, explain=True)
    check("explain 返回判型理由", isinstance(re1.get("explain"), list) and len(re1["explain"]) >= 1, str(re1.get("explain")))
    re2 = yp.present({"title": "t", "verdict": "v"})
    check("缺省 explain 不返回（CLI 语义保持）", "explain" not in re2, str(re2.get("explain")))

    c = {"title": "扫描结论", "grade": "success", "verdict": "未发现风险",
         "metrics": [{"label": "检测点", "value": 8, "unit": "项"}],
         "bullets": ["全部通过"], "notes": ["仅本机扫描"]}
    r = yp.present(c, explain=True)
    check("conclusion md 含标题", "# 扫描结论" in r["markdown"])
    check("conclusion md 含徽章", "🟢 **通过**" in r["markdown"])
    check("conclusion md 含指标表", "| 检测点 | 8 项 |" in r["markdown"])
    check("conclusion md 含要点", "- 全部通过" in r["markdown"])
    check("conclusion md 含注记", "> 注：仅本机扫描" in r["markdown"])
    check("conclusion text 无 #", "#" not in r["text"])
    check("conclusion text 含 [通过]", "[通过]" in r["text"])
    check("explain 返回判断原因", isinstance(r.get("explain"), list) and r["explain"])
    for g, emoji in (("warn", "🟡"), ("danger", "🔴"), ("info", "⚪")):
        rg = yp.present({"grade": g, "verdict": "x"})
        check("grade %s 徽章 %s" % (g, emoji), emoji in rg["markdown"])
    rc = yp.present({"grade": "AA", "verdict": "x"})
    check("自定义 grade 原文渲染", "**AA**" in rc["markdown"] and "🟢" not in rc["markdown"])
    rh = yp.present({"title": "t", "headline": "h"})
    check("无 verdict 时 headline 作结论", "> h" in rh["markdown"])

    print("== 形态渲染：table ==")
    t1 = yp.present({"title": "对比", "rows": [{"方案": "A", "成本": "低"}, {"方案": "B", "成本": "高"}]})
    check("对象表表头", "| 方案 | 成本 |" in t1["markdown"])
    check("对象表数据", "| A | 低 |" in t1["markdown"])
    t2 = yp.present({"rows": [["列1", "列2"], ["v1", "v2"]]})
    check("二维表首行作表头", "| 列1 | 列2 |" in t2["markdown"] and "| v1 | v2 |" in t2["markdown"])
    t3 = yp.present({"rows": [["键", "值"]]})
    check("键值对表头", "| 项 | 值 |" in t3["markdown"])
    t4 = yp.present({"rows": [[1, 2], [3, 4]], "headers": ["x", "y"]})
    check("显式表头", "| x | y |" in t4["markdown"])
    t5 = yp.present({"rows": [["a", "b|c"]]})
    check("表格单元格竖线转义", "b\\|c" in t5["markdown"])
    tt = yp.present({"title": "t", "rows": [["a", "b"], [1, 2]]}, form="table")
    check("table text 管道分隔", "a | b" in tt["text"])

    print("== 形态渲染：checklist / metrics / qa ==")
    cl = yp.present({"title": "清单", "bullets": ["[x] 完成", "[ ] 事项", "普通项"]})
    check("checklist 复选框保留", "[x] 完成" in cl["markdown"] and "[ ] 事项" in cl["markdown"])
    mt = yp.present({"title": "指标", "metrics": [{"label": "营收", "value": 100, "unit": "万", "tone": "up"},
                                                  {"label": "流失", "value": 2, "tone": "down"}]})
    check("metrics 箭头 up", "▲ 100 万" in mt["markdown"])
    check("metrics 箭头 down", "▼ 2" in mt["markdown"])
    q1 = yp.present({"title": "FAQ", "rows": [{"问题": "是什么", "回答": "呈现层"}]})
    check("qa rows 渲染", "**问：是什么**" in q1["markdown"] and "答：呈现层" in q1["markdown"])
    q2 = yp.present({"bullets": ["问：A？", "答：甲。", "问：B？", "答：乙。"]})
    check("qa bullets 渲染", "**问：A？**" in q2["markdown"] and "答：甲。" in q2["markdown"])
    q3 = yp.present({"bullets": ["Q: C?", "A: 丙."]})
    check("qa 英文前缀", "**问：C?**" in q3["markdown"] and "答：丙." in q3["markdown"])

    print("== 形态渲染：report ==")
    rep = {"title": "周报", "headline": "正常", "verdict": "整体正常",
           "metrics": [{"label": "任务", "value": 10}],
           "rows": [["项", "状态"], ["S3", "进行中"]],
           "bullets": ["下周校验"]}
    rr = yp.present(rep)
    check("report 含目录", "**目录**" in rr["markdown"] and "- 摘要" in rr["markdown"])
    check("report 含章节", "## 关键指标" in rr["markdown"] and "## 明细" in rr["markdown"])
    check("report 明细不重复标题", rr["markdown"].count("# 周报") == 1)
    check("report 明细表格", "| S3 | 进行中 |" in rr["markdown"])

    print("== 形态渲染：prose / chart ==")
    pr = yp.present({"title": "说明", "headline": "要点", "body": ["第一段。", "第二段。"]})
    check("prose 正文段落", "第一段。" in pr["markdown"] and "第二段。" in pr["markdown"])
    tmpdir = tempfile.mkdtemp(prefix="yotta-present-test-")
    svg_path = os.path.join(tmpdir, "trend.svg")
    ch = yp.present({"title": "趋势", "chart_data": {"chart": "line", "title": "访问趋势",
                                                     "labels": ["一", "二"], "data": [3, 5]}},
                    svg_out=svg_path)
    check("chart 形态判定", ch["form"] == "chart")
    check("chart 生成 SVG 文件", os.path.isfile(svg_path) and os.path.getsize(svg_path) > 200)
    check("chart md 含图片引用", "![访问趋势](%s)" % svg_path.replace("\\", "/").replace("//", "/") in ch["markdown"] or "![访问趋势]" in ch["markdown"])
    check("chart text 含生成信息", "已生成" in ch["text"])
    ch2 = yp.present({"chart_data": {"chart": "pie", "data": [1, 2]}})
    check("chart data URI 内嵌", "![pie](data:image/svg+xml;base64," in ch2["markdown"])
    check("chart 缺 chart_data 报错", _raises(lambda: yp.present({"title": "x"}, form="chart")))

    print("== CLI ==")
    r0 = _run_cli(["--list-forms"])
    check("CLI --list-forms 退出 0", r0.returncode == 0 and "conclusion" in r0.stdout)
    rv = _run_cli(["--version"])
    check("CLI --version 含版本", rv.returncode == 0 and yp.VERSION in rv.stdout)
    rc1 = _run_cli(["--content", '{"title": "t", "bullets": ["a"]}'])
    check("CLI --content 默认 md", rc1.returncode == 0 and "# t" in rc1.stdout and "- a" in rc1.stdout)
    rc2 = _run_cli(["--content", '{"title": "t", "bullets": ["a"]}', "--text"])
    check("CLI --text", rc2.returncode == 0 and "#" not in rc2.stdout)
    rc3 = _run_cli(["--content", '{"title": "t", "bullets": ["a"]}', "--json"])
    data3 = json.loads(rc3.stdout)
    check("CLI --json 完整结果", rc3.returncode == 0 and data3["form"] == "checklist" and "markdown" in data3)
    fpath = os.path.join(tmpdir, "input.json")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write('{"title": "文件输入", "rows": [["a", "b"]]}')
    rc4 = _run_cli(["--file", fpath])
    check("CLI --file", rc4.returncode == 0 and "文件输入" in rc4.stdout)
    rc5 = _run_cli(["--content", '{"title": "t", "bullets": ["a"]}', "--both"])
    check("CLI --both 双输出", rc5.returncode == 0 and "# t" in rc5.stdout and "---" in rc5.stdout)
    out_md = os.path.join(tmpdir, "out.md")
    rc6 = _run_cli(["--content", '{"title": "t", "bullets": ["a"]}', "--out", out_md, "--both"])
    check("CLI --out both 写两文件", rc6.returncode == 0 and os.path.isfile(out_md) and os.path.isfile(out_md[:-3] + ".txt"))
    rc7 = _run_cli(["--content", '{"title": "t", "bullets": ["a"]}', "--svg", os.path.join(tmpdir, "x.svg")])
    check("CLI --svg 非图表报错退出 2", rc7.returncode == 2 and "--svg" in rc7.stderr)
    rc8 = _run_cli(["--content", '{"form": "nope"}'])
    check("CLI 非法形态退出 2", rc8.returncode == 2)
    rc9 = _run_cli([])
    check("CLI 无输入退出 1", rc9.returncode == 1)
    rc10 = _run_cli(["--content", ""])
    check("CLI 空内容退出 1", rc10.returncode == 1)
    rc11 = _run_cli(["--content", '{"title": "图", "chart_data": {"chart": "bar", "data": [1, 2]}}', "--svg", svg_path])
    check("CLI --svg 图表写文件", rc11.returncode == 0 and os.path.isfile(svg_path))
    rc12 = _run_cli(["--content", "一段纯文本说明。\n\n第二段。", "--text"])
    check("CLI 纯文本输入 text", rc12.returncode == 0 and "一段纯文本说明。" in rc12.stdout)

    print("== MCP：initialize / tools.list / tools.call ==")
    init = m.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    check("initialize serverInfo", init["result"]["serverInfo"]["name"] == "yotta-present")
    tl = m.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    names = [t["name"] for t in tl["result"]["tools"]]
    check("tools.list 2 工具", len(names) == 2, str(names))
    check("含 present_result", "present_result" in names)
    check("含 present_forms", "present_forms" in names)
    resp = m.handle_message({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                             "params": {"name": "present_result",
                                        "arguments": {"content": '{"title": "t", "bullets": ["a"], "grade": "success"}'}}})
    check("present_result 非 error", resp["result"]["isError"] is False)
    text = json.loads(resp["result"]["content"][0]["text"])
    check("present_result 返回 markdown", text["form"] == "conclusion" and "# t" in text.get("markdown", ""))
    resp2 = m.handle_message({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                              "params": {"name": "present_result",
                                         "arguments": {"content": '{"title": "t", "bullets": ["a"]}',
                                                       "output": "text", "explain": True}}})
    t2 = json.loads(resp2["result"]["content"][0]["text"])
    check("present_result output=text+explain", t2["form"] == "checklist" and "text" in t2 and "explain" in t2 and "markdown" not in t2)
    resp3 = m.handle_message({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                              "params": {"name": "present_result",
                                         "arguments": {"content": '{"title": "图", "chart_data": {"chart": "pie", "data": [1, 2]}}',
                                                       "output": "json"}}})
    t3 = json.loads(resp3["result"]["content"][0]["text"])
    check("present_result chart json", t3["form"] == "chart" and "chart" in t3 and t3["chart"]["data_uri"].startswith("data:image/svg+xml;base64,"))
    resp4 = m.handle_message({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                              "params": {"name": "present_forms", "arguments": {}}})
    t4 = json.loads(resp4["result"]["content"][0]["text"])
    check("present_forms 8 形态", len(t4["forms"]) == 8)

    print("== MCP：错误路径 ==")
    e1 = m.handle_message({"jsonrpc": "2.0", "id": 20, "method": "tools/call",
                           "params": {"name": "present_result", "arguments": {}}})
    check("缺 content isError", e1["result"]["isError"] is True)
    e2 = m.handle_message({"jsonrpc": "2.0", "id": 21, "method": "tools/call",
                           "params": {"name": "present_result",
                                      "arguments": {"content": "x", "output": "nope"}}})
    check("output 非法 isError", e2["result"]["isError"] is True)
    e3 = m.handle_message({"jsonrpc": "2.0", "id": 22, "method": "tools/call",
                           "params": {"name": "present_result",
                                      "arguments": {"content": '{"form": "bad"}'}}})
    check("非法形态 isError", e3["result"]["isError"] is True)
    e4 = m.handle_message({"jsonrpc": "2.0", "id": 23, "method": "tools/call",
                           "params": {"name": "bogus", "arguments": {}}})
    check("未知工具 isError", e4["result"]["isError"] is True)
    e5 = m.handle_message({"jsonrpc": "2.0", "id": 24, "method": "bogus", "params": {}})
    check("未知 method -32601", e5["error"]["code"] == -32601)
    e6 = m.handle_message({"foo": 1})
    check("非 2.0 -32600", e6["error"]["code"] == -32600)
    e7 = m.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    check("通知不响应", e7 is None)

    print("== stdio 端到端 ==")
    script = str(_HERE / "yotta_present_mcp.py")
    payloads = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "present_result",
                    "arguments": {"content": '{"title": "端到端", "bullets": ["a", "b"]}'}}},
    ]
    inp = "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in payloads)
    py = os.environ.get("YOTTA_TEST_PYTHON", sys.executable)
    proc = subprocess.run([py, script], input=inp, capture_output=True, text=True, encoding="utf-8", timeout=60)
    check("stdio 子进程退出码 0", proc.returncode == 0, proc.stderr[:200])
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    check("stdio 产出 3 行", len(lines) == 3, "got %d" % len(lines))
    r1 = json.loads(lines[0])
    check("stdio initialize id=1", r1.get("id") == 1 and r1["result"]["serverInfo"]["name"] == "yotta-present")
    r2 = json.loads(lines[1])
    check("stdio tools/list 2", len(r2["result"]["tools"]) == 2)
    r3 = json.loads(lines[2])
    check("stdio tools/call 非 error", r3["result"]["isError"] is False)
    t3s = json.loads(r3["result"]["content"][0]["text"])
    check("stdio tools/call 返回标题", "# 端到端" in t3s.get("markdown", ""))

    shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    run()
    print("\n结果：%d 通过 / %d 失败" % (PASS, FAIL))
    if FAILED:
        print("失败项：%s" % ", ".join(FAILED))
        sys.exit(1)
    print("全部通过 ✓")
