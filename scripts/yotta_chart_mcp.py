#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yotta_chart_mcp.py — 元图（yotta-chart）SVG 内核的 MCP 包装（内部实现）。

stdio MCP server（JSON-RPC 2.0，换行分隔），把 yotta_chart.py 本地零依赖
SVG 渲染内核暴露为 MCP 工具（12 种图表）。数据不出本机：只在本机拼 SVG
并写文件，不联网、不调用外部渲染服务。

注意：本文件是内部实现，已被 yotta-present（yotta_present_mcp.py）统一
呈现取代——图表形态走 present_result 的 chart_data 即可，无需单独配置
本 server；对外文档不把它列为公开 MCP。仅供直接调试 / 高级用法。
"""

import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import yotta_chart as yc  # noqa: E402

VERSION = yc.VERSION
TOOL_NAME = yc.TOOL_NAME
CN_NAME = yc.CN_NAME
MCP_PROTOCOL = "2025-03-26"
SERVERS = {TOOL_NAME: {"name": TOOL_NAME, "cn": CN_NAME, "version": VERSION}}


def _tool_error(message, extra=None):
    """构造工具调用错误结果（isError=true）。"""
    payload = {"error": message}
    if extra:
        payload.update(extra)
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
            "isError": True}


_COMMON_PROPS = {
    "title": {"type": "string", "description": "图表标题（可选）"},
    "width": {"type": "integer", "description": "画布宽（默认 800，表格 700）"},
    "height": {"type": "integer", "description": "画布高（默认 480-520）"},
    "palette": {"type": "string",
                "enum": ["default", "ocean", "forest", "mono", "warm"],
                "description": "配色方案（默认 default）"},
    "out": {"type": "string", "description": "可选：SVG 输出目录或文件路径；缺省只返回 data URI"},
    "filename": {"type": "string", "description": "可选：输出文件名（配合 out 目录使用）"},
}

_DATA_PROPS = {
    "labels": {"type": "array", "items": {"type": "string"},
               "description": "类目/维度标签（bar/line/pie/radar/funnel/waterfall）"},
    "data": {"description": "图表数据：数值数组 / 嵌套数组 / JSON 字符串（见各工具描述）"},
}

_PAIR_PROPS = {
    "labels": _DATA_PROPS["labels"],
    "data": _DATA_PROPS["data"],
}


def _tool_spec(name, description, properties, required=None):
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            **({"required": required} if required else {}),
        },
    }


def mcp_tools():
    """返回 MCP tools 列表（12 种图表，与内核 CHART_TYPES 一一对应）。"""
    p = dict(_COMMON_PROPS)
    p.update(_PAIR_PROPS)
    return [
        _tool_spec("generate_bar_chart",
                   "本地生成柱状图 SVG。data 为数值数组（单序列）或嵌套数组（多序列分组）；"
                   "可选 stacked=true 堆叠。返回 SVG 文件路径 / data URI。",
                   dict(p, stacked={"type": "boolean", "description": "是否堆叠（多序列时）"}),
                   ["data"]),
        _tool_spec("generate_line_chart",
                   "本地生成折线图 SVG。data 为数值数组或嵌套数组（多序列）；可选 fill=true 面积填充。",
                   dict(p, fill={"type": "boolean", "description": "是否面积填充"}),
                   ["data"]),
        _tool_spec("generate_pie_chart",
                   "本地生成饼图 SVG。data 为数值数组（>0），labels 为扇区名；返回路径 / data URI。",
                   dict(p, show_pct={"type": "boolean", "description": "是否显示百分比（默认 true）"}),
                   ["data"]),
        _tool_spec("generate_radar_chart",
                   "本地生成雷达图 SVG。labels=维度（>=3），data 为数值数组或嵌套数组（多序列）。",
                   p, ["data"]),
        _tool_spec("generate_scatter_chart",
                   "本地生成散点图 SVG。data=[[x,y],...] 或嵌套数组（多组）。",
                   {"data": _DATA_PROPS["data"], "labels": _DATA_PROPS["labels"], **_COMMON_PROPS},
                   ["data"]),
        _tool_spec("generate_histogram_chart",
                   "本地生成直方图 SVG。data=原始数值数组，可选 bins 分箱数。",
                   dict({k: v for k, v in _COMMON_PROPS.items()},
                        data=_DATA_PROPS["data"],
                        bins={"type": "integer", "description": "分箱数（默认 sqrt(n)）"}),
                   ["data"]),
        _tool_spec("generate_funnel_chart",
                   "本地生成漏斗图 SVG。labels=阶段名，data=阶段数值。",
                   p, ["data"]),
        _tool_spec("generate_waterfall_chart",
                   "本地生成瀑布图 SVG。data=[起始, 增减..., 累计]，正=增加、负=减少。",
                   p, ["data"]),
        _tool_spec("generate_word_cloud_chart",
                   "本地生成词云 SVG。data 为 [{\"text\":..,\"weight\":..}, ...] 或 [[text,weight], ...]。",
                   dict({k: v for k, v in _COMMON_PROPS.items()},
                        data=_DATA_PROPS["data"],
                        max_words={"type": "integer", "description": "最大词数（默认 60）"}),
                   ["data"]),
        _tool_spec("generate_sankey_chart",
                   "本地生成桑基图 SVG。data 为 {\"nodes\":[{id,label}],\"links\":[{source,target,value}]}。",
                   dict({k: v for k, v in _COMMON_PROPS.items()},
                        data=_DATA_PROPS["data"]),
                   ["data"]),
        _tool_spec("generate_spreadsheet_chart",
                   "本地生成表格 SVG。data=二维数组，headers 可选列头。",
                   dict({k: v for k, v in _COMMON_PROPS.items()},
                        data=_DATA_PROPS["data"],
                        headers={"type": "array", "items": {"type": "string"}, "description": "列头"}),
                   ["data"]),
        _tool_spec("generate_treemap_chart",
                   "本地生成矩形树图 SVG。data 为 [{\"label\":..,\"value\":..}, ...] 或 [[label,value], ...]。",
                   dict({k: v for k, v in _COMMON_PROPS.items()},
                        data=_DATA_PROPS["data"],
                        max_boxes={"type": "integer", "description": "最大块数（默认 60）"}),
                   ["data"]),
    ]


def _normalize_data(params):
    """把 data 字符串转成 JSON / 数值列表（与内核 render 一致）。"""
    data = params.get("data")
    if isinstance(data, str):
        try:
            return json.loads(data)
        except (ValueError, TypeError):
            return [yc._num(x) for x in yc._as_list(data)]
    return data


def _tool_generate(chart):
    def handler(params):
        if "data" not in params or params.get("data") in (None, "", []):
            return _tool_error("generate_%s_chart 需要 data 参数" % chart)
        p = dict(params)
        p["data"] = _normalize_data(params)
        if isinstance(p.get("labels"), str):
            p["labels"] = yc._as_list(p["labels"])
        if isinstance(p.get("headers"), str):
            p["headers"] = yc._as_list(p["headers"])
        try:
            r = yc.render(chart, p)
        except Exception as e:  # noqa: BLE001
            return _tool_error("生成 %s 失败：%s" % (chart, e))
        result = {k: v for k, v in r.items() if k != "svg"}
        if not result.get("path"):
            # 未指定 out：写临时目录，保证客户端有文件可用
            import tempfile
            tmpdir = tempfile.mkdtemp(prefix="yotta-chart-")
            out = os.path.join(tmpdir, "yotta-chart-%s.svg" % chart)
            yc._write_utf8(out, r["svg"])
            result["path"] = out
            result["temp_dir"] = tmpdir
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
                "isError": False}
    return handler


TOOL_HANDLERS = {("generate_%s_chart" % c): _tool_generate(c) for c in yc.CHART_TYPES}


def handle_message(msg):
    """处理一行 JSON-RPC 消息，返回响应 dict；通知返回 None。"""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        rid = msg.get("id") if isinstance(msg, dict) else None
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32600, "message": "invalid request"}}
    method = msg.get("method")
    rid = msg.get("id")
    if rid is None:  # JSON-RPC 通知（无 id）不响应
        return None
    if method is None:
        return None
    params = msg.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": rid,
            "result": {
                "protocolVersion": MCP_PROTOCOL,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": TOOL_NAME, "version": VERSION},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": mcp_tools()}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return {
                "jsonrpc": "2.0", "id": rid,
                "result": {"content": [{"type": "text", "text": "未知工具: %s" % name}], "isError": True},
            }
        try:
            return {
                "jsonrpc": "2.0", "id": rid,
                "result": handler(arguments),
            }
        except Exception as e:  # noqa: BLE001
            return {
                "jsonrpc": "2.0", "id": rid,
                "result": {"content": [{"type": "text", "text": "工具执行异常：%s" % e}], "isError": True},
            }
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "Method not found: " + str(method)}}


def main():
    """stdio 主循环：读行 -> JSON-RPC -> 响应行。"""
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}},
                ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue
        resp = handle_message(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
