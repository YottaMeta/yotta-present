#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yotta_present.py — 元呈（yotta-present）呈现核心 + CLI。

把任意 AI 输出（JSON / Markdown / 纯文本）归一为「标准内容对象」，
再按形态体系渲染成可复制的 Markdown / 纯文本（copyable-first），
按需附本地 SVG 图（复用 yotta_chart.py 的 12 图表内核 = 「图表形态」子集）。

形态（开源基线 8 种）：
  conclusion 结论卡 / table 表格交付 / checklist 清单卡 / prose 正文 /
  metrics 指标板 / qa 问答卡 / report 报告 / chart 图表

标准内容对象 schema：
  title     标题（字符串，可选）
  headline  头条 / 一句话结论（字符串，可选）
  grade     等级徽章（success|warn|danger|info 或任意文本，可选）
  verdict   裁决 / 结论正文（字符串，可选；与 grade 搭配）
  metrics   指标块（[{label, value, unit?, tone?}, ...]）
  rows      表格（对象列表 / 二维数组 / 键值对，见 references/schema.md）
  bullets   要点（字符串数组）
  body      正文段落（字符串数组，纯文本输入自动解析）
  notes     注记 / 免责（字符串数组）
  chart_data 图表数据（{"chart"|"type", "labels", "data", ...}，可选）
  headers   显式表头（rows 为二维数组时可选）
  form      显式形态（可选，缺省自动判断）

CLI：
  python scripts/yotta_present.py [--file PATH] [--content JSON|TEXT] [--form F]
      [--title T] [--md|--text|--both|--json] [--out PATH] [--svg PATH]
      [--explain] [--list-forms] [--version]

