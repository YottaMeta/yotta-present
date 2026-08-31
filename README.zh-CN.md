<p align="center"><b>Language</b>: <a href="./README.md">English</a> · 中文</p>

<p align="center">
  <img src="assets/banner.png" alt="yotta-present banner" width="100%" />
</p>

<h1 align="center">yotta-present · 元呈 (YuanCheng)</h1>

<p align="center">YottaMeta 的 <b>通用结果呈现层</b>：把任意 AI 输出（结论 / 表格 / 正文 / 图表 / 报告）
经「<b>内容类型 → 呈现形态</b>」判断后，统一渲染成<b>可复制</b>的 Markdown / 纯文本（按需附本地 SVG）。</p>
<p align="center">触发：默认——凡交付给用户的 AI 输出都先经元呈「判型 → 选形态 → 渲染」为可复制 Markdown / 纯文本再输出；
白名单例外（纯代码 / 命令 / CLI 原始输出、错误堆栈 / 日志、超长走 <code>--out</code>、用户明确一句话 / 裸文本）显式退回原样。
<b>不是图表工具</b>，图表只是呈现形态之一。</p>
<p align="center">零依赖（Python 3.8+ 标准库）；Windows + Linux + macOS；纯本地离线，不联网、不调远程服务。</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue" /></a>
  <a href="https://agentskills.io/"><img alt="Standard: agentskills.io" src="https://img.shields.io/badge/standard-agentskills.io-orange" /></a>
  <a href="https://www.npmjs.com/package/@yottameta/yotta-present"><img alt="npm package" src="https://img.shields.io/npm/v/@yottameta/yotta-present" /></a>
  <a href="https://github.com/YottaMeta/yotta-present"><img alt="GitHub stars" src="https://img.shields.io/github/stars/YottaMeta/yotta-present" /></a>
  <a href="https://github.com/YottaMeta/yotta-present/commits/main"><img alt="last commit" src="https://img.shields.io/github/last-commit/YottaMeta/yotta-present" /></a>
  <a href="https://github.com/YottaMeta/yotta-present"><img alt="PRs welcome" src="https://img.shields.io/badge/PRs-welcome-brightgreen" /></a>
</p>

## 这是什么

AI 输出的内容五花八门、有的难读难复用：纯文本堆砌、乱用表格、直接丢一坨 JSON。元呈 = 一个
「**呈现判断 + 美化修饰**」层：先决定这段内容用什么**形态**（卡片 / 表格 / 正文 / 图表 / 报告…），
再套上元阁统一设计语言，输出**可复制**的 Markdown / 纯文本。用户拿到的是「看着舒服、能直接复制」的结果。

它只负责**呈现**：决定用什么形态并渲染，不改写内容、不替用户做价值判断。

## 核心价值

- **统一呈现**——不管输入是 JSON / Markdown / 纯文本，输出都是元阁一致的设计语言（层级 / 徽章 / 指标 / 注记）。
- **copyable-first**——Markdown（粘贴到任意 Markdown 编辑器）+ 纯文本（粘贴到 Word / 邮件）双输出。
- **AI 自主选择**——智能体按判断层（内容类型 → 形态）主动选形态；未接智能体时 `yotta_present` 确定性兜底 + `--form` 显式指定。
- **本地 SVG**——数值分布 / 趋势 / 占比时，复用 12 图内核在本机生成 SVG，默认 Markdown 内嵌 data URI（自包含可复制）；显式 `--svg` 时写本地 SVG 并以路径引用。
- **判断可解释**——`--explain` 返回「为什么用表格 / 卡片」，避免「AI 乱选」。
- **零依赖离线**——Python 3.8+ 标准库；数据不出本机，不调远程渲染服务。

## 为什么用它

| 优势 | 说明 |
|---|---|
| **通用** | 任何 AI 输出都能接：结论 / 对比 / 清单 / 教程 / 报告 / 图表 |
| **可复制** | Markdown + 纯文本双输出；SVG 仅作增强，不阻塞复制 |
| **本地离线** | 0 matplotlib / canvas / 远程渲染；数据不出本机 |
| **判断层** | 内容类型 → 形态的规则在 SKILL.md（核心深度）；确定性兜底保证没接智能体也能跑 |
| **可解释** | 判断原因可输出，用户知道为什么是这个形态 |
| **生态分发** | GitHub + npm + ClawHub 三源同步；npx / git clone / Download ZIP / install.sh 四种安装方式 |

## 标准内容对象 schema

```json
{
  "title": "安全扫描结果",
  "grade": "success",
  "verdict": "未发现高危风险",
  "metrics": [{"label": "检测点", "value": 8, "unit": "项"}],
  "bullets": ["全部 8 个检测点通过"],
  "notes": ["扫描仅在本机进行"]
}
```

字段：`title / headline / grade|verdict / metrics[] / rows[] / bullets[] / body[] / notes[] / chart_data? / form?`
完整说明见 `references/schema.md`（含 rows 三种形式、chart_data、判断规则、示例）。

## 形态清单（开源基线 8 种）

