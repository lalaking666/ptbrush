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
2. 下载器需要为QBittorrent，目前测试通过的是最新版5.0.1
3. 暂时只支持`M-Team`站点

### 快速部署

PTBrush提供`docker-compose`方式一行命令部署：

1. **创建配置文件**

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

   在`docker-compose.yml`文件所在目录下，创建一个新的`data`文件夹。

3. **配置刷流参数**

   在`data`文件夹下，创建一个新的`config.toml`文件，内容如下：

   ```toml
   # 刷流配置
   [brush]
   # 刷流任务工作时间范围设置
   # 格式说明:
   # - "1-4" 表示每天凌晨1点00分到4点59分工作
   # - "12-18" 表示每天12点00分到18点59分工作
   # - "20-23,0-6" 表示每天20点00分到23点59分以及0点00分到6点59分工作
   # 留空则表示24小时工作
   work_time = ""
   
   # 保留最小剩余磁盘空间，默认值为 1024GiB
   min_disk_space = "1024GiB"
   
   # 位于下载状态的种子数上限
   max_downloading_torrents = 6  
   
   # 期望达到的整体上传速度
   # 推荐设置为上传速率的50%，比如:30Mbps带宽最大上传速度为3.75MiB/s，推荐设置为"1.875MiB/s"
   expect_upload_speed = "1.875MiB/s"
   
   # 期望达到的整体下载速度
   expect_download_speed = "12MiB/s"
   
   # 单个种子的文件大小限制，超过此限制后会进行拆包
   torrent_max_size = "10GiB"
   
   # 允许种子最大的无活跃时间，超过此时间将会被删除，单位为:分钟
   max_no_activate_time = 10
   
   # 下载器设置，仅支持qb
   [downloader]
   url = "http://127.0.0.1:8080"  # 改为你的QBittorrent WebUI地址
   username = ""  # QBittorrent登录用户名
   password = ""  # QBittorrent登录密码
   
   # M-Team配置示例
   [[sites]]
   name = "M-Team"
   [[sites.headers]]
   key = "x-api-key"
   value = "这里替换成你自己的令牌"  # 必须修改为你的API令牌
   ```

   > ⚠️ **注意**：一般情况下，只需要修改`[downloader]`和`[[sites]]`部分即可。

4. **启动服务**

   在`docker-compose.yml`文件所在目录下执行：

   ```bash
   docker-compose up -d
   ```

5. **查看Web界面**

   访问 `http://你的服务器IP:8000` 查看刷流状态。
   > 💡 **提示**：首次启动后请耐心等待1-2小时后再通过web界面查看刷流状态，您可以在`data`文件夹中的`ptbrush.log`里查看详细日志.

   ![Web界面](https://github.com/lalaking666/ptbrush/raw/master/images/screenshot1.png)



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
