# PTBrush

PT 站全自动刷流工具，配合 qBittorrent 使用。目前仅支持 M-Team。

## 技术栈

- Python `>=3.10,<4.0`
- 依赖管理：**uv**（`pyproject.toml` + `uv.lock`），构建后端 hatchling
- 调度：apscheduler（BlockingScheduler）
- 配置：pydantic / pydantic-settings（TOML 读）+ tomli-w（TOML 写）
- 存储：peewee + SQLite（WAL 模式）
- HTTP 客户端：qbittorrent-api、requests
- 后端 Web：Flask（**只返回 JSON**，不渲染 HTML）+ Flask-CORS
- 前端：**纯静态 SPA**——Vue 3 + Vue Router 4 + Element Plus 2，全部走 `<script type="importmap">` + ESM，**不使用任何构建工具**
- 图表：Plotly（仪表盘速度曲线）
- 日志：loguru

## 目录结构

```
ptbrush/                       # Python 包，运行时 PYTHONPATH=ptbrush
├── main.py                    # 入口；启动 Web 线程 + apscheduler
├── db.py                      # peewee Models：Torrent / BrushTorrent / QBStatus；migrate_database()
├── model.py                   # 站点抓取用的 pydantic 模型
├── qbittorrent.py             # 封装 qbittorrent-api，定义 QBitorrentTorrent / QBittorrentStatus
├── config/
│   ├── config.py              # PTBrushConfig / BrushConfig / QBConfig / SiteModel / WebConfig；parse_size/speed/time_ranges
│   └── config.example.toml    # 示例配置（启动时缺省会被复制为 data/config.toml）
├── ptsite/
│   ├── __init__.py            # BaseSiteSpider 抽象 + TorrentFetch 工厂（SITE_SPIDER_MAP）
│   └── mteam.py               # M-Team 实现
├── tasks/
│   ├── __init__.py            # 调度任务入口；统一用 @catch_error 包装
│   └── services.py            # PtTorrentService / QBTorrentService / BrushService / vacuum_database
├── web/                       # Flask 后端（API only）+ 前端静态文件
│   ├── __init__.py            # create_app()；注册蓝图 + SPA catch-all 路由
│   ├── server.py              # start_web_server_thread()
│   ├── auth.py                # login_required 装饰器、session 状态判断
│   ├── config_io.py           # toml 读/原子写/.bak 备份/threading.Lock/敏感字段 mask 合并
│   ├── config_schemas.py      # PUT /api/config 的 input pydantic schema
│   ├── config_serializer.py   # humanize_size/speed、expand/compress_work_time、mask 工具
│   ├── blueprints/
│   │   ├── api_auth.py        # /api/auth/login、logout、state
│   │   ├── api_stats.py       # /api/stats、/api/history（受 login_required 保护）
│   │   └── api_config.py      # GET/PUT /api/config、test-downloader、test-site
│   └── static/                # 前端 SPA 全部静态文件
│       ├── index.html         # 唯一入口（importmap + 挂载点 #app）
│       ├── css/app.css
│       ├── vendor/            # 本地化的第三方资源（无任何 CDN 外链）
│       │   ├── vue.esm-browser.prod.js
│       │   ├── vue-router.esm-browser.prod.js
│       │   ├── element-plus.full.min.mjs
│       │   ├── element-plus.css
│       │   └── plotly-latest.min.js
│       └── js/
│           ├── main.js        # createApp + use(router/ElementPlus) + mount
│           ├── router.js      # Vue Router + beforeEach 鉴权守卫
│           ├── api.js         # fetch 封装，401 自动跳 /login
│           ├── utils.js       # humanize / size/speed/work_time 双向转换 / MASKED_SENTINEL
│           ├── components/    # AppShell、SizeInput、SpeedInput、WorkTimePicker、HeadersEditor、SitesEditor
│           └── views/         # Dashboard / Config / Login
└── data/                      # 运行时目录（挂载卷）：config.toml、ptbrush.db、ptbrush.log、config.toml.bak
tests/                         # pytest，依赖 ptbrush 包导入路径
Dockerfile                     # 基于 python:3.10-slim，用 uv 装依赖
docker-entrypoint.sh           # 处理 PUID/PGID 后 gosu 启动 python main.py
requirements.txt               # 由 `uv export --no-emit-project` 生成，仅供 Docker 镜像使用
```

## 运行方式

### 本地开发

```bash
uv sync                                # 安装依赖到 .venv
PYTHONPATH=ptbrush uv run python ptbrush/main.py
uv run pytest                          # 运行测试
```

注意 `main.py` 内部以 `from config.config import ...` 这种方式导入，**必须把 `ptbrush/` 加入 PYTHONPATH**，不能从仓库根目录直接 `python ptbrush/main.py`。

启动后访问 `http://localhost:8000`（自动跳 `/dashboard`），配置页 `/config`。**前端是 SPA，所有路由（含刷新）都由后端 catch-all 返回 `static/index.html`，Vue Router 接管**。

### Docker

```bash
docker build -t ptbrush .
docker run -v ./data:/app/data -p 8000:8000 ptbrush
```

镜像内通过 `uv pip install --system -r /app/requirements.txt` 安装；改依赖后必须重新生成 requirements.txt：

```bash
uv lock
uv export --no-hashes --no-emit-project -o requirements.txt
```

## 前后端边界

