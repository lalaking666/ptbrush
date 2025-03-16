#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
    @File    :   main.py
    @Time    :   2024/11/05 14:38:04
    @Author  :   huihuidehui 
    @Version :   1.0
'''

from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from loguru import logger
import tasks as tasks
from config.config import BrushConfig, PTBrushConfig
from web.server import start_web_server_thread
import os
from db import migrate_database

# 设置不打印 debug 级别的日志，最小级别为 INFO
logger.remove()  # 移除默认的 handler
logger.add(Path(__file__).parent / 'data' / "ptbrush.log", rotation="10 MB", retention="10 days", level="INFO")

def check_work_time(brush_config:BrushConfig):
    """检查当前是否在工作时间内"""
    
    if not brush_config.is_work_time():
        logger.info("当前不在工作时间范围内，跳过任务执行")
        return False
    return True

def run_if_work_time(func):
    """只在工作时间内运行的装饰器"""

    def wrapper():
        config = PTBrushConfig()
        if check_work_time(config.brush):
            func()
    return wrapper

def main():
    # 确保数据库结构是最新的
    migrate_database()
    
    # Start web server
    web_port = int(os.environ.get('WEB_PORT', 8000))
    web_thread = start_web_server_thread(port=web_port)
    logger.info(f"Web界面已启动，端口: {web_port}")
    
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
        minute="*/30"
    )
    
    # 每3分钟清理一次长时间无活跃的种子
    scheduler.add_job(
        tasks.clean_long_time_no_activate_torrents, 
        "cron", 
        minute="*"
    )
    
    logger.info(f"开始运行，稍后你可以在日志文件中查看日志，观察运行情况...")
    logger.info(f"Web界面已启动，访问 http://your-server-ip:{web_port} 查看刷流状态")
    scheduler.start()

if __name__ == "__main__":
    main()