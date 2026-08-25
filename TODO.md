# TODO.md

依据 `CLAUDE.md` 拆解的分阶段执行计划。每完成一个代码任务，必须同步完成对应的测试任务（先写失败的测试，再实现使其通过），并遵守 `CLAUDE.md` 中的命名规范与技术栈约束。

---

## Phase 1：核心 Python 抓取与邮件逻辑

### 1.1 项目骨架
- [x] 创建 `requirements.txt`（`requests`、`beautifulsoup4`、`pyyaml`、`python-dotenv`，仅限确有必要的依赖）
- [x] 创建 `.env.example`（列出 `RESEND_API_KEY`、`NOTIFY_TO_EMAIL`、`NOTIFY_FROM_EMAIL` 字段说明，不含真实值）
- [x] 创建 `.gitignore`（排除 `.env`、`__pycache__/`、本地测试产物）
- [x] 创建 `config/targets.yaml`，至少填入 1-2 个示例监测目标（name/url/selector/enabled）

### 1.2 `src/storage.py`（快照与历史读写）
- [x] 实现读取/写入 `data/snapshots/<target-id>.json`
- [x] 实现追加写入 `data/history.json`（只追加，不覆盖）
- [x] 编写 `tests/test_storage.py`：验证首次读取不存在快照时返回空/None、写入后能正确读回、追加历史不会丢失已有记录

### 1.3 `src/fetcher.py`（网页抓取）
- [x] 实现基于 `requests` 的 HTML 抓取，处理超时、非 200 状态码
- [x] 编写 `tests/test_fetcher.py`：用 mock/本地固定 HTML 验证正常抓取，以及超时/HTTP 错误时的异常处理路径

### 1.4 `src/extractor.py`（CSS 选择器提取）
- [x] 实现基于 `beautifulsoup4` 的选择器提取 + 文本规范化（去除多余空白）
- [x] 编写 `tests/test_extractor.py`：验证选择器命中/未命中、多元素匹配、空白规范化的边界情况

### 1.5 `src/differ.py`（变动检测）
- [x] 实现内容 hash（SHA-256）计算与新旧 hash 比较，返回是否变动 + 变动前后内容
- [x] 编写 `tests/test_differ.py`：验证内容相同时判定无变动、内容不同时判定有变动且能返回正确的 old/new 值、首次运行（无历史快照）时的处理逻辑

### 1.6 `src/notifier.py`（Resend 邮件通知）
- [x] 实现调用 Resend HTTPS API 发送邮件，支持多个目标变动合并为一封邮件
- [x] API Key 仅通过环境变量读取，不出现任何硬编码
- [x] 编写 `tests/test_notifier.py`：用 mock 请求验证请求体/请求头组装正确、API 返回错误时的处理、多目标合并逻辑

### 1.7 `src/main.py`（编排入口）+ 根目录 `monitor.py`
- [x] 串联 fetcher → extractor → differ → storage → notifier
- [x] 支持从 `config/targets.yaml` 读取多个目标并逐一处理，单个目标失败不应中断整体运行
- [x] 编写 `tests/test_main.py`（或集成测试）：验证多目标场景下变动与未变动目标被正确区分处理
- [x] 新增根目录 `monitor.py` 作为编排入口（内部调用 `src/main.py::run`），满足运行命令的直观命名，同时保留模块化结构

### Phase 1 验收标准
- [x] 本地运行 `python monitor.py` 能对示例目标完成一次完整抓取-比较-（必要时）通知流程（已用 winget 装好 Python 3.12.10 并实际跑通：真实抓取 example.com / httpbin.org、检测变动、缺少 Resend 密钥时优雅跳过通知且不崩溃）
- [x] 所有单元测试可通过 `pytest` 全部通过（19 个测试全部 PASSED）
- [x] `data/snapshots/` 与 `data/history.json` 按预期生成/更新（已验证：无变动时不写 history、有变动时正确追加且不丢失已有记录）

---

## Phase 2：前端可视化展示

### 2.1 面板页面骨架
- [x] 创建 `docs/index.html`，通过 CDN 引入 Chart.js（不引入构建工具/打包器）
- [x] 创建 `docs/assets/app.js`：负责 fetch `docs/data/latest.json`、`docs/data/history.json` 并解析
- [x] 创建 `docs/assets/style.css`：基础样式（列表、卡片、图表容器）

### 2.2 数据展示逻辑
- [x] 实现“最新状态列表”：按目标展示名称、URL、最后检查时间、最新内容摘要（数据来自新增的 `docs/data/latest.json`，因为静态页面无法列目录，需要一份汇总文件——为此同步修改了 `src/main.py`/`src/storage.py` 并补了对应测试）
- [x] 实现“变动趋势图”：按目标分组，用 Chart.js 绘制"累计变动次数"阶梯折线图（时间轴用格式化后的时间字符串作为分类轴，不引入额外的时间适配器库，避免违反“禁止擅自引入第三方”的规则）
- [x] 处理 `data/history.json` 为空或某目标无历史记录时的空态展示

