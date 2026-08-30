# 更新日志

## v0.1.0 (2026-08-30)

初始发布：

- 定位：元呈 —— AI 自主选择的**通用结果呈现层**（不是图表工具）；图表只是呈现形态之一。
- 呈现核心 `yotta_present`：任意输入（JSON 标准内容对象 / Markdown / 纯文本）→ 可复制 Markdown / 纯文本双输出。
- 标准内容对象 schema v1：`title / headline / grade|verdict / metrics[] / rows[] / bullets[] / body[] / notes[] / chart_data? / form?`。
- 开源基线 8 形态：结论卡 / 表格交付 / 清单卡 / 正文 / 指标板 / 问答卡 / 报告 / 图表。
- 确定性判断兜底：内容形状 → 形态自动选择（可解释，`--explain` 返回原因）；`--form` 显式指定。
- 图表形态复用 12 图 SVG 内核（bar/line/pie/radar/scatter/histogram/funnel/waterfall/word_cloud/sankey/spreadsheet/treemap）：本地生成，Markdown 内嵌 data URI 或 `--svg` 写文件。
- MCP server `yotta-present`：`present_result`（md|text|both|json + explain，`form=chart` 复用 12 图内核）+ `present_forms`（只读）；SKILL.md 含「MCP：AI 自动接入」——AI 首次使用自动写 mcpServers + 永久记忆护栏，按需调用、未加载降级 CLI。
- 测试：112/112（呈现）+ 72/72（SVG 内核），Python 3.8 + 3.13 双版本全绿（含 CLI / MCP / stdio 端到端）。
- 文档：SKILL.md 判断层（内容类型 8 大类 → 形态 12 种）+ README 中英双版 + references/schema.md。
