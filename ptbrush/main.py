#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
    @File    :   main.py
    @Time    :   2024/11/05 14:38:04
    @Author  :   huihuidehui 
    @Version :   1.0
    @Contact :   kanhuihui@163.com
'''

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
import ptbrush.tasks as tasks

def main():
    executors = {"default": ThreadPoolExecutor(max_workers=5)}
    job_defaults = {"coalesce": True, "max_instances": 1}
    scheduler = BlockingScheduler(
        executors=executors, job_defaults=job_defaults)

    scheduler.add_job(tasks.brush, "interval", minutes=15)
    scheduler.add_job(tasks.clean_will_expire_torrents, "interval", minutes=15)
    scheduler.add_job(tasks.fetch_qb_status, "interval", seconds=15)
    scheduler.add_job(tasks.fetch_qb_torrents, "interval", seconds=30)
    scheduler.add_job(tasks.fetch_pt_torrents, "interval", minutes=15)

if __name__ == "__main__":
    main()