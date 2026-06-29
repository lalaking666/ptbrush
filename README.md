# PTBrush - PT全自动刷流工具 🚀

PTBrush是一款专注于PT站点刷流的全自动工具，让你的QBittorrent下载器24小时不间断全速上传！受`ptool`启发，用Python实现，目前支持`M-Team`站点。

## 这是什么？🤔

简单来说，PTBrush是一个能帮你在PT站点自动刷流量的工具。它会：

- 自动从PT站点抓取Free种子 📥
- 智能添加种子到QBittorrent进行下载和做种 🌱
- 自动处理大包种子，只下载部分文件快速进入做种状态 ✂️
- 智能清理长时间无活跃的种子，优化磁盘空间 🧹
- 提供Web界面实时监控刷流状态 📊

## 为什么需要它？💡

- 想要在PT站点提高分享率但没时间手动操作？
- 希望24小时保持上传速度但不知道如何优化？
- 厌倦了手动添加、删除种子的繁琐过程？

PTBrush就是为解决这些问题而生的！它能根据你的网络状况和磁盘空间智能调整刷流策略，让你的上传速度始终保持在理想状态。

## 使用方法 📝

### 使用前提

1. 你需要懂一点命令行，会使用`docker`命令
2. 下载器需要为QBittorrent，已测试通过 5.0.1 以及 5.2.0+（5.2.0+ 还可以用 API Key 登录）
3. 暂时只支持`M-Team`站点

### 快速部署

PTBrush提供`docker-compose`方式一行命令部署，**全部配置都可以在 Web 页面上填，不需要手动写 toml 文件**。

1. **创建 docker-compose.yml**

   找个空文件夹，新建一个`docker-compose.yml`文件，内容如下：

   ```yaml
   version: '3.3'
   services:
       ptbrush:
           restart: always
           volumes:
               - './data:/app/data'
           environment:
               - PUID=1000  # 修改为你的用户ID
               - PGID=1000  # 修改为你的组ID
               - UMASK=022
               - TZ=Asia/Shanghai
               - WEB_PORT=8000
           ports:
               - "8000:8000"
           container_name: ptbrush
           image: 'huihuidehui/ptbrush:latest'
   ```

   > 💡 **提示**：PUID和PGID需要根据你的系统用户ID和组ID进行修改，否则可能无法正常读写文件。

2. **创建数据目录**

   在`docker-compose.yml`文件所在目录下，创建一个新的`data`文件夹。首次启动时 PTBrush 会自动在里面生成一份默认配置。

3. **启动服务**

   ```bash
   docker-compose up -d
   ```

