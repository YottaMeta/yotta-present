# 更新日志

## v0.1.1 (2026-08-31)

- SKILL.md 新增「使用须知（先做一步）」：技能按需触发（`always-load: false`，不常驻）；配置的 yotta-present MCP 常驻；AI 首次使用写入永久记忆护栏（已有则跳过）。
- SKILL.md 新增「何时使用（默认全走，例外显式退回）」：默认凡交付用户的 AI 输出先经元呈判型 → 选形态 → 渲染；白名单例外（纯代码 / 命令 / CLI 原始输出、错误堆栈 / 日志、超长走 `--out`、用户明确一句话 / 裸文本）显式退回；附形态选择要点。
- SKILL.md 新增「可选配套技能：元真 yotta-humanize」：prose 明显 AI 腔时可选去味，自检测已装则交给它、未装则提示安装命令，不强制、不默认已装。
- SKILL.md 边界 / frontmatter description 定位改「AI 输出的默认呈现层」。

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
