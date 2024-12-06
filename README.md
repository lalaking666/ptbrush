
## PT全自动刷流工具
受`ptool`启发，用Python实现的一款全自动无感刷流工具，专注刷流功能。目的是做到，QBittorrent下载器中能够25小时不间断的全速上传。目前仅支持`M-Team`，因为我就这一个PT站的账号...





## 使用方法

使用前提：
1. 你需要懂一点命令行，会使用`docker`命令，当然也可以不用命令行来配置(但我手头没有群晖、极空间啥的...不好写教程)
2. 下载器需要为QBittorrent，目前测试通过的是最新版5.0.1，其他版本暂未测试，不保证可用。
3. 暂时只支持`M-Team`，其他PT站暂不支持.



本工具提供`docker-compose`方式一行命令部署。

1. 第一步先找个空文件夹，新建一个`docker-compose.yml`文件，将一下内容复制进去：
    ```yaml
    version: '3.3'
    services:
        ptbrush:
            restart: always
            volumes:
                - './data:/app/data'
            environment:
                - PUID=1000
                - PGID=1000
                - UMASK=022
                - TZ=Asia/Shanghai
            container_name: ptbrush
            image: 'huihuidehui/ptbrush:latest'
    ```
    
    其中的PUID和PGID需要根据你的系统用户ID和组ID进行修改，否则可能无法正常读写文件。


    
2. 在`docker-compose.yml`文件所在目录下，创建一个新的`data`文件夹，用于存储配置文件，以及日志、数据等。

3. 在`data`文件夹下，创建一个新的`config.toml`。

    将以下内容按照实际内容修改后，填写到`config.toml`文件中，一般情况下，只需要修改`[downloader]`和`[[sites]]`部分即可。其他配置项可以看注释来进行修改。
    ```
    # 刷流配置
    [brush]
    # 保留最小剩余磁盘空间，单位 B，默认1024GiB即1024 * 1024 * 1024 * 1024，剩余空间小于此值不会再添加新的任务
    min_disk_space = 1099511627776
    
    # 位于下载状态的种子数上限，当qb中下载状态种子数大于此值时不会添加新的任务
    max_downloading_torrents = 6  
    
    # 平均速度计算用的时间周期，默认即可，不推荐修改
    upload_cycle = 600  # 平均上传速度计算周期，单位秒，默认600秒即10分钟 
    download_cycle = 600 # 平均下载速度计算周期，单位秒，默认600秒即10分钟
    
    # 期望达到的整体上传速度，单位 B/s， 推荐设置为上传速率的50%，比如:30M上行速率，推荐设置为 (15/8) * 1024 * 1024 = 1966080
    # 一个时间周期内的平均上传速度大于此值的情况下，不会添加新的任务
    expect_upload_speed = 1966080  # 刷流：上传速度上限，单位 B/s，默认3932160B/s即30M上传带宽对应值(30 / 8 * 1024 * 1024)。当qb中上传速度大于此值时不会添加新的任务   
    
    # 期望达到的整体下载速度，单位 B/s，默认值: 13,107,200 B/s 即 100M下行速率对应的值
    # 一个时间周期内的最大下载速度大于此值的情况下，不会添加新的任务
    # 为什么要有这个逻辑， 因为我发现QB中如果有正在下载的任务且下载速度较快达到了10MiB/s，那么其他正在上传的种子会受到影响上传速度会降低很多。
    # 当但下载任务完成时或下载速度放慢时，其他正在上传的种子会恢复正常上传速度。
    # 因此，当下载速度达到一定值时，不再添加新的任务，避免下载任务过多导致上传速度降低。直到下载速度降低后一段时间，上传速度还没有达标再进行添加新的任务。
    expect_download_speed = 13107200
    
    
    # 下载器设置，仅支持qb
    [downloader]
    url = "http://127.0.0.1:8080"
    username = ""
    password = ""
    
    # M-Team配置示例，请自行替换x-api-key参数
    [[sites]]
    name = "M-Team"
    [sites.options]
    free_only = false  # 是否只下载免费种子，默认false
    [[sites.headers]]
    key = "x-api-key"
    value = "xxxxx"
    ```
    
4. 最后使用`docker-compose up -d`命令启动即可。



## 注意事项

本工具中涉及到了对大包的拆包操作，因此盒子用户不建议使用`M-Team`对盒子用户拆包规则不友好。建议家宽用户使用.


## 刷流逻辑

详细的刷流逻辑请查看项目中的`README.dev.md`文件。
