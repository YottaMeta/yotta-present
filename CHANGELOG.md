## v0.6.6 (2026-09-25)

口径修正：默认呈现规则补明确边界（ClawHub LLM 复核）。

- SKILL.md 与中英 README 明确：呈现层是可选增强而非强制接管——用户要裸文本 / 说不用元呈时按原样输出，项目或用户自有输出规范优先；渲染不改写内容与结论，渲染失败退回原文。
- 安装器加固：拒绝对符号链接目标写入、不做整目录删除；批量安装需 `--yes`。

**默认触发自检 + fidelity 语义澄清 + MCP schema 精简**

- `SKILL.md` 增加发送前自检：只要含清单 / 表格 / 结论 / 汇总，必须先调用 `present_result`；白名单例外只豁免命中块，其余块仍走元呈。
- `fidelity` 新增 `requested_form` / `final_form` / `requested_form_preserved` / `content_preserved`，明确区分“请求形态未保真”和“最终内容未保留”；`explain` 同步输出两项。
- `present_result` 默认 MCP schema 从 12 个参数精简为 6 个：`content` / `form` / `template` / `output` / `explain` / `options`；高级参数统一放入 `options`，旧版顶层高级参数继续兼容。
- 回归覆盖 fallback 双保真语义、正常形态保真、精简 schema、`options` 调用和旧参数兼容；present 测试 247/247 通过。
- 版本对齐：package.json / SKILL.md frontmatter / skill-manifest.json / CHANGELOG / 引擎 VERSION = 0.6.5。

## v0.6.5 (2026-09-22)

## v0.6.4 (2026-09-21)

嵌套列表保真修复（YottaCode 实测 C1）：

- `form=report` 保留嵌套有序 / 无序列表的层级与列表类型，不再把子项拍平成同级。
- 内容保真门禁增加嵌套结构覆盖校验：深度或有序 / 无序类型丢失时按不兼容处理，不再误报 `fidelity.preserved`。
- 新增 C1-01～C1-08 回归，覆盖无序嵌套、父项 / 子项归属、有序嵌套、纯文本输出、结构丢失识别与 CLI `--form report`；全量 239/239 通过。
- 版本五件对齐 0.6.4（package.json / SKILL.md / skill-manifest.json / CLI / chart CLI）；插件 yotta-present-plugin 同步 0.6.4。

## v0.6.3 (2026-09-17)

- `metrics` 明确要求对象列表 `[{label,value,unit?,tone?}]`；传入字符串 / 缺少字段时，错误提示直接给出完整示例。
- FAQ / schema 同步补充 metrics 形态说明；新增 2 项错误提示回归。

## v0.6.2 (2026-09-13)

**P0-4.2 元呈 before_send 试点**：

- 新增 `skill-manifest.json`，声明 `before_send` / `present_result` / `fallback: explicit-unverified`。
- 适配器按宿主能力诚实降级：Codex 无 `before_send` 原生事件，结果只能标记 `explicit-unverified`，不宣称强制。
- 发布件包含 `skill-manifest.json`，供元阁 `hook evaluate` 读取并写审计证据。

## v0.6.1 (2026-09-11)

顺序保真修复（dogfooding D-07）：有书写顺序的输入（Markdown / 纯文本 / 显式 `blocks`）新增块顺序校验；候选形态顺序不符时按不兼容处理，自动降级 report-safe。

- 新增顺序保真校验：按源块顺序做单调锚点定位；「段落 → 列表 → 段落」这类交叉结构在字段驱动形态（如 `prose`）中不能保序时，自动降级 report-safe，`fallback.reason` 说明“无法保持内容块顺序”。
- `fidelity` 新增 `order_checked` / `order_preserved` / `order_violations`，顺序变化不再无记录；`--explain` 增加「顺序」行。
- JSON 字段输入（无书写顺序）不做顺序判定，避免误伤 report 目录 / 模板骨架等结构形态。
- 回归：A-11 / A-11b（顺序保真 + 降级可观测）、A-12（顺序可表达时不误降级）；`python scripts/test_yotta_present.py` 229 通过 / 0 失败；chart 84 通过 / 0 失败。
- 版本对齐 0.6.1（package.json / SKILL.md / CHANGELOG / CLI --version / chart CLI）。

## v0.6.0 (2026-09-11)

P0-0 内容保真与 dogfooding gate：元呈从「字段驱动渲染」升级为「块级内容保真渲染」，显式形态不再拥有丢正文的权利。

