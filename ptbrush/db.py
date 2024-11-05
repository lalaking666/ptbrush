#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   db.py
@Time    :   2024/11/04 09:59:51
@Author  :   huihuidehui 
@Version :   1.0
@Contact :   kanhuihui@163.com
'''

# here put the import lib
from datetime import datetime, timedelta
import peewee

database = peewee.SqliteDatabase('ptbrush.db')


class BaseModel(peewee.Model):
    created_time = peewee.DateTimeField(default=datetime.now)
    updated_time = peewee.DateTimeField(default=datetime.now)

    class Meta:
        database = database


class Torrent(BaseModel):
    name = peewee.CharField()
    site = peewee.CharField(index=True)
    torrent_id = peewee.CharField(index=True)
    leechers = peewee.IntegerField(default=0)
    seeders = peewee.IntegerField(default=0)
    size = peewee.IntegerField(default=0)
    score = peewee.IntegerField(default=0)

    # free结束时间，默认值为当前时间点之后1天
    free_end_time = peewee.DateTimeField()

    brushed = peewee.BooleanField(default=False, index=True)
    
    class Meta:
        # torrend_id和site联合唯一索引
        indexes = (
            (('torrent_id', 'site'), True),
        )

class BrushTorrent(BaseModel):
    torrent = peewee.ForeignKeyField(Torrent, backref='brushes')
    up_total_size = peewee.BigIntegerField(default=0)  # 上传总大小
    upspeed = peewee.IntegerField(default=0)  # 当前上传速度
    
    dl_total_size = peewee.BigIntegerField(default=0) # 下载总大小
    dlspeed = peewee.IntegerField(default=0)  # 当前下载速度


class QBStatus(BaseModel):
    dlspeed = peewee.IntegerField(default=0)    # 当前下载速度
    upspeed = peewee.IntegerField(default=0)    # 当前上传速度
    
    up_total_size = peewee.BigIntegerField(default=0)  # 上传总大小
    dl_total_size = peewee.BigIntegerField(default=0) # 下载总大小
    
    free_space_size:int
    
    


# 建表
database.create_tables([Torrent, BrushTorrent, QBStatus])