4. **打开 Web 界面填配置**

   访问 `http://你的服务器IP:8000`，会看到仪表盘。如果配置不完整，仪表盘顶部会有一条警告告诉你缺哪些字段。

   点顶部菜单 **"配置"** 进入配置页，填好以下三块即可：

   - **刷流策略**：磁盘保留空间、期望上下传速度（带预设按钮，单位下拉框）、工作时间（24 小时网格点选）
   - **qBittorrent 下载器**：WebUI 地址、认证方式（**用户名密码** 或 **API Key**，后者仅 qBittorrent v5.2.0+ 支持）、对应凭证（旁边有"测试连接"按钮）
   - **PT 站点**：选择站点模板（目前内置 `M-Team`）、Cookie / Header（M-Team 在 Header 里填 `x-api-key`）

   填完点 **"保存"**（页面顶部和底部各有一个按钮），配置会自动写回 `data/config.toml`，最长 15 分钟（一个 cron 周期）后自动生效，**无需重启容器**。

   ![仪表盘](https://github.com/lalaking666/ptbrush/raw/master/images/dashboard.png)

   ![配置页](https://github.com/lalaking666/ptbrush/raw/master/images/config.png)

### Web 端的实用功能

| 功能 | 入口 | 说明 |
|---|---|---|
| 登录密码保护 | 配置页 → "Web 访问" 卡片 | 留空表示不要求登录（默认）；填了之后所有 API 都要登录才能访问 |
| 修改 Web 密码 | 配置页 → "Web 访问" 卡片 | 输入当前密码 + 新密码即可生效；清空新密码可关闭登录（需二次确认） |
| 测试 QB 连接 | 配置页 → "qBittorrent 下载器" 头部 | 不写盘，仅试连一次返回成功/失败原因，支持用户名密码 / API Key 两种认证 |
| 测试站点 | 配置页 → 每个站点卡片头部 | 尝试拉取 5 条 Free 种子验证 cookie / API key |
| 配置不完整提示 | 仪表盘顶部 | 检测到 downloader / sites 缺关键字段时弹出引导 |

### 旧用户：手动编辑 toml 仍然可用

如果你更习惯命令行，直接编辑 `data/config.toml` 一样工作——格式参考下方完整示例。所有 cron 任务每次执行都会重新读取 toml，**改完无需重启**。但要注意：通过 Web UI 保存会丢掉 toml 中的注释（`config.toml.bak` 会保留上一次的版本）。

<details>
<summary>完整的 config.toml 示例（点击展开）</summary>

```toml
# 刷流配置
[brush]
work_time = ""                      # "1-4" / "20-23,0-6" / 留空 = 24 小时
min_disk_space = "1024GiB"
max_downloading_torrents = 6
expect_upload_speed = "1.875MiB/s"  # 推荐为上传带宽的 50%
expect_download_speed = "12MiB/s"
torrent_max_size = "10GiB"
max_no_activate_time = 10           # 分钟

[downloader]
url = "http://127.0.0.1:8080"
# 认证方式："password" 用户名密码；"api_key" qBittorrent v5.2.0+ 的 API Key
auth_type = "password"
username = ""
password = ""
api_key = ""             # auth_type = "api_key" 时使用

[[sites]]
name = "M-Team"
[[sites.headers]]
key = "x-api-key"
value = "你的 API Token"

# 可选：启用 Web 端登录密码
[web]
password = ""                       # 留空 = 不要求登录
```

</details>



## 刷流原理 🧠

PTBrush的刷流逻辑非常智能，主要包括以下几个部分：

### 辅助模块

1. **PT站种子抓取**：定时从PT站获取Free的种子，并保存等待刷流使用。

2. **QBittorrent信息记录**：定时记录下载器状态和种子信息，为刷流决策提供数据支持。

### 刷流模块

涉及三个对种子的操作：新增、删除、拆分。

1. **新增种子逻辑**

   添加新种子需同时满足以下条件：
   - 下载器中未完成种子数小于设定值
   - 下载器当前下载速度不超过阈值
   - 上传速度未达到期望值
   - 剩余磁盘空间充足

2. **删除种子逻辑**

   满足以下任一条件的种子会被删除：
   - 种子临近Free结束时间（默认1小时内）
   - 已完成的种子长时间无活跃（无上传也无下载）

3. **种子拆分规则**

   对于大包种子，PTBrush会智能拆分，只下载部分文件，快速进入做种状态，提高刷流效率。

## 注意事项 ⚠️

- 本工具涉及对大包的拆包操作，因此盒子用户不建议使用，`M-Team`对盒子用户拆包规则不友好。建议家宽用户使用。
- 首次启动后，请查看Web界面确认配置是否生效。
- 如果长时间没有刷流活动，请检查日志文件了解原因。

## 常见问题 ❓

**Q: 为什么我的上传速度一直上不去？**  
A: 原因比较多，排查一下以下几种情况：
   1. `expect_upload_speed`设置过高，导致一上传速度上不去就一直下载种子，进入死循环，建议设置上传带宽的一般就够了，比如30Mbps带宽，可以设置为`1.875MiB/s`
   2. 没有公网IP，或者有公网IP但没有进行qb端口映射
   3. 如果没有公网IP，可以尝试开通IPV6，并放行相应端口


**Q: 磁盘空间会被占满吗？**  
A: 不会，PTBrush会根据`min_disk_space`设置保留足够的磁盘空间，当空间不足时会停止添加新种子。

**Q: 如何获取M-Team的API令牌？**  
A: 登录M-Team网站，在控制台-实验室中找到存取令牌，生成并复制令牌。

---

希望PTBrush能帮你轻松刷流，提高分享率！如有问题，欢迎提交issue。祝你刷流愉快！🎉
