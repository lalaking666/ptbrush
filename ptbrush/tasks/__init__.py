#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   __init__.py
@Time    :   2024/11/04 10:34:05
@Author  :   huihuidehui 
@Version :   1.0
@Contact :   kanhuihui@163.com
'''

# here put the import lib
from ptbrush.tasks.services import PtTorrentService, QBTorrentService, BrushService

# 抓取PT站种子
def fetch_pt_torrents():
    PtTorrentService().fetcher()

# 抓取QB中的种子信息
def fetch_qb_torrents():
    QBTorrentService().fetcher()

# 抓取QB的信息
def fetch_qb_status():
    QBTorrentService().fetch_qb_status()

# 刷流
def brush():
    BrushService().brush()

# 清理即将过期种子
def clean_will_expire_torrents():
    QBTorrentService().clean_will_expired()




if __name__ == "__main__":
    # fetch_pt_torrents()
    fetch_qb_torrents()
    # while True:
    #     fetch_qb_status()
    #     sleep(3)
    # brush()