### 2.3 本地验证
- [x] 用 `python -m http.server` 在 `docs/` 目录本地起服务，验证页面能正确加载并渲染示例数据（用 claude-in-chrome 实际打开页面截图确认：空态文案正常、伪造历史数据后趋势图正常渲染、控制台无报错）
- [x] 验证页面在无网络请求密钥、无敏感信息泄露的前提下正常工作（`app.js` 只 fetch 同源 JSON 文件，无任何密钥相关代码）

### Phase 2 验收标准
- [x] 面板能正确读取 Phase 1 产出的数据并渲染图表与列表
- [x] 页面为纯静态资源，不依赖任何后端服务

> **重要架构修正**：原方案里数据落盘目录是仓库根目录的 `data/`，但 GitHub Pages 只发布 Source 指定的 `docs/` 目录，根目录下的 `data/` 部署后前端读取不到。已把 Phase 1 的 `DEFAULT_DATA_DIR` 改为 `docs/data/`（对应修改并同步更新了 `tests/test_storage.py`、`tests/test_main.py`，全部测试重新跑过并通过），CLAUDE.md 的目录结构和第 4/6/7/8 节也已同步更新。

---

## Phase 3：GitHub Actions 自动化与发布

### 3.1 workflow 编写
- [x] 创建 `.github/workflows/monitor.yml`：
  - [x] `on.schedule.cron: '0 0 * * *'`（**每 24 小时一次**，按你的最新要求调整，已同步更新 CLAUDE.md 里原来写的“每小时”描述）+ `on.workflow_dispatch`（支持手动触发）
  - [x] steps：checkout → setup-python 3.12 → 安装 `requirements.txt` → 运行 `python monitor.py`
  - [x] 通过 `env` 注入 `secrets.RESEND_API_KEY`、`secrets.NOTIFY_TO_EMAIL`、`secrets.NOTIFY_FROM_EMAIL`
  - [x] 检测 `docs/data/` 是否有变化，若有则用内置 `GITHUB_TOKEN`（workflow 顶层声明 `permissions: contents: write`）自动 `git commit` + `git push`；YAML 已用 `python -c "import yaml; yaml.safe_load(...)"` 验证语法正确

### 3.2 仓库配置
- [x] 在 Settings → Secrets and variables → Actions 中添加三个密钥（`gh secret list` 确认存在；`NOTIFY_TO_EMAIL` 中途发现填的不是 Resend 注册邮箱导致发信被拒 403，已改成账号自己的注册邮箱 `qimeimeiqi@gmail.com`）
- [x] 在 Settings → Pages 中将 Source 设置为 `docs/` 目录（用 `gh api` 直接设置：`main` 分支 `/docs`，站点 https://qimeimeiqi-hash.github.io/monitor-app/ ）
- [x] 确认 Actions 权限允许 workflow 使用 `GITHUB_TOKEN` 推送提交（仓库默认是 `read`，但 `monitor.yml` 顶层显式声明了 `permissions: contents: write`，会覆盖仓库默认设置；已用真实的 push 结果验证生效）

仓库：https://github.com/qimeimeiqi-hash/monitor-app （public，`git init` 后用 `gh repo create --source=. --push` 创建并推送）

### 3.3 端到端验证
- [x] 手动触发 `workflow_dispatch`，确认 workflow 执行成功（连续跑了 3 次，均 success）
- [x] 制造一次真实变动（改坏一个快照的 content_hash 再 push），验证能正确检测到变动、更新 `docs/data/history.json` 并自动 commit；**发邮件这步中途踩了个坑**：Resend 测试模式下只能发给账号自己的注册邮箱，第一次用错的 `NOTIFY_TO_EMAIL` 导致 API 返回 403（但捕获得很干净，没有让 workflow 崩溃、数据照常落盘），改对邮箱后第二次运行日志里没有 `[ERROR]`，已请你去 `qimeimeiqi@gmail.com` 确认是否真的收到了那封提醒邮件
- [x] 访问 GitHub Pages 面板 URL，确认展示的数据与最新 commit 一致（`curl` 直接验证了 `https://qimeimeiqi-hash.github.io/monitor-app/data/history.json` 返回的内容和仓库里最新 commit 一致）

