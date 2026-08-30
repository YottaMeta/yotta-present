# -*- coding: utf-8 -*-
"""test_yotta_chart.py — yotta-chart（元图）自测套件。

覆盖：12 种图表渲染（SVG 骨架 / data URI / 文件写入）/ 参数归一化 / XML 转义
防注入 / 数值边界（空数据 / 全 0 / 负值）/ MCP initialize / tools.list /
tools.call 12 工具 / 未知 method / 未知 tool / 错误入参 / stdio 端到端。

运行：python scripts/test_yotta_chart.py
说明：本测试只在本地生成临时 SVG，不联网、不依赖外部库。
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
import yotta_chart_mcp as m  # noqa: E402

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
    tmpdir = tempfile.mkdtemp(prefix="yotta-chart-test-")
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

    print("== MCP：initialize / tools.list / tools.call ==")
    init = m.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    check("initialize 返回 serverInfo", init["result"]["serverInfo"]["name"] == "yotta-chart")
    tl = m.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    names = [t["name"] for t in tl["result"]["tools"]]
    check("tools.list 12 工具", len(names) == 12, str(names))
    check("工具命名 generate_*_chart", all(n.startswith("generate_") and n.endswith("_chart") for n in names))
    check("工具含 generate_pie_chart", "generate_pie_chart" in names)
    check("工具含 generate_treemap_chart", "generate_treemap_chart" in names)

    for c in yc.CHART_TYPES:
        args = dict(samples.get(c, {"data": [1, 2, 3]}))
        resp = m.handle_message({"jsonrpc": "2.0", "id": 10, "method": "tools/call",
                                 "params": {"name": "generate_%s_chart" % c, "arguments": args}})
        r = resp["result"]
        check("tools.call %s 非 error" % c, r.get("isError") is False, json.dumps(r)[:200])
        text = json.loads(r["content"][0]["text"])
        check("tools.call %s 返回 path+data_uri" % c, text.get("path") and text["data_uri"].startswith("data:image/svg+xml;base64,"))
        if text.get("temp_dir"):
            shutil.rmtree(text["temp_dir"], ignore_errors=True)

    print("== MCP：错误路径 ==")
    no_data = m.handle_message({"jsonrpc": "2.0", "id": 20, "method": "tools/call",
                                "params": {"name": "generate_bar_chart", "arguments": {}}})
    check("缺 data 返回 isError", no_data["result"]["isError"] is True)
    unknown_tool = m.handle_message({"jsonrpc": "2.0", "id": 21, "method": "tools/call",
                                     "params": {"name": "generate_foo_chart", "arguments": {"data": [1]}}})
    check("未知工具 isError", unknown_tool["result"]["isError"] is True)
    unknown_method = m.handle_message({"jsonrpc": "2.0", "id": 22, "method": "bogus", "params": {}})
    check("未知 method -32601", unknown_method["error"]["code"] == -32601)
    bad_jsonrpc = m.handle_message({"foo": 1})
    check("非 2.0 返回 -32600", bad_jsonrpc["error"]["code"] == -32600)
    notify = m.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    check("通知不响应", notify is None)

    print("== stdio 端到端 ==")
    script = str(_HERE / "yotta_chart_mcp.py")
    payloads = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "generate_pie_chart", "arguments": {"labels": ["a", "b"], "data": [3, 1]}}},
    ]
    inp = "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in payloads)
    py = os.environ.get("YOTTA_TEST_PYTHON", sys.executable)
    proc = subprocess.run([py, script], input=inp, capture_output=True, text=True, encoding="utf-8", timeout=60)
    check("stdio 子进程退出码 0", proc.returncode == 0, proc.stderr[:200])
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    check("stdio 产出 3 行", len(lines) == 3, "got %d" % len(lines))
    r1 = json.loads(lines[0])
    check("stdio initialize id=1", r1.get("id") == 1 and r1["result"]["serverInfo"]["name"] == "yotta-chart")
    r2 = json.loads(lines[1])
    check("stdio tools/list 12", len(r2["result"]["tools"]) == 12)
    r3 = json.loads(lines[2])
    check("stdio tools/call pie 非 error", r3["result"]["isError"] is False)
    t3 = json.loads(r3["result"]["content"][0]["text"])
    check("stdio tools/call 返回文件", bool(t3.get("path")))
    if t3.get("temp_dir"):
        shutil.rmtree(t3["temp_dir"], ignore_errors=True)

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
