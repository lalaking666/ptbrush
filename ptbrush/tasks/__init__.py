#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   __init__.py
@Time    :   2024/11/04 10:34:05
@Author  :   huihuidehui 
@Version :   1.0
'''

# here put the import lib
from time import sleep
from loguru import logger
from tasks.services import PtTorrentService, QBTorrentService, BrushService
# 给所有任务加一个装饰器，进行错误捕获
def catch_error(func):
    def wrapper():
        try:
            func()
        except Exception as e:
            # 这里还需要打印出函数名称
            logger.error(f"任务执行出错: {str(e)}")
    return wrapper



# 抓取PT站种子
@catch_error
def fetch_pt_torrents():
    PtTorrentService().fetcher()

# 抓取QB中的种子信息
@catch_error
def fetch_qb_torrents():
    QBTorrentService().fetcher()

# 抓取QB的信息
@catch_error
def fetch_qb_status():
    QBTorrentService().fetch_qb_status()

# 刷流
@catch_error
def brush():
    add_torrent_count = BrushService().brush()
    if add_torrent_count > 0:
        logger.info(f"1分钟后,开始拆包任务...")
        sleep(60)
        QBTorrentService().torrent_thinned()
    

# 清理长时间没有上传的种子
@catch_error
def clean_long_time_no_activate_torrents():
    QBTorrentService().clean_long_time_no_activate()

# 清理即将过期种子
@catch_error
def clean_will_expire_torrents():
    QBTorrentService().clean_will_expired()

# 对大包种子进行瘦身
@catch_error
def torrent_thinned():
    QBTorrentService().torrent_thinned()

