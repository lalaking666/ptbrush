#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
    @File    :   main.py
    @Time    :   2024/11/05 14:38:04
    @Author  :   huihuidehui 
    @Version :   1.0
    @Contact :   kanhuihui@163.com
'''

from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from loguru import logger
import tasks as tasks
# 设置不打印 debug 级别的日志，最小级别为 INFO
logger.remove()  # 移除默认的 handler
logger.add(Path(__file__).parent / 'data' / "ptbrush.log", rotation="10 MB", retention="10 days", level="INFO")


def main():
    
    executors = {"default": ThreadPoolExecutor(max_workers=6)}
    job_defaults = {"coalesce": True, "max_instances": 1}
    scheduler = BlockingScheduler(
        executors=executors, job_defaults=job_defaults)
    scheduler.add_job(tasks.torrent_thinned, "interval", minutes=10)
    scheduler.add_job(tasks.brush, "interval", minutes=15)
    scheduler.add_job(tasks.clean_will_expire_torrents, "interval", minutes=10)
    scheduler.add_job(tasks.fetch_qb_status, "interval", seconds=15)
    scheduler.add_job(tasks.fetch_qb_torrents, "interval", seconds=60)
    scheduler.add_job(tasks.fetch_pt_torrents, "interval", minutes=15, next_run_time=datetime.now()+timedelta(seconds=10))
    scheduler.add_job(tasks.clean_long_time_no_activate_torrents, "interval", hour=1)
    logger.info(f"开始运行，稍后你可以在日志文件中查看日志，观察运行情况...")
    scheduler.start()

if __name__ == "__main__":
    main()