# CLAUDE.md

本文件为 Claude Code 在本仓库中工作的规范说明。

## 项目概述

**网页数据变动监测与邮件提醒工具**：定时抓取指定网页的 HTML 内容，通过 CSS 选择器提取关注区域，与上一次抓取结果比较；检测到变动时通过 Resend API 发送邮件提醒，并将变动历史写入仓库，由 GitHub Pages 上的 Chart.js 面板展示趋势图。

整个项目要求 **100% 零成本**：只使用 GitHub 提供的免费额度（public 仓库 Actions 分钟数无限、GitHub Pages 免费托管）和 Resend 的免费邮件额度，不引入任何需要付费的数据库、服务器或第三方 API。

## 技术栈

- **Python 3.11+**：网页抓取（`requests` + `beautifulsoup4`）、内容比较、生成历史数据
- **Resend API**：免费邮件通知（HTTP API 调用，无需 SMTP 服务器）
- **Chart.js**：前端可视化面板，纯静态页面，托管在 GitHub Pages
- **GitHub Actions**：`schedule` 触发，定时运行抓取任务并自动 commit 结果

不引入数据库、不引入付费云服务、不引入 Node 后端——面板是纯静态 HTML/JS，直接读取仓库中的 JSON 数据文件。

## 目录结构约定

```
.
├── CLAUDE.md
├── config/
│   └── targets.yaml          # 监测目标列表（URL、CSS 选择器、名称等），非敏感信息
├── src/
│   ├── fetcher.py            # 抓取网页 HTML
│   ├── extractor.py          # 用 CSS 选择器从 HTML 提取目标内容
│   ├── differ.py             # 比较本次内容与历史快照，判断是否变动
│   ├── notifier.py           # 调用 Resend API 发送邮件
│   ├── storage.py            # 读写 docs/data/ 下的快照、历史与最新状态 JSON
│   └── main.py                # 编排入口：抓取 -> 比较 -> 通知 -> 落盘
├── monitor.py                 # 根目录编排入口，内部调用 src/main.py::run
├── docs/                      # GitHub Pages 发布目录（Pages Source 设为此目录）
│   ├── index.html             # Chart.js 面板页面
│   ├── assets/
│   │   ├── app.js              # 拉取 docs/data 下 JSON 并渲染列表/图表
│   │   └── style.css
│   └── data/                   # 抓取产出的数据，必须放在 docs/ 内部才能被 Pages 发布
│       ├── snapshots/           # 每个监测目标的最新快照（用于下次比较）
│       ├── latest.json          # 所有目标的最新状态（供“最新状态”列表使用，每次运行整体覆盖）
│       └── history.json         # 所有目标的历史变动记录（只追加），供 Chart.js 读取
├── .github/
│   └── workflows/
│       └── monitor.yml        # 定时任务：每 24 小时运行一次网页抓取脚本并 commit 结果
├── requirements.txt
└── .env.example                # 环境变量示例，不含真实密钥
```

> 数据目录之所以放在 `docs/data/` 而不是仓库根目录的 `data/`，是因为 GitHub Pages 只发布 Source 指向的那一个目录；把数据文件放在 `docs/` 之外，前端页面部署后会读取不到。

## 核心规则

### 1. 模块化

- 每个模块只负责单一职责：`fetcher`（抓取）、`extractor`（提取）、`differ`（比较）、`notifier`（通知）、`storage`（持久化）严格分离，禁止相互耦合业务逻辑。
- `main.py` 只做编排，不写具体实现细节。
- 新增监测目标类型（如未来扩展 JSON API）时，应新增独立的 extractor/fetcher 实现，不得修改既有模块内部逻辑分叉过多的 if/else。

### 2. 密钥与敏感信息管理（硬性要求）

- **禁止**在任何 `.py`、`.yaml`、`.html`、`.yml` 文件中硬编码 API Key、邮箱密码等敏感信息。
- 本地开发：密钥放在 `.env` 文件中（已加入 `.gitignore`），通过 `python-dotenv` 读取；仓库中只保留 `.env.example` 作为字段说明模板，不含真实值。
- GitHub Actions 运行：密钥存放在仓库 **Settings → Secrets and variables → Actions** 中，workflow 通过 `${{ secrets.RESEND_API_KEY }}` 注入为环境变量。
- 涉及的密钥至少包括：
  - `RESEND_API_KEY`：Resend 邮件服务密钥
  - `NOTIFY_TO_EMAIL`：接收提醒的邮箱地址
  - `NOTIFY_FROM_EMAIL`：Resend 已验证的发信地址
- 提交代码前必须确认 `git status` / `git diff` 中不包含任何密钥明文；若不慎提交，需立即在 Resend 后台吊销并重新生成密钥。

### 3. 监测目标配置

- 监测目标（URL、CSS 选择器、显示名称、检测间隔覆盖等）统一写在 `config/targets.yaml`，不写死在 Python 代码里，方便非开发者增减监测项。
- 示例结构：

```yaml
targets:
  - name: "示例商品价格"
    url: "https://example.com/product/123"
    selector: ".price"
    enabled: true
```

### 4. 变动检测逻辑

- 用 CSS 选择器提取目标区域的文本内容，对提取结果做规范化（去除多余空白）后计算 hash（如 SHA-256），与 `docs/data/snapshots/<target-id>.json` 中保存的上次 hash 比较。
- 若 hash 不同，视为“变动”：
  1. 记录本次内容、时间戳、目标名称到 `docs/data/history.json`（追加，不覆盖历史）
  2. 更新 `docs/data/snapshots/<target-id>.json` 为最新内容
  3. 调用 `notifier` 发送邮件提醒
- 若相同，仅更新“最后检查时间”，不触发邮件、不追加历史记录（避免历史文件无限膨胀和邮件骚扰）。
- 每次运行结束后，无论是否变动，都会把所有目标当前的名称/URL/内容/检查时间整体覆盖写入 `docs/data/latest.json`，供面板的“最新状态”列表使用（静态页面无法列目录，需要这份汇总文件）。
- 首次运行（该目标还没有快照）视为建立基线，不算变动、不发邮件，避免新增目标时群发一次误报邮件。

### 5. 邮件通知（Resend）

- 通过 Resend 的 HTTPS API（`https://api.resend.com/emails`）发送，使用 `requests` 直接调用，无需引入 Resend 官方 SDK 增加依赖体积。
- 邮件内容需包含：目标名称、变动时间（UTC 及本地时区）、变动前后内容摘要、原始 URL 链接。
- 单次运行中若多个目标同时变动，应合并为一封邮件发送，避免触发 Resend 免费额度限流。

### 6. GitHub Actions 定时任务

- 触发频率：**每 24 小时一次**（`cron: '0 0 * * *'`，每天 UTC 0 点），写在 `.github/workflows/monitor.yml`，同时保留 `workflow_dispatch` 支持手动触发。
- 任务步骤：checkout → 安装依赖 → 运行 `python monitor.py` → 若 `docs/data/` 有变化，则用内置 `GITHUB_TOKEN`（workflow 中声明 `permissions: contents: write`）自动 `git commit` 并 `push` 回仓库同一分支。
- 因为 GitHub Pages（Source: `docs/` 目录，branch 部署方式）在检测到该目录内容变化时会自动重新发布，所以 workflow 不需要额外的 Pages 部署步骤，commit 推送即完成发布。
- Actions 运行完全在 public 仓库免费额度内，不使用自托管 runner，不使用第三方付费 CI。

### 7. 数据持久化与历史记录

- 不使用任何外部数据库（零成本要求），所有数据以 JSON 文件形式提交回仓库，且必须放在 `docs/data/` 下（详见目录结构一节的说明）：
  - `docs/data/snapshots/<target-id>.json`：单个目标的最新快照，用于下次比较
  - `docs/data/latest.json`：所有目标当前状态的汇总（整体覆盖），供“最新状态”列表使用
  - `docs/data/history.json`：只追加的变动历史，供 Chart.js 绘制趋势图
- `history.json` 每条记录结构：

```json
{
  "target": "示例商品价格",
  "url": "https://example.com/product/123",
  "changed_at": "2026-08-25T06:00:00Z",
  "old_value": "¥199",
  "new_value": "¥179"
}
```

- `history.json` 只做追加（append），不做删除或改写，保证 Chart.js 面板能绘制完整的历史趋势。若文件体积增长过大，可按目标拆分为 `docs/data/history/<target-id>.json`，但需同步更新面板读取逻辑。

### 8. GitHub Pages 面板

- 面板源码放在 `docs/` 目录，通过仓库 Settings 中开启 GitHub Pages（Source: Deploy from a branch，目录选 `docs/`），实现零成本静态托管。
- `docs/index.html` + `docs/assets/app.js` 用原生 JS + Chart.js（通过 CDN 引入）读取同目录下的 `docs/data/latest.json`（最新状态列表）和 `docs/data/history.json`（按目标分组绘制变动趋势图），均为页面同源相对路径 fetch，本地用 `python -m http.server` 在 `docs/` 下起服务即可验证。
- 面板为纯前端展示，不包含任何密钥、不发起需要认证的请求；`history.json`/`latest.json` 为空或某目标暂无历史记录时需展示空态提示，不能渲染出错的图表。

## 开发与提交约定

- 提交前运行本地测试（针对 `differ`、`extractor` 等纯函数模块编写单元测试，放在 `tests/`）。
- commit message 使用简洁的中文或英文均可，但需说明“做了什么”而非过程细节。
- 不引入需要付费套餐才能使用的第三方服务或库；新增依赖前先确认其免费额度是否满足项目量级。

## 希望 AI 遵守的规则（硬性要求）

- **命名规范**：所有变量和函数名必须使用含义明确的英文单词/短语（禁止拼音、禁止无意义缩写如 `tmp1`、`data2`）。
- **同步测试**：只要修改了任何代码文件，必须同步更新对应的测试文件；不允许只改实现不改测试。
- **禁止擅自替换技术栈**：严格按照本文件“技术栈”一节指定的 Python / Resend API / Chart.js / GitHub Actions 编写代码，严禁擅自引入其他第三方库、框架或服务替代它们（例如不得用其他邮件服务替换 Resend，不得用其他图表库替换 Chart.js）。如确有必要变更，须先向用户确认。

## 编写测试代码时的严格遵守事项

以下规则在编写或修改任何测试代码时必须绝对严格遵守：

### 测试代码的质量

- 测试必须对实际功能进行验证，不能是摆设。
- 绝对不要编写像 `expect(true).toBe(true)` 这样毫无意义的测试。
- 每个测试都必须验证“具体的输入”与“预期的输出”之间的对应关系。

### 禁止硬编码（Hardcoding）

- 严禁为了强行通过测试而在测试代码里直接硬填答案（例如让断言直接等于实现返回的字面量，而不是基于业务逻辑推导出的期望值）。
- 严禁在正式代码中加入专门为了测试而设立的分支逻辑（如 `if testMode: ...`）。

### 测试编写原则

- 必须从“失败状态”开始：先写出会失败的测试（红），再编写/修改实现让测试通过（绿）。
- 必须针对边界值、异常流程、错误情况编写测试，不能只测“正常路径”。
- 测试名称必须让人一眼看出“究竟在测试什么”（例如 `test_detects_change_when_selector_text_differs`，而不是 `test_1`）。

### 编写前的确认

- 必须在正确理解需求规范后再编写测试。
- 对于不明确的地方，绝不可凭空假设推进，务必向用户确认后再继续编写。