数据不出本机：只在本机拼字符串 / SVG，不联网、不调用远程渲染服务。
"""

import argparse
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import yotta_chart as yc  # noqa: E402  （图表形态复用 12 图内核）

VERSION = "0.1.0"
TOOL_NAME = "yotta-present"
CN_NAME = "元呈·呈现"

FORMS = ["conclusion", "table", "checklist", "prose", "metrics", "qa", "report", "chart"]

FORM_DESC = {
    "conclusion": "结论卡：单个结论 / 评分 / 推荐 → 徽章 + 指标 + 要点",
    "table": "表格交付：行列分明、需对比 / 罗列的数据",
    "checklist": "清单卡：事项 / 要点 / 清单",
    "prose": "正文：叙述 / 说明 / 长段落",
    "metrics": "指标板：一组关键指标",
    "qa": "问答卡：问题 / 回答成对",
    "report": "报告：多节长内容（卡片 + 表 + 文组合 + 目录）",
    "chart": "图表：数值分布 / 趋势 / 占比（本地 SVG，复用 12 图内核）",
}

# 等级徽章（元阁设计语言：🟢🟡🔴；info 用 ⚪）
GRADE_META = {
    "success": {"emoji": "🟢", "text": "通过"},
    "warn": {"emoji": "🟡", "text": "警告"},
    "danger": {"emoji": "🔴", "text": "危险"},
    "info": {"emoji": "⚪", "text": "信息"},
}

SCALAR_KEYS = ("title", "headline", "grade", "verdict")
LIST_KEYS = ("metrics", "rows", "bullets", "body", "notes", "headers")
DICT_KEYS = ("chart_data",)


class PresentError(Exception):
    """内容校验 / 渲染错误（CLI 退出码 2，MCP isError）。"""


# ---------------------------------------------------------------------------
# 标准内容对象归一化
# ---------------------------------------------------------------------------

def _fmt_num(v):
    """数字显示：整数不带小数点，浮点最多两位。"""
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        s = ("%.2f" % v).rstrip("0").rstrip(".")
        return s
    return v


def _norm_scalar_list(key, items):
    out = []
    for i, it in enumerate(items):
        if isinstance(it, (dict, list)):
            raise PresentError("%s 第 %d 项必须是字符串（当前是 %s）"
                               % (key, i + 1, type(it).__name__))
        out.append(str(it))
    return out


def _norm_metrics(items):
    out = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise PresentError("metrics 第 %d 项必须是对象 {label, value, ...}" % (i + 1))
        if "label" not in it or "value" not in it:
            raise PresentError("metrics 第 %d 项缺 label 或 value" % (i + 1))
        m = dict(it)
        m["label"] = str(m["label"])
        m["value"] = _fmt_num(m["value"]) if isinstance(m["value"], (int, float)) else str(m["value"])
        out.append(m)
    return out


def _norm_rows(items):
    out = []
    for i, it in enumerate(items):
        if isinstance(it, dict):
            out.append(dict(it))
        elif isinstance(it, list):
            out.append([_fmt_num(c) if isinstance(c, (int, float)) else str(c) for c in it])
        else:
            raise PresentError("rows 第 %d 项必须是对象或数组" % (i + 1))
    return out


def _parse_text(raw):
    """纯文本 / Markdown 输入 → 标准内容对象（title/headline/bullets/body）。"""
    data = {}
    title = None
    headline = None
    bullets = []
    body = []
    for ln in raw.splitlines():
        s = ln.rstrip()
        m = re.match(r"^\s*#\s+(.+?)\s*$", s)
        if m and title is None:
            title = m.group(1).strip()
            continue
        m = re.match(r"^\s*>\s*(.+)$", s)
        if m:
            if headline is None:
                headline = m.group(1).strip()
            else:
                bullets.append(m.group(1).strip())
            continue
        if re.match(r"^\s*[-*]\s+", s):
            bullets.append(re.sub(r"^\s*[-*]\s+", "", s))
            continue
        if re.match(r"^\s*\[[ xX]\]\s+", s):
            bullets.append(s.strip())
            continue
        if s.strip():
            body.append(s)
    if title:
        data["title"] = title
    if headline:
        data["headline"] = headline
    if bullets:
        data["bullets"] = bullets
    if body:
        data["body"] = body
    return data


def normalize_content(raw, title_override=None):
    """把输入归一化为标准内容对象 dict。

    raw 可为 dict / JSON 字符串 / 纯文本（Markdown）。
    返回 dict；非法输入抛 PresentError。
    """
    if isinstance(raw, dict):
        data = dict(raw)
    elif isinstance(raw, str):
        s = raw.strip()
        if not s:
            raise PresentError("内容为空")
        if s[0] in "[{":
            try:
                data = json.loads(s)
            except json.JSONDecodeError as e:
                raise PresentError("JSON 解析失败：%s" % e)
            if not isinstance(data, dict):
                raise PresentError("JSON 顶层必须是对象（标准内容对象）")
        else:
            data = _parse_text(raw)
    else:
        raise PresentError("不支持的输入类型：%s" % type(raw).__name__)

    if title_override is not None:
        data["title"] = str(title_override)

    for k in SCALAR_KEYS:
        if k in data and data[k] is not None and not isinstance(data[k], str):
            data[k] = str(data[k])
    for k in LIST_KEYS:
        if k not in data or data[k] is None:
            continue
        if not isinstance(data[k], list):
            raise PresentError("%s 必须是数组" % k)
        if k == "metrics":
            data[k] = _norm_metrics(data[k])
        elif k == "rows":
            data[k] = _norm_rows(data[k])
        else:
            data[k] = _norm_scalar_list(k, data[k])
    if data.get("chart_data") is not None and not isinstance(data.get("chart_data"), dict):
        raise PresentError("chart_data 必须是对象")
    return data


# ---------------------------------------------------------------------------
# 确定性判断兜底：内容形状 → 形态（可解释）
# ---------------------------------------------------------------------------

def _row_keys(rows):
    """对象表行：键并集（按首现顺序）。"""
    keys = []
    for r in rows:
        if isinstance(r, dict):
            for k in r:
                if k not in keys:
                    keys.append(k)
    return keys


def _row_cells(row):
    if isinstance(row, dict):
        return list(row.values())
    return list(row)


def _rows_cols(rows):
    """表格列数（对象表取键并集长度，二维表取最长行）。"""
    if rows and isinstance(rows[0], dict):
        return len(_row_keys(rows))
    return max((len(r) for r in rows), default=0)


def _looks_qa_rows(rows, headers=None):
    if headers:
        hh = [str(h).strip().lower() for h in headers]
        if any(h in ("问题", "question", "q") for h in hh) and any(h in ("回答", "答案", "answer", "a") for h in hh):
            return True
    if rows and isinstance(rows[0], dict):
        keys = [str(k).lower() for k in _row_keys(rows)]
        qhit = any(k in ("问题", "question", "q") for k in keys)
        ahit = any(k in ("回答", "答案", "answer", "a") for k in keys)
        if qhit and ahit:
            return True
    return False


def _looks_qa_bullets(bullets):
    n = 0
    for b in bullets:
        s = str(b).strip()
        if re.match(r"^(问|答|q|a)\s*[:：]", s, re.I):
            n += 1
    return n >= 2


def decide_form(content):
    """确定性判断兜底：按内容形状选形态，返回 (form, reasons)。"""
    f = content.get("form")
    if f:
        f = str(f).strip().lower()
        if f not in FORMS:
            raise PresentError("未知形态：%s（可选：%s）" % (f, ", ".join(FORMS)))
        return f, ["用户显式指定 form=%s" % f]

    if content.get("chart_data"):
        return "chart", ["chart_data 存在 → 图表形态（本地 SVG，复用 12 图内核）"]

    rows = content.get("rows")
    if rows:
        if _looks_qa_rows(rows, content.get("headers")):
            return "qa", ["rows 呈现『问题 / 回答』两列 → 问答卡"]
        if content.get("title") and (
                content.get("metrics") or content.get("bullets")
                or content.get("verdict") or content.get("headline") or content.get("body")):
            return "report", ["标题 + 表格 + 其他内容段 → 多节报告"]
        return "table", ["rows 为行列分明的表格数据 → 表格交付"]

    metrics = content.get("metrics")
    if metrics:
        if content.get("verdict") or content.get("grade") or content.get("headline"):
            return "conclusion", ["指标 + 结论 / 头条 → 结论卡"]
        if len(metrics) >= 2:
            return "metrics", ["仅指标（>=2 项）→ 指标板"]
        return "conclusion", ["单指标 + 其余要点 → 结论卡"]

    bullets = content.get("bullets")
    if bullets:
        if _looks_qa_bullets(bullets):
            return "qa", ["要点成对出现『问 / 答』→ 问答卡"]
        if content.get("verdict") or content.get("grade") or content.get("headline"):
            return "conclusion", ["要点 + 结论 / 头条 → 结论卡"]
        if content.get("body"):
            return "prose", ["含正文段落 → 正文"]
        return "checklist", ["仅要点 → 清单卡"]

    if content.get("verdict") or content.get("grade"):
        return "conclusion", ["存在结论 / 裁决 → 结论卡"]

    if content.get("body"):
        return "prose", ["叙述性内容 / 正文段落 → 正文"]

    if content.get("headline") or content.get("title"):
        return "prose", ["仅标题 / 头条 → 正文"]

    return "prose", ["兜底：任何输出至少套『正文』美化，不让内容裸奔"]


# ---------------------------------------------------------------------------
# Markdown / 纯文本 渲染原语
# ---------------------------------------------------------------------------

def _esc_md_cell(v):
    """表格单元格转义：竖线转义、换行转 <br>。"""
    s = str(v)
    return s.replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")

def _md_table(headers, rows):
    out = ["| %s |" % " | ".join(_esc_md_cell(h) for h in headers),
           "| %s |" % " | ".join(["---"] * len(headers))]
    for row in rows:
        cells = [_esc_md_cell(c) for c in row]
        while len(cells) < len(headers):
            cells.append("")
        out.append("| %s |" % " | ".join(cells[:len(headers)]))
    return "\n".join(out)


def _text_table(headers, rows):
    lines = []
    if headers:
        lines.append(" | ".join(str(h) for h in headers))
    for row in rows:
        lines.append(" | ".join(str(c) for c in row))
    return "\n".join(lines)


def _md_bullets(bullets):
    out = []
    for b in bullets:
        s = str(b)
        if re.match(r"^\s*[-*]\s", s) or re.match(r"^\s*\[[ xX]\]\s", s):
            out.append(s.strip())
        else:
            out.append("- %s" % s)
    return "\n".join(out)


def _text_bullets(bullets):
    return "\n".join(str(b) for b in bullets)


def _md_body(body):
    return "\n\n".join(str(b) for b in body)


def _md_notes(notes):
    return "\n".join("> 注：%s" % n for n in notes)


def _text_notes(notes):
    return "\n".join("注：%s" % n for n in notes)


def _grade_badge(grade):
    """返回 (emoji 或 None, 文案)。"""
    if not grade:
        return (None, None)
    g = str(grade).strip().lower()
    meta = GRADE_META.get(g)
    if meta:
        return (meta["emoji"], meta["text"])
    return (None, str(grade))


def _metrics_rows(metrics):
    rows = []
    for m in metrics:
        label = m.get("label", "")
        value = str(m.get("value", ""))
        unit = str(m.get("unit", "")).strip()
        tone = str(m.get("tone", "")).strip().lower()
        arrow = {"up": "▲", "down": "▼", "neutral": "—"}.get(tone, "")
        cell = value
        if unit:
            cell = "%s %s" % (cell, unit)
        if arrow:
            cell = "%s %s" % (arrow, cell)
        rows.append([label, cell])
    return rows


# ---------------------------------------------------------------------------
# 各形态渲染
# ---------------------------------------------------------------------------

def _render_conclusion_md(c):
    sec = []
    if c.get("title"):
        sec.append("# %s" % c["title"])
    badge = _grade_badge(c.get("grade"))
    verdict = c.get("verdict")
    headline = c.get("headline")
    parts = []
    if badge and badge[0]:
        parts.append("%s **%s**" % badge)
    elif badge and badge[1]:
        parts.append("**%s**" % badge[1])
    if verdict:
        parts.append(verdict)
    if headline and headline != verdict:
        parts.append(headline)
    if parts:
        sec.append("> %s" % " — ".join(parts))
    elif headline:
        sec.append("> %s" % headline)
    if c.get("metrics"):
        sec.append("**关键指标**")
        sec.append(_md_table(["指标", "数值"], _metrics_rows(c["metrics"])))
    if c.get("bullets"):
        sec.append("**要点**")
        sec.append(_md_bullets(c["bullets"]))
    if c.get("body"):
        sec.append("**说明**")
        sec.append(_md_body(c["body"]))
    if c.get("notes"):
        sec.append("---")
        sec.append(_md_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_conclusion_text(c):
    sec = []
    if c.get("title"):
        sec.append(c["title"])
    badge = _grade_badge(c.get("grade"))
    verdict = c.get("verdict")
    headline = c.get("headline")
    parts = []
    if badge and badge[1]:
        parts.append("[%s]" % badge[1])
    if verdict:
        parts.append(verdict)
    if headline and headline != verdict:
        parts.append(headline)
    if parts:
        sec.append(" ".join(parts))
    elif headline:
        sec.append(headline)
    if c.get("metrics"):
        sec.append("关键指标")
        sec.append(_text_table(["指标", "数值"], _metrics_rows(c["metrics"])))
    if c.get("bullets"):
        sec.append("要点")
        sec.append(_text_bullets(c["bullets"]))
    if c.get("body"):
        sec.append("说明")
        sec.append(_md_body(c["body"]))
    if c.get("notes"):
        sec.append("")
        sec.append(_text_notes(c["notes"]))
    return "\n\n".join(sec)


def _table_parts(c):
    """解析 rows → (headers, data)；供表格形态与报告『明细』共用。"""
    rows = c["rows"]
    headers = c.get("headers")
    if headers is None:
        if rows and isinstance(rows[0], dict):
            keys = _row_keys(rows)
            if set(keys) <= {"header", "value"} and len(keys) == 2:
                headers = ["项", "值"]
            else:
                headers = keys
            data = [[r.get(k, "") for k in headers] for r in rows]
        else:
            # 二维数组：首行全为字符串且 >=2 行 → 视为表头
            if (len(rows) >= 2 and rows[0] and all(isinstance(x, str) for x in rows[0])):
                headers = [str(x) for x in rows[0]]
                data = rows[1:]
            elif rows and len(rows[0]) == 2:
                headers = ["项", "值"]
                data = rows
            else:
                headers = ["列 %d" % (i + 1) for i in range(_rows_cols(rows))]
                data = rows
    else:
        headers = [str(h) for h in headers]
        data = [_row_cells(r) for r in rows]
    return headers, data


def _render_table_md(c):
    sec = []
    if c.get("title"):
        sec.append("# %s" % c["title"])
    headers, data = _table_parts(c)
    sec.append(_md_table(headers, data))
    if c.get("notes"):
        sec.append(_md_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_table_text(c):
    sec = []
    if c.get("title"):
        sec.append(c["title"])
    headers, data = _table_parts(c)
    sec.append(_text_table(headers, data))
    if c.get("notes"):
        sec.append(_text_notes(c["notes"]))
    return "\n\n".join(sec)

def _render_checklist_md(c):
    sec = []
    if c.get("title"):
        sec.append("# %s" % c["title"])
    if c.get("headline"):
        sec.append("> %s" % c["headline"])
    if c.get("bullets"):
        sec.append(_md_bullets(c["bullets"]))
    if c.get("notes"):
        sec.append("---")
        sec.append(_md_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_checklist_text(c):
    sec = []
    if c.get("title"):
        sec.append(c["title"])
    if c.get("headline"):
        sec.append(c["headline"])
    if c.get("bullets"):
        sec.append(_text_bullets(c["bullets"]))
    if c.get("notes"):
        sec.append("")
        sec.append(_text_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_prose_md(c):
    sec = []
    if c.get("title"):
        sec.append("# %s" % c["title"])
    if c.get("headline"):
        sec.append("> %s" % c["headline"])
    if c.get("body"):
        sec.append(_md_body(c["body"]))
    if c.get("bullets"):
        sec.append("**要点**")
        sec.append(_md_bullets(c["bullets"]))
    if c.get("notes"):
        sec.append("---")
        sec.append(_md_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_prose_text(c):
    sec = []
    if c.get("title"):
        sec.append(c["title"])
    if c.get("headline"):
        sec.append(c["headline"])
    if c.get("body"):
        sec.append(_md_body(c["body"]))
    if c.get("bullets"):
        sec.append("要点")
        sec.append(_text_bullets(c["bullets"]))
    if c.get("notes"):
        sec.append("")
        sec.append(_text_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_metrics_md(c):
    sec = []
    if c.get("title"):
        sec.append("# %s" % c["title"])
    sec.append("**关键指标**")
    sec.append(_md_table(["指标", "数值"], _metrics_rows(c["metrics"])))
    if c.get("headline"):
        sec.append("> %s" % c["headline"])
    if c.get("notes"):
        sec.append("---")
        sec.append(_md_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_metrics_text(c):
    sec = []
    if c.get("title"):
        sec.append(c["title"])
    sec.append("关键指标")
    sec.append(_text_table(["指标", "数值"], _metrics_rows(c["metrics"])))
    if c.get("headline"):
        sec.append(c["headline"])
    if c.get("notes"):
        sec.append("")
        sec.append(_text_notes(c["notes"]))
    return "\n\n".join(sec)


def _parse_qa(content):
    """解析问答对列表 [(问, 答), ...]。"""
    pairs = []
    rows = content.get("rows")
    if rows:
        if rows and isinstance(rows[0], dict):
            keys = _row_keys(rows)
            if set(keys) <= {"header", "value"} and len(keys) == 2:
                for r in rows:
                    pairs.append((str(r.get("header", "")), str(r.get("value", ""))))
            else:
                qkey = akey = None
                for k in keys:
                    kl = str(k).lower()
                    if qkey is None and kl in ("问题", "question", "q"):
                        qkey = k
                    if akey is None and kl in ("回答", "答案", "answer", "a"):
                        akey = k
                if qkey and akey:
                    for r in rows:
                        pairs.append((str(r.get(qkey, "")), str(r.get(akey, ""))))
                else:
                    for r in rows:
                        cells = _row_cells(r)
                        if len(cells) >= 2:
                            pairs.append((str(cells[0]), str(cells[1])))
        else:
            for r in rows:
                cells = _row_cells(r)
                if len(cells) >= 2:
                    pairs.append((str(cells[0]), str(cells[1])))
    elif content.get("bullets"):
        pairs = _pairs_from_bullets(content["bullets"])
    return pairs


def _pairs_from_bullets(bullets):
    pairs = []
    cur_q = None
    cur_a = None
    for b in bullets:
        s = str(b).strip()
        m = re.match(r"^(?:问|q|question)\s*[:：]\s*(.+)$", s, re.I)
        if m:
            if cur_q is not None:
                pairs.append((cur_q, cur_a or ""))
            cur_q = m.group(1).strip()
            cur_a = None
            continue
        m = re.match(r"^(?:答|a|answer)\s*[:：]\s*(.+)$", s, re.I)
        if m:
            cur_a = m.group(1).strip()
            continue
        if cur_q is not None and cur_a is None:
            cur_a = s
        elif cur_q is not None:
            pairs.append((cur_q, cur_a or ""))
            cur_q = s
            cur_a = None
        else:
            cur_q = s
    if cur_q is not None:
        pairs.append((cur_q, cur_a or ""))
    return pairs


def _render_qa_md(c):
    sec = []
    if c.get("title"):
        sec.append("# %s" % c["title"])
    for q, a in _parse_qa(c):
        sec.append("**问：%s**" % q)
        sec.append("答：%s" % a)
    if c.get("notes"):
        sec.append("---")
        sec.append(_md_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_qa_text(c):
    sec = []
    if c.get("title"):
        sec.append(c["title"])
    for q, a in _parse_qa(c):
        sec.append("问：%s" % q)
        sec.append("答：%s" % a)
    if c.get("notes"):
        sec.append("")
        sec.append(_text_notes(c["notes"]))
    return "\n\n".join(sec)


def _report_sections(c):
    """报告章节列表 [(标题, 是否存在), ...]。"""
    return [
        ("摘要", bool(c.get("verdict") or c.get("headline") or c.get("body"))),
        ("关键指标", bool(c.get("metrics"))),
        ("明细", bool(c.get("rows"))),
        ("要点", bool(c.get("bullets"))),
        ("注记", bool(c.get("notes"))),
    ]


def _render_report_md(c):
    sec = []
    if c.get("title"):
        sec.append("# %s" % c["title"])
    if c.get("headline"):
        sec.append("> %s" % c["headline"])
    sections = [t for t, on in _report_sections(c) if on]
    if sections:
        sec.append("**目录**")
        sec.append("\n".join("- %s" % t for t in sections))
    badge = _grade_badge(c.get("grade"))
    for t, on in _report_sections(c):
        if not on:
            continue
        sec.append("## %s" % t)
        if t == "摘要":
            parts = []
            if badge and badge[0]:
                parts.append("%s **%s**" % badge)
            elif badge and badge[1]:
                parts.append("**%s**" % badge[1])
            if c.get("verdict"):
                parts.append(c["verdict"])
            if parts:
                sec.append(" ".join(parts))
            if c.get("headline") and c.get("headline") != c.get("verdict"):
                sec.append(c["headline"])
            if c.get("body"):
                sec.append(_md_body(c["body"]))
        elif t == "关键指标":
            sec.append(_md_table(["指标", "数值"], _metrics_rows(c["metrics"])))
        elif t == "明细":
            headers, data = _table_parts(c)
            sec.append(_md_table(headers, data))
        elif t == "要点":
            sec.append(_md_bullets(c["bullets"]))
        elif t == "注记":
            sec.append(_md_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_report_text(c):
    sec = []
    if c.get("title"):
        sec.append(c["title"])
    if c.get("headline"):
        sec.append(c["headline"])
    badge = _grade_badge(c.get("grade"))
    for t, on in _report_sections(c):
        if not on:
            continue
        sec.append("== %s ==" % t)
        if t == "摘要":
            parts = []
            if badge and badge[1]:
                parts.append("[%s]" % badge[1])
            if c.get("verdict"):
                parts.append(c["verdict"])
            if parts:
                sec.append(" ".join(parts))
            if c.get("headline") and c.get("headline") != c.get("verdict"):
                sec.append(c["headline"])
            if c.get("body"):
                sec.append(_md_body(c["body"]))
        elif t == "关键指标":
            sec.append(_text_table(["指标", "数值"], _metrics_rows(c["metrics"])))
        elif t == "明细":
            headers, data = _table_parts(c)
            sec.append(_text_table(headers, data))
        elif t == "要点":
            sec.append(_text_bullets(c["bullets"]))
        elif t == "注记":
            sec.append(_text_notes(c["notes"]))
    return "\n\n".join(sec)


def _chart_ref(chart, prefer_path=False):
    """Markdown 图片引用：有本地路径且允许时用相对路径，否则用 data URI（自包含可复制）。"""
    if prefer_path and chart.get("path"):
        p = chart["path"]
        try:
            rel = os.path.relpath(p, os.getcwd())
            if not rel.startswith(".."):
                return rel.replace("\\", "/")
        except ValueError:
            pass
        return p
    return chart.get("data_uri") or ""


def _render_chart_md(c, chart, prefer_path=False):
    sec = []
    if c.get("title"):
        sec.append("# %s" % c["title"])
    ctitle = chart.get("title") or c.get("title") or chart.get("chart")
    sec.append("![%s](%s)" % (ctitle, _chart_ref(chart, prefer_path)))
    if c.get("headline"):
        sec.append("> %s" % c["headline"])
    if c.get("notes"):
        sec.append("---")
        sec.append(_md_notes(c["notes"]))
    return "\n\n".join(sec)


def _render_chart_text(c, chart):
    sec = []
    if c.get("title"):
        sec.append(c["title"])
    if chart.get("path"):
        sec.append("图表（%s）已生成：%s" % (chart["chart"], chart["path"]))
    else:
        sec.append("图表（%s）：data URI 内嵌于 Markdown 输出" % chart["chart"])
    if c.get("headline"):
        sec.append(c["headline"])
    if c.get("notes"):
        sec.append("")
        sec.append(_text_notes(c["notes"]))
    return "\n\n".join(sec)


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------

def _render_chart(cd, svg_out=None):
    """渲染图表（复用 yotta_chart 内核），返回 meta dict。"""
    cd = cd or {}
    params = dict(cd)
    ctype = params.pop("chart", None) or params.pop("type", None) or "bar"
    if svg_out:
        params["out"] = svg_out
    try:
        r = yc.render(str(ctype), params)
    except Exception as e:  # noqa: BLE001
        raise PresentError("图表渲染失败：%s" % e)
    return {
        "chart": r.get("chart") or str(ctype),
        "title": cd.get("title") or "",
        "width": r.get("width"),
        "height": r.get("height"),
        "path": r.get("path"),
        "data_uri": r.get("data_uri"),
    }


def present(raw, form=None, title=None, svg_out=None, explain=False):
    """呈现核心入口。

    raw: dict / JSON 字符串 / 纯文本
    form: 显式形态（可选）
    title: 标题覆盖（可选）
    svg_out: 图表形态的本地 SVG 输出路径（可选）
    explain: 附判断说明（可选）
    返回: {form, markdown, text, explain?, chart?}
    """
    content = normalize_content(raw, title_override=title)
    if form is not None:
        f = str(form).strip().lower()
        if f not in FORMS:
            raise PresentError("未知形态：%s（可选：%s）" % (f, ", ".join(FORMS)))
        reasons = ["用户显式指定 form=%s" % f]
    else:
        f, reasons = decide_form(content)

    if f == "chart":
        if not content.get("chart_data"):
            raise PresentError("形态 chart 需要 chart_data 字段")
        chart = _render_chart(content["chart_data"], svg_out=svg_out)
        md = _render_chart_md(content, chart, prefer_path=bool(svg_out))
        text = _render_chart_text(content, chart)
        result = {"form": f, "markdown": md, "text": text, "chart": chart}
    elif f == "conclusion":
        result = {"form": f, "markdown": _render_conclusion_md(content),
                  "text": _render_conclusion_text(content)}
    elif f == "table":
        result = {"form": f, "markdown": _render_table_md(content),
                  "text": _render_table_text(content)}
    elif f == "checklist":
        result = {"form": f, "markdown": _render_checklist_md(content),
                  "text": _render_checklist_text(content)}
    elif f == "prose":
        result = {"form": f, "markdown": _render_prose_md(content),
                  "text": _render_prose_text(content)}
    elif f == "metrics":
        result = {"form": f, "markdown": _render_metrics_md(content),
                  "text": _render_metrics_text(content)}
    elif f == "qa":
        result = {"form": f, "markdown": _render_qa_md(content),
                  "text": _render_qa_text(content)}
    elif f == "report":
        result = {"form": f, "markdown": _render_report_md(content),
                  "text": _render_report_text(content)}
    else:
        raise PresentError("未实现的形态：%s" % f)

    if explain:
        result["explain"] = reasons
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _write_utf8(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _read_utf8(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _build_parser():
    p = argparse.ArgumentParser(
        prog="yotta_present",
        description="元呈 yotta-present 呈现核心：任意内容 → 可复制 Markdown / 纯文本（按需附本地 SVG）")
    p.add_argument("--file", metavar="PATH", help="从文件读取内容（UTF-8）")
    p.add_argument("--content", metavar="TEXT", help="直接传入内容（JSON 或文本）")
    p.add_argument("--form", choices=FORMS, help="显式指定形态（缺省自动判断）")
    p.add_argument("--title", metavar="T", help="覆盖标题")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--md", action="store_true", help="输出 Markdown（默认）")
    g.add_argument("--text", action="store_true", help="输出纯文本")
    g.add_argument("--both", action="store_true", help="同时输出 Markdown 与纯文本")
    g.add_argument("--json", dest="json_out", action="store_true", help="输出完整 JSON 结果")
    p.add_argument("--out", metavar="PATH", help="写文件（--both 时写 .md 与 .txt；目录则按形态命名）")
    p.add_argument("--svg", metavar="PATH", help="图表形态：本地 SVG 输出路径")
    p.add_argument("--explain", action="store_true", help="附判断说明")
    p.add_argument("--list-forms", action="store_true", help="列出形态清单")
    p.add_argument("--version", action="store_true", help="显示版本")
    return p


def _read_input(args):
    if args.file:
        try:
            return _read_utf8(args.file)
        except OSError as e:
            raise PresentError("无法读取文件：%s" % e)
    if args.content is not None:
        return args.content
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def _write_out(args, result):
    """--out 写文件；返回已写文件列表。"""
    out = args.out
    is_dir = os.path.isdir(out)
    base = out if is_dir else os.path.splitext(out)[0]
    written = []
    if args.json_out:
        p = os.path.join(base, "present.json") if is_dir else out
        _write_utf8(p, json.dumps(result, ensure_ascii=False, indent=2))
        written.append(p)
    elif args.text:
        p = os.path.join(base, "present-%s.txt" % result["form"]) if is_dir else out
        _write_utf8(p, result["text"])
        written.append(p)
    elif args.both:
        md_p = os.path.join(base, "present-%s.md" % result["form"]) if is_dir else (out or base + ".md")
        txt_p = os.path.splitext(md_p)[0] + ".txt"
        _write_utf8(md_p, result["markdown"])
        _write_utf8(txt_p, result["text"])
        written.extend([md_p, txt_p])
    else:
        p = os.path.join(base, "present-%s.md" % result["form"]) if is_dir else out
        _write_utf8(p, result["markdown"])
        written.append(p)
    for p in written:
        print("已写入：%s" % p)


def cli(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("元呈 yotta-present %s（呈现核心，TOOL_NAME=%s）" % (VERSION, TOOL_NAME))
        return 0
    if args.list_forms:
        print("元呈 yotta-present 呈现形态（开源基线 %d 种）：" % len(FORMS))
        for f in FORMS:
            print("  %-12s %s" % (f, FORM_DESC[f]))
        return 0

    try:
        raw = _read_input(args)
    except PresentError as e:
        print("错误：%s" % e, file=sys.stderr)
        return 1
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        parser.print_help()
        return 1

    try:
        result = present(raw, form=args.form, title=args.title,
                         svg_out=args.svg, explain=args.explain)
    except PresentError as e:
        print("错误：%s" % e, file=sys.stderr)
        return 2
    except ValueError as e:
        print("错误：%s" % e, file=sys.stderr)
        return 2

    if args.svg and result["form"] != "chart":
        print("错误：--svg 仅在图表形态下有效（当前形态：%s，可加 --form chart）"
              % result["form"], file=sys.stderr)
        return 2

    if args.out:
        try:
            _write_out(args, result)
        except OSError as e:
            print("错误：写入失败：%s" % e, file=sys.stderr)
            return 2
        return 0

    if args.json_out:
        out = dict(result)
        if out.get("chart"):
            out["chart"] = {k: v for k, v in out["chart"].items() if k != "svg"}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif args.text:
        print(result["text"])
    elif args.both:
        print(result["markdown"])
        print("\n---\n")
        print(result["text"])
    else:
        print(result["markdown"])
    return 0


if __name__ == "__main__":
    sys.exit(cli())