| 形态 | CLI 名 | 何时用 |
|---|---|---|
| 结论卡 | `conclusion` | 单个结论 / 评分 / 推荐 → 徽章 + 指标 + 要点 |
| 表格交付 | `table` | 行列分明、需对比 / 罗列的数据 |
| 清单卡 | `checklist` | 事项 / 要点 / 清单（支持 `[x]` / `[ ]`） |
| 正文 | `prose` | 叙述 / 说明 / 长段落 |
| 指标板 | `metrics` | 一组关键指标 |
| 问答卡 | `qa` | 问题 / 回答成对 |
| 报告 | `report` | 多节长内容（卡片 + 表 + 文组合 + 目录） |
| 图表 | `chart` | 数值分布 / 趋势 / 占比（本地 SVG，复用 12 图内核） |

## 命令一览

| 命令 | 说明 |
|---|---|
| `--content <JSON\|文本>` | 直接传入内容（JSON 标准对象或 Markdown / 纯文本） |
| `--file <路径>` | 从文件读取内容（UTF-8） |
| `--form <形态>` | 显式指定形态（缺省自动判断） |
| `--md / --text / --both / --json` | 输出 Markdown（默认）/ 纯文本 / 两者 / 完整 JSON |
| `--out <路径>` | 写文件（`--both` 时写 .md 与 .txt；目录按形态命名） |
| `--svg <路径>` | 图表形态：本地 SVG 输出路径 |
| `--explain` | 附判断说明（可解释性） |
| `--list-forms / --version` | 形态清单 / 版本 |

## 使用示例

Windows 用 `python`，Linux/macOS 用 `python3`。

```bash
# 标准内容对象 → 可复制 Markdown（默认）
python3 scripts/yotta_present.py --content '{"title": "结论", "grade": "success", "verdict": "通过", "bullets": ["a", "b"]}'

# 纯文本输入（自动解析 + 兜底美化）
python3 scripts/yotta_present.py --file result.txt

# 纯文本输出（复制到 Word / 邮件）
python3 scripts/yotta_present.py --content '<同上>' --text

# 显式指定形态 + 判断说明
python3 scripts/yotta_present.py --content '<同上>' --form report --explain

# 图表形态：本地 SVG + Markdown 引用
python3 scripts/yotta_present.py --content '{"chart_data": {"chart": "pie", "labels": ["A", "B"], "data": [3, 1]}}' --svg out/pie.svg

# 完整 JSON（程序消费）/ 写文件
python3 scripts/yotta_present.py --content '<同上>' --json
python3 scripts/yotta_present.py --content '<同上>' --out result.md --both
```

退出码：**0** = 成功；**1** = 无输入 / 读取错误；**2** = 内容校验或渲染错误。

## MCP 用法（present_result）

本技能只提供一个公开 MCP server：`yotta-present`（零依赖、数据不出本机）。纯图表**不需要**单独配置
另一个 MCP server——`present_result` 的 `chart` 形态（`chart_data`）直接复用 12 图内核。
AI **首次使用本技能时自动完成配置**（把 server 写入 `mcpServers` 并把护栏写入
永久记忆），用户无需手动改；MCP 未加载时自动降级 CLI，输出一致。

```json
{
  "mcpServers": {
    "yotta-present": {
      "command": "python",
      "args": ["<绝对路径>/scripts/yotta_present_mcp.py"]
    }
  }
}
```

- `present_result`：`content`（JSON / Markdown / 纯文本）+ 可选 `form` / `title` / `output`(md|text|both|json) / `svg` / `explain`；`form=chart` + `chart_data` 复用 12 图内核（bar / line / pie / radar / scatter / histogram / funnel / waterfall / word_cloud / sankey / spreadsheet / treemap），本地 SVG 或 data URI。
- `present_forms`：列出开源基线 8 种形态（只读）。

## 安装

四种方式任选（推荐方式一）：

**方式一：npx 一行装（走 npm 源）**

```bash
npx -y @yottameta/yotta-present --agent <智能体名>     # 按智能体默认用户级目录安装（推荐）
npx -y @yottameta/yotta-present --dir <路径>          # 装到指定目录（改过目录的智能体）
npx -y @yottameta/yotta-present --list                # 查看 智能体 -> 默认目录
```

**方式二：git clone**

```bash
git clone https://github.com/YottaMeta/yotta-present.git
```

**方式三：Download ZIP**

GitHub 仓库页 → `Code` → `Download ZIP`，解压后放入智能体技能目录。

**方式四：install.sh**

```bash
bash install.sh --agent <智能体名>    # 按智能体默认用户级目录安装
bash install.sh --dir <路径>          # 装到指定目录
bash install.sh --list                # 查看 智能体 -> 默认目录
```

安装后即可在智能体中使用：加载技能后按 SKILL.md 判断层选形态，用 `yotta_present` CLI 或 MCP
`present_result` 输出可复制结果。

## 边界（红线）

- **不做图表工具**：图表只是呈现形态之一。
- **copyable-first**：Markdown + 纯文本双输出；SVG 仅增强，不阻塞可复制。
- **数据不出本机**：不联网、不调远程渲染服务。
- **不替代判断**：只负责呈现，不改写内容、不替用户做价值判断。
- **开源与许可**：MIT 开源、能力开放；商标与品牌声明见 [NOTICE](NOTICE)。

## 许可证

[MIT](LICENSE)。商标与品牌声明见 [NOTICE](NOTICE)。
