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
from config.config import BrushConfig, PTBrushConfig

# 设置不打印 debug 级别的日志，最小级别为 INFO
logger.remove()  # 移除默认的 handler
logger.add(Path(__file__).parent / 'data' / "ptbrush.log", rotation="10 MB", retention="10 days", level="INFO")
config = PTBrushConfig()
def check_work_time(brush_config:BrushConfig):
    """检查当前是否在工作时间内"""
    
    if not brush_config.is_work_time():
        logger.info("当前不在工作时间范围内，跳过任务执行")
        return False
    return True

def run_if_work_time(func):
    """只在工作时间内运行的装饰器"""
    def wrapper():
        if check_work_time(config.brush):
            func()
    return wrapper

def main():
    executors = {"default": ThreadPoolExecutor(max_workers=6)}
    job_defaults = {"coalesce": True, "max_instances": 1}
    scheduler = BlockingScheduler(
        executors=executors, job_defaults=job_defaults)
        
    # 每10分钟执行一次种子瘦身
    scheduler.add_job(
        tasks.torrent_thinned, 
        "cron", 
        minute="*/10"
    )
    
    # 每15分钟执行一次刷流任务，受刷流任务工作时间设置
    scheduler.add_job(
        run_if_work_time(tasks.brush), 
        "cron", 
        minute="*/15"
    )
    
    # 每10分钟检查一次即将过期的种子
    scheduler.add_job(
        tasks.clean_will_expire_torrents, 
        "cron", 
        minute="*/10"
    )
    
    # 每15秒记录一次QB状态
    scheduler.add_job(
        tasks.fetch_qb_status, 
        "cron", 
        second="*/15"
    )
    
    # 每分钟记录一次QB中的种子状态
    scheduler.add_job(
        tasks.fetch_qb_torrents, 
        "cron", 
        minute="*"
    )
    
    # 每15分钟抓取一次PT站的种子
    scheduler.add_job(
        tasks.fetch_pt_torrents, 
        "cron", 
        minute="*/15"
    )
    
    # 每小时清理一次长时间无活跃的种子
    scheduler.add_job(
        tasks.clean_long_time_no_activate_torrents, 
        "cron", 
        minute="0"
    )
    
    logger.info(f"开始运行，稍后你可以在日志文件中查看日志，观察运行情况...")
    scheduler.start()

if __name__ == "__main__":
    main()