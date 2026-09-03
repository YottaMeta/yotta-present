## v0.3.0 (2026-09-03)

S7-M1 彩色呈现升级·开源第一步：R1 全面化 + channel×platform 通道映射 + plain 去 emoji（R0 保底无色）。

- 新增渲染通道 `--channel` / MCP `channel`（auto/r0/r1/r2/r3）：auto 按 platform 自动映射——`plain` → `r0`（保底无色、无 emoji 徽章），`webchat`/`discord`/`whatsapp` → `r1`（emoji 增强 Markdown）；显式 `r2`/`r3`（富文本 HTML / SVG 整卡）属收费侧高级美化引擎，当前版本友好报错「尚未开放」。
- R1 全面化：grade chip emoji（🟢🟡🔴⚪）与统一引用条覆盖各形态——有 grade/verdict/headline 即渲染 `> 🟢 **通过** — …` 摘要条（conclusion/table/checklist/prose/metrics/qa/report/模板 summary）；table/qa 的注记前补 `---` 分隔线，metrics 摘要条移至标题之后，与其它形态一致。
- plain 去 emoji：`platform=plain`（auto→r0）时 Markdown 输出不再含 🟢🟡🔴⚪ 徽章（颜色不作唯一信息载体，文字徽章仍在）；text 输出本就无 emoji，保持不变。
- 返回结果新增 `channel` 字段（生效通道），CLI `--json` / MCP `present_result` 均可见。
- 文档：SKILL.md 新增「渲染通道与平台」；README 中英命令表 + 示例补 `--channel`；references/schema.md 平台节扩为「渲染通道与平台」；references/faq.md 补「想去掉 emoji / 颜色」「R2/R3 何时可用」。
- 测试：新增 R1/plain/channel 断言 33 条；双版本（3.8/3.13）全绿不回归（180/180 + SVG 72/72）。
- 版本四件对齐 0.3.0（package.json / SKILL.md / CHANGELOG / CLI --version）；插件 yotta-present-plugin 同步 0.3.0。

## v0.2.1 (2026-09-01)

评测反馈优化（文档 + 错误提示，功能不变）。

- 新增 `references/faq.md`：12 条常见问题 / 避坑指南（徽章、columns、chart_data、--svg、形态选择、JSON 解析、MCP 加载、--text、max_len、平台差异、退出码、白名单例外）。
- 错误提示友好化：CLI 出错时 stderr 附「修复建议」人话（内容为空 / JSON 解析 / 顶层对象 / 类型 / 数组 / chart_data / 形态 / 模板 / 图表渲染 / 平台 / max_len / 读文件 / --svg / 写文件 等 14 类）。
- README 中英：新增「30 秒上手」「效果展示（输入→输出）」「使用技巧」「错误处理」「常见问题 FAQ 速查」。
- SKILL.md：新增「常见问题 FAQ（速查）」小节，指向 references/faq.md。
- 版本四件对齐 0.2.1（package.json / SKILL.md / CHANGELOG / CLI --version）。

# 更新日志

## v0.2.0 (2026-09-01)

格式规范扩展（《AI智能体回复格式设计规范》大嫂实战总结）+ 安全扫描修复（ClawHub SUSPICIOUS 项）。

- 平台自适应层：新增 `--platform` / MCP `platform`，webchat（默认，完整 Markdown）/ discord / whatsapp（禁表格、禁大标题 → 表格转列表、标题转加粗）/ plain（命令行/纯文本：保留分点与逻辑顺序，去 Markdown 符号）。
- 命名场景模板：新增 `--template` / MCP `template`，声明式 structure 骨架（vuln_report / faq / status），一次定义多处复用；模板定义存 `references/templates.json`（独立配置、可热更新，缺失回退内置）。
- codeblock 块类型：模板支持 `codeblock`（content 的 `code` 字段，`lang` 语言围栏）。
- bold_keys 自动加粗：content 或 MCP 参数 `bold_keys`，命中字段的值渲染为 `**加粗**`（plain 不加）。
- max_len 长度熔断：content `max_len` 或 `--max-len N`，先压缩列表、再降标题层级、最后硬截断，保留 title/headline/verdict 结论。
- MCP 新增 `present_templates` 只读工具（列出模板骨架）；`present_result` 缺省返回判型理由的说明与实现对齐（SDI-4）。
- 安全修复（ClawHub 0.1.2 Security SUSPICIOUS 项）：TT2 测试 interpreter 白名单校验（`_resolve_test_python`，仅接受绝对路径 + basename python*，否则回退 sys.executable）；SKILL.md / README 补「明确同意门」与权限声明（写入 mcpServers/永久记忆前先征得用户同意，拒绝则降级 CLI，不影响功能）。
- 测试：147/147（呈现）+ 72/72（SVG 内核）双版本全绿（原 118 + 新增 29：平台 6 / 模板 10 / codeblock+bold+max_len 5 / CLI 4 / MCP 2 / 安全 2）。

> 注：v0.1.2（5c681de）实际已随 GitHub tag v0.1.2 三源发布（npm gitHead=5c681de / ClawHub 0.1.2），本版在其基础上扩展；v0.1.2 修复内容见下。

 (2026-08-31)

问题反馈修复（晓安 2026-08-31 反馈）：P2/P4 代码 + P3/P5/P1 文档。

- P2 错用不报错：新增 warnings 机制——错误字段组合（table 的 columns / conclusion 无 grade·verdict / qa 非问题·回答两列）不阻断渲染，但 CLI 打 stderr「提示」、MCP 返回附 warnings 字段。
- P4 判型反馈：MCP present_result 缺省即返回判型理由（explain），显式 explain=false 可关。
- P3 输入速查：references/schema.md 顶部新增「形态 → 输入形式 → 必填字段」总表。
- P5 qa 约束：SKILL.md「形态选择要点」与「形态选择规则」补「rows 须为 问题/回答 两列，否则判 table」。
- P1 降级一致性澄清：SKILL.md / README 中英明确「无 --svg 时 CLI 与 MCP 均输出 data URI（自包含可复制）；显式 --svg 时 CLI 写本地 SVG 并以路径引用」。（反馈中 blob 引用现象在 0.1.1 代码层无法复现，无 image_blob_ref 逻辑，疑似客户端侧表示）
- 测试：新增 warnings/explain 用例（6 条）。
- 版本升至 0.1.2。

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
