# PTBrush

PT 站全自动刷流工具，配合 qBittorrent 使用。目前仅支持 M-Team。

## 技术栈

- Python `>=3.10,<4.0`
- 依赖管理：**uv**（`pyproject.toml` + `uv.lock`），构建后端 hatchling
- 调度：apscheduler（BlockingScheduler）
- 配置：pydantic / pydantic-settings（TOML）
- 存储：peewee + SQLite（WAL 模式）
- HTTP 客户端：qbittorrent-api、requests
- Web：Flask + Flask-CORS + Plotly + Pandas
- 日志：loguru

## 目录结构

```
ptbrush/                       # Python 包，运行时 PYTHONPATH=ptbrush
├── main.py                    # 入口；启动 Web 线程 + apscheduler
├── db.py                      # peewee Models：Torrent / BrushTorrent / QBStatus；migrate_database()
├── model.py                   # 站点抓取用的 pydantic 模型
├── qbittorrent.py             # 封装 qbittorrent-api，定义 QBitorrentTorrent / QBittorrentStatus
├── config/
│   ├── config.py              # PTBrushConfig（从 data/config.toml 读取）；parse_size / parse_speed / parse_time_ranges
│   └── config.example.toml    # 示例配置（启动时缺省会被复制为 data/config.toml）
├── ptsite/
│   ├── __init__.py            # BaseSiteSpider 抽象 + TorrentFetch 工厂（SITE_SPIDER_MAP）
│   └── mteam.py               # M-Team 实现
├── tasks/
│   ├── __init__.py            # 调度任务入口；统一用 @catch_error 包装
│   └── services.py            # PtTorrentService / QBTorrentService / BrushService / vacuum_database
├── web/
│   ├── __init__.py            # create_app()
│   ├── server.py              # start_web_server_thread()
│   └── routes.py              # Flask 蓝图（/、/api/stats 等）
└── data/                      # 运行时目录（挂载卷）：config.toml、ptbrush.db、ptbrush.log
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

## 不要做的事

- 不要把 `requirements.txt` 当作真实依赖来源——`pyproject.toml` 才是。
- 不要在仓库根目录跑 `python ptbrush/main.py`，import 会全部失败。
- 不要在调度里加高频写库 / VACUUM 类任务，前车之鉴见上文。