### Phase 3 验收标准
- [x] 定时任务在无人工干预下按 24 小时稳定运行（`cron: '0 0 * * *'` 已生效，另支持 `workflow_dispatch` 手动触发，三次手动触发全部 success）
- [x] 变动发生时能收到 Resend 邮件提醒（你已确认在 `qimeimeiqi@gmail.com` 收到了提醒邮件）
- [x] GitHub Pages 面板始终反映仓库中最新的 `docs/data/history.json`
- [x] 全流程零成本：全程只用了 public 仓库的 Actions 分钟数、GitHub Pages 免费托管、Resend 免费额度，没有引入任何付费服务

---

## Phase 4：股票价格监测（日本五大商社，2 个月新低提醒）

### 4.1 数据源与核心逻辑
- [x] `src/stock_api.py`：调雅虎财经非官方图表接口拿最近 2 个月每日收盘价，**已用真实请求验证可用**（不是靠文档/搜索猜的——本地直接 curl 了 8001.T 拿到了伊藤忠商事的真实数据，吸取了 Amadeus 那次的教训）；`detect_new_low` 判断"当天收盘价是否严格低于窗口内其它所有交易日"
- [x] `src/stocks_main.py`：编排入口，同一交易日不会重复发提醒邮件（记在 `docs/data/stocks/snapshots/<symbol>.json` 的 `last_alert_date`），单支股票查询失败不影响其他股票
- [x] `stocks.py`：根目录编排入口
- [x] `config/stocks.yaml`：伊藤忠商事、三菱商事、三井物産、住友商事、丸紅，五支股票（不需要价格阈值，判定逻辑是自适应的"是否创新低"，不用像机票那样让你先填个占位值）
- [x] `tests/test_stock_api.py`、`tests/test_stocks_main.py`：15 个新测试全部通过（mock 网络请求，覆盖创新低/未创新低/持平不算新低/同一天不重复提醒/次日更低价再提醒/单支股票出错不影响其他），`pytest` 全量从 22 项增加到 37 项

### 4.2 数据存储与面板
- [x] 数据独立存放在 `docs/data/stocks/`（不与网页监测的 `docs/data/` 混用）
- [x] `docs/index.html` + `docs/assets/app.js` 新增"股票价格·最新状态"和"股票价格·创新低趋势"两个区块，复用已有渲染函数
- [x] **本地真实跑通**（不是 mock）：`python stocks.py` 直接调雅虎财经拿到了五支股票当天的真实收盘价（伊藤忠商事 2118.0、三菱商事 4765.0、三井物産 4949.0、住友商事 1769.0、丸紅 4957.0，均为 JPY），用 Playwright 截图确认面板正确渲染了这份真实数据，控制台除了预期内的 `history.json` 404（还没有任何股票创新低，文件还不存在）之外没有其它报错

### 4.3 GitHub Actions
- [x] `.github/workflows/stocks.yml`：独立于 `monitor.yml` 的定时任务，`cron: '30 7 * * 1-5'`（东证收盘 15:00 JST = 06:00 UTC 后，只在工作日运行），YAML 语法已校验
- [x] **不需要新增任何 Secrets**——数据源免费免注册，邮件复用已有的 `RESEND_API_KEY`/`NOTIFY_TO_EMAIL`/`NOTIFY_FROM_EMAIL`，这一点比机票那次简单很多
- [x] 推送到 GitHub 后手动触发了一次 `workflow_dispatch`，云端 run 全部步骤 success，日志里没有 `[ERROR]`/`[WARN]`，`docs/data/stocks/latest.json` 正确 commit & push，GitHub Pages 面板已同步显示最新数据（`curl` 直接确认过线上返回内容）

### 已知风险 / 需要你留意
- 雅虎财经这个接口是**非官方**的（没有公开文档、不是 Yahoo 承诺维护的公共 API），存在被限流或悄悄改版的可能。当前设计每天只调用 5 次，风险很低，但如果哪天 workflow 突然大批报错，大概率是这个接口的问题，不是代码逻辑坏了。
- "2 个月新低"用的是收盘价，不是盘中最低价；也没有做除权除息调整（如果某支股票期间分红除息，收盘价会有一个技术性下跳，可能被误判为"创新低"——五大商社分红频率不高，短期内概率低，但长期使用需要留意）。

---

## 阶段间依赖说明

- Phase 2 依赖 Phase 1 产出的 `data/history.json` 数据结构，开发 Phase 2 时可先用手工构造的示例 JSON 进行联调，无需等待 Phase 3 完成。
- Phase 3 依赖 Phase 1、Phase 2 已在本地验证通过，避免把未测试的代码直接放到定时任务中反复出错、浪费 Actions 运行次数。
- Phase 4 与 Phase 1-3 相互独立（不同的数据目录、不同的 workflow、不依赖任何额外 Secrets），可以随时接入，不影响已经在跑的网页监测。