- 后端**只暴露 `/api/*` JSON 端点**，不渲染任何 HTML，不使用 Jinja2 / `render_template` / `url_for`。
- 所有非 `/api/` 非 `/static/` 的路径（如 `/dashboard`、`/config`、`/login`）由 `web/__init__.py:spa()` catch-all 返回 `static/index.html`，前端 Vue Router 接管。
- 前端**禁止任何 CDN 外链**——所有第三方库都本地化在 `static/vendor/`，通过 `<script type="importmap">` 解析裸 import。
- Element Plus 的 `index.full.min.mjs` 内部仍残留 `process.env.NODE_ENV`，所以 `index.html` 在 importmap 之前 inline 一行 `window.process = { env: { NODE_ENV: 'production' } }` 当作 shim，去掉会白屏。

## 调度任务（见 `ptbrush/main.py`）

| Cron | 任务 | 说明 |
|---|---|---|
| `*/10 min` | `torrent_thinned` | 大包种子瘦身（取消下载多余文件） |
| `*/15 min` | `brush`（受 `work_time` 限制） | 新增刷流种子；新增后 sleep 60s 再触发一次瘦身 |
| `*/10 min` | `clean_will_expire_torrents` | 删除临近 Free 结束的种子（默认 1 小时内） |
| `*/15 sec` | `fetch_qb_status` | 抓 QB 全局状态 |
| `* min` | `fetch_qb_torrents` | 抓 QB 中本工具加入的种子状态 |
| `*/30 min` | `fetch_pt_torrents` | 抓 PT 站 Free 列表 |
| `* min` | `clean_long_time_no_activate_torrents` | 删除长时间无活跃种子 |
| `7 days` | `vacuum_database` | SQLite VACUUM；原来按分钟执行会写废 SSD，已拆分 |

工作时间用 `work_time = "20-23,0-6"` 这类格式表达（详见 `parse_time_ranges`）。

## 数据库注意事项

- SQLite 走 WAL，pragmas 在 `db.py:16-25` 里集中配置，特意做了 SSD 寿命优化（`wal_autocheckpoint=10000` 等）。**改 pragma 前请确认背景**：commit `8e61204` 就是为这件事做的。
- 表结构变更走 `migrate_database()` 而不是引入新依赖。当前历史迁移：给 `QBStatus` 加 `free_space_size` 字段。

## 配置

- 运行时配置文件路径写死在 `config/config.py:17`：`ptbrush/data/config.toml`。
- 单位解析：`parse_size`（B / KiB / MiB / GiB / TiB / KB / MB / GB / TB）、`parse_speed`（同上 + `/s`）。pydantic 字段验证器在 config 里。
- 加新 PT 站点 = 在 `ptsite/` 下加一个继承 `BaseSiteSpider` 的类，并注册到 `ptsite/__init__.py` 的 `SITE_SPIDER_MAP`。
- **配置生效**：所有 cron 任务每次执行都构造新的 `PTBrushConfig()` 重读 toml，因此从 UI 保存或手动改 toml **下次任务周期就生效（最长 15 分钟），无需重启**。

### 通过 Web UI 改配置

- `PUT /api/config` 收前端友好形态 `{value, unit}`，经 `config_schemas.ConfigPayload` 校验后由 `config_serializer.to_unit_string` 拼回 `"512GiB"` 这种字符串，再写回 toml。
- 敏感字段（`downloader.password`、`sites[i].cookie`、`sites[i].headers[j].value`）：
  - 后端 GET 时 mask 成 `"***"`
  - 前端编辑表单 placeholder 提示"留空则保留原值"
  - 后端 PUT 时 `config_io.merge_with_mask` 识别 `""` 和 `"***"`两个哨兵，跳过更新使用 old 值
- `web.password` 和 `web.secret_key` 不允许前端通过 PUT 修改（schema 拒绝顶层 `web` 字段）；密码只能手动改 toml。
- 写盘流程：`shutil.copy2` 备份到 `config.toml.bak` → `tomli_w.dump` 写 `.tmp` → `os.replace` 原子替换；全程持 `threading.Lock`。
- 注意：`tomli-w` 不保留注释，UI 保存后会丢，`.bak` 兜底。

### 登录鉴权

- `config.toml` 的 `[web].password` 为空时 **不要求登录**（兼容老用户）。
- 非空时所有 `/api/*` 端点（除 `/api/auth/login`、`/api/auth/state`）+ 前端 `/config` 路由都要求 session。
- `[web].secret_key` 首次启动会由 `config_io.ensure_secret_key()` 自动生成 64 字符 hex 并写回 toml；改了它会让所有现存 session 失效。
- 鉴权代码集中在 `web/auth.py`，session key 是 `SESSION_KEY = "ptbrush_authed"`。

## 不要做的事

- 不要把 `requirements.txt` 当作真实依赖来源——`pyproject.toml` 才是。
- 不要在仓库根目录跑 `python ptbrush/main.py`，import 会全部失败。
- 不要在调度里加高频写库 / VACUUM 类任务，前车之鉴见 commit `8e61204`。
- 不要在前端引入 CDN 外链或构建工具——所有依赖必须本地化到 `static/vendor/`。
- 不要在后端用 Jinja2 / `render_template` / `url_for`——这是前后端分离项目。
- 不要让前端通过 `PUT /api/config` 修改 `web.password` 或 `web.secret_key`——`config_schemas.ConfigPayload` 故意不接收顶层 `web` 字段；修改密码应另起专用端点。