- 新增 Markdown 顺序块级 AST：标题、段落、列表（含有序/复选）、表格、引用、代码、问答、图表；混合内容按原顺序保真。
- 表格双兼容：Markdown table 可直接进入 `table` / `report` 等形态，不再要求用户改写成 JSON `rows`；JSON `rows` 既有路径保持不变。
- 新增内容保真门禁：候选 `form` / `template` 渲染后执行块覆盖校验；无法完整保留内容时自动降级 `report-safe`，禁止 title-only 静默失败。
- 返回结果新增 `fallback`（来源、目标、原因）与 `fidelity`（源块、保留块、丢弃块、压缩块、建议形态）；`--explain` 说明保留、压缩、丢弃与降级取舍。
- `max_len` 长度熔断不再假成功：被截断/压缩的块会进入 `fidelity.dropped` / `fidelity.compressed`，`explain` 只报告实际保留块。
- 修复 Windows 测试基建编码：CLI 子进程显式 `PYTHONIOENCODING=utf-8`，避免 stderr 按本机 ANSI 输出导致测试崩溃。
- 固化 A-01～A-10 内容保真回归（status 正文、checklist 表格、report 表格、Markdown/JSON 双表格、QA、混合内容、长文+代码、模板失败、空内容）与 `max_len` 真实取舍测试。
- 测试：`python scripts/test_yotta_present.py` 224 通过 / 0 失败。
- 版本对齐 0.6.0（package.json / SKILL.md / CHANGELOG / CLI --version / chart CLI）。

## v0.5.0 (2026-09-06)

**MCP 协议对齐最新版 2026-07-28（无状态时代）**：yotta-present MCP 升级 dual-era——modern 直连（server/discover 免握手、逐请求 _meta 版本声明、resultType、-32022 版本错误）服务新客户端；legacy（initialize 握手，protocolVersion 2025-11-25）兼容旧客户端，旧形状响应零惊扰。SKILL 标注「基于 MCP 最新协议 2026-07-28（向后兼容 2025-11-25 及更早握手）」。测试 201/201（含 modern MCP 用例）。

## v0.4.0 (2026-09-05)

S7-M2 色板 token 化（开源）：一处定义、全通道消费 + 图表 SVG 明暗双主题 + WCAG 对比度自查。

- 新增 `references/theme.json`：声明式主题 token（light/dark 基础色 + 语义色 + 形态主色 + 图表色板），缺失/损坏自动回退内置，社区可贡献、可热更新。
- 渲染内核去硬编码：yotta_chart 全部角色色（背景/标题/正文/次要/网格/轴线/表面/边框/彩色块描边与文字）改经 token 取色，颜色只出现在 token 定义处。
- 新增 `--theme light|dark`（CLI / MCP `present_result` / chart_data）：dark = 深底浅字暗色图表，含各色板 dark 变体；默认 light 视觉与 0.3.0 一致（次要文字微调至 WCAG AA）。
- 新增 `python scripts/yotta_chart.py --check-contrast`：WCAG 对比度自查（正文/背景配对 ≥ 4.5:1），不达标即非 0 退出（防社区 token 破坏无障碍底线）。
- 语义色 token 与 GRADE_META 对齐（success/warn/danger/info/neutral），为 R2/R3 高级美化通道铺好取色地基。
- 文档：SKILL.md / README 中英命令表与示例补 `--theme`；CHANGELOG。
- 测试：新增 S7-M2 断言（present 12 + chart 12）；双版本全绿不回归（192/192 + SVG 84/84）。
- 版本五件对齐 0.4.0（package.json / SKILL.md / CHANGELOG / CLI --version / MCP serverInfo）；插件 yotta-present-plugin 同步 0.4.0。

## v0.3.0 (2026-09-03)

S7-M1 彩色呈现升级·开源第一步：R1 全面化 + channel×platform 通道映射 + plain 去 emoji（R0 保底无色）。

- 新增渲染通道 `--channel` / MCP `channel`（auto/r0/r1/r2/r3）：auto 按 platform 自动映射——`plain` → `r0`（保底无色、无 emoji 徽章），`webchat`/`discord`/`whatsapp` → `r1`（emoji 增强 Markdown）；显式 `r2`/`r3`（富文本 HTML / SVG 整卡）属高级美化引擎（后续版本推出），当前版本友好报错「尚未开放」。
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
