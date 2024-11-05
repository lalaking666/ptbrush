#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   task.py
@Time    :   2024/11/04 09:56:17
@Author  :   huihuidehui 
@Version :   1.0
@Contact :   kanhuihui@163.com
'''


from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger
from ptbrush.config.config import PTBrushConfig, SiteModel
from ptbrush.model import Torrent
from ptbrush.db import Torrent as TorrentDB, BrushTorrent, QBStatus
from ptbrush.qbittorrent import QBittorrent
from ptbrush.site import TorrentFetch
import peewee


# 从PT站获取种子
class PtTorrentService():

    def fetcher(self):
        """
        抓取种子，并进行存储
        """
        logger.info(f"开始抓取PT站点FREE种子")
        sites = PTBrushConfig().sites
        for site in sites:
            logger.info(f'开始处理站点:{site.name}')
            torrent_fetcher = TorrentFetch(
                site.name, cookie=site.cookie, headers=site.headers
            )
            for torrent in torrent_fetcher.free_torrents:
                logger.info(f"从{site.name}抓取到种子: {torrent.name}")
                self._insert_or_update_torrent(torrent)

        logger.info(f"抓取PT站点FREE种子完成")
        
    def _insert_or_update_torrent(self, torrent: Torrent):
        updated_time = datetime.now()
        logger.info(f"insert or update torrent:{torrent.site} {torrent.id}")
        TorrentDB.insert(name=torrent.name, site=torrent.site, torrent_id=torrent.id, leechers=torrent.leechers, seeders=torrent.seeders,
                         size=torrent.size, free_end_time=torrent.free_end_time, score=torrent.score,
                         ).on_conflict(conflict_target=[TorrentDB.site, TorrentDB.torrent_id], update=dict(
                             updated_time=updated_time, leechers=torrent.leechers, seeders=torrent.seeders, free_end_time=torrent.free_end_time, score=torrent.score)).execute()
        pass


# 从qb获取种子状态、以及下载器状态、 清理临近过期的种子
class QBTorrentService():

    def __init__(self):
        self._config = PTBrushConfig()
        self._qb = QBittorrent(self._config.downloader.url,
                               self._config.downloader.username, self._config.downloader.password)

    def fetch_qb_status(self):
        """
        获取qb状态
        """
        qb_status = self._qb.status
        logger.info(f"Record qb status: {qb_status}")
        QBStatus.create(
            free_space_size=qb_status.free_space_size,
            dlspeed=qb_status.dlspeed,
            upspeed=qb_status.upspeed,

            up_total_size=qb_status.up_total_size,
            dl_total_size=qb_status.dl_total_size,

        )
        pass

    def fetcher(self):
        """
        获取所有正在刷流的种子，记录其信息
        """
        for torrent in self._qb.torrents:
            torrent_db, flag = TorrentDB.get_or_create(
                site=torrent.site, torrent_id=torrent.torrent_id, defaults={'name': torrent.name, 'brushed': True, 'free_end_time': torrent.free_end_time})
            torrent_db.brushed = True
            torrent_db.save()
            BrushTorrent.create(
                torrent=torrent_db,
                up_total_size=torrent.up_total_size,
                upspeed=torrent.upspeed,
                dl_total_size=torrent.dl_total_size,
                dlspeed=torrent.dlspeed,
            )
            logger.info(f"Record brush torrent status: {torrent.name}")

    def clean_will_expired(self):
        """
        清理临近过期的种子
        """
        logger.info(f'开始清理即将过期的种子')
        count = 0
        current_timestamp = datetime.now().timestamp()
        # 截止时间戳，1小时后
        # 当free时间不足1小时时，直接删除
        expire_timestamp = current_timestamp + 3600
        for torrent in self._qb.torrents:
            if torrent.completed:
                continue

            free_timestamp = torrent.free_end_time.timestamp()
            if expire_timestamp > free_timestamp:
                continue

            logger.info(
                f"Delete torrent where will to expire {torrent.name}, free end time:{torrent.free_end_time}")
            
            # 直接删除种子
            self._qb.delete(torrent.hash)
            count += 1
    
        logger.info(f"清理即将过期的种子完成，本次删除种子数:{count}")

# 刷流逻辑
class BrushService():
    def __init__(self):
        self._config = PTBrushConfig()
        self._qb = QBittorrent(self._config.downloader.url,
                               self._config.downloader.username, self._config.downloader.password)

    @property
    def last_cycle_max_dlspeed(self) -> int:
        """
        上一个周期内，qb的最大下载速度
        """
        start_time = datetime.now() - timedelta(seconds=self._config.brush.download_cycle)
        avg_dlspeed,  = QBStatus.select(peewee.fn.MAX(QBStatus.dlspeed)).where(
            QBStatus.created_time > start_time).scalar(as_tuple=True)
        # 如果还没有采集过qb的信息，那么应该等采集完再决定要不要刷流，因此这里返回最大值
        return avg_dlspeed if avg_dlspeed != None else 9999999999999

    @property
    def qb_free_space_size(self) -> int:
        """
        当前qb剩余空间
        """
        return self._qb.status.free_space_size

    @property
    def last_cycle_average_upspeed(self) -> int:
        """
        上一个周期内，qb的平均上传速度
        """
        start_time = datetime.now() - timedelta(seconds=self._config.brush.upload_cycle)
        avg_upspeed, = QBStatus.select(peewee.fn.AVG(QBStatus.upspeed)).where(
            QBStatus.created_time > start_time).scalar(as_tuple=True)
        # 如果还没有采集过qb的信息，那么应该等采集完再决定要不要刷流，因此这里返回最大值
        return avg_upspeed if avg_upspeed != None else 9999999999999

    @property
    def uncompleted_count(self) -> int:
        """
        当前qb中未完成的刷流任务数
        """
        return len([i for i in self._qb.torrents if i.completed == 0])

    def get_brush_torrent(self, count: int = 10) -> List[Torrent]:
        # 至少要留3个小时来下载
        now = datetime.now() + timedelta(hours=3)
        torrents_db = TorrentDB.select().where((TorrentDB.free_end_time > now) & (TorrentDB.brushed == False)).order_by(
            TorrentDB.score.desc()).limit(count)
        result = []
        for i in torrents_db:
            result.append(Torrent(
                id=i.torrent_id,
                leechers=i.leechers,
                name=i.name,
                seeders=i.seeders,
                created_time=i.created_time,
                free_end_time=i.free_end_time,
                size=i.size,
                site=i.site,
            ))

        return result

    def _get_site_config(self, site: str) -> Optional[SiteModel]:
        for i in self._config.sites:
            if i.name == site:
                return i
        return None

    def _set_brushed(self, torrent: Torrent):
        torrent_db = TorrentDB.get_or_none(
            TorrentDB.site == torrent.site, TorrentDB.torrent_id == torrent.id)
        torrent_db.brushed = True
        torrent_db.save()

    def add_brush_torrent(self, torrents: List[Torrent]):
        for torrent in torrents:
            site_config = self._get_site_config(torrent.site)
            if not site_config:
                logger.error(f"torrent site config empty, {torrent}")
                continue

            torrent_fetch = TorrentFetch(
                torrent.site, site_config.cookie, site_config.headers)
            torrent_link = torrent_fetch.parse_torrent_link(torrent.id)
            if not torrent_link:
                logger.error(f"torrent parse link empty, {torrent}")
                continue
            torrent_rename = f'{torrent.name}__meta.{torrent.site}.{torrent.id}.endTime.{torrent.free_end_time.strftime("%Y-%m-%d-%H:%M:%S")}'
            res = self._qb.download_torrent_url(torrent_link, torrent_rename)
            if res:
                logger.info(f"add torrent {torrent} success")
                self._set_brushed(torrent)

            # return res

    def brush(self):
        """
        刷流入口
        """

        # 检查当前qb下载器的剩余空间
        if self.qb_free_space_size < self._config.brush.min_disk_space:
            logger.warning(f"qb剩余空间不足，停止刷流")
            return

        # 检查过去一段时间内，qb的下载速度是否超过配置
        if self.last_cycle_max_dlspeed > self._config.brush.expect_download_speed:
            logger.warning(f"qb下载速度超过配置，停止刷流")
            return

        # 检查过去一段时间内，qb的上传速度是否超过配置
        if self.last_cycle_average_upspeed > self._config.brush.expect_upload_speed:
            logger.warning(f"qb上传速度已达到期望值，停止刷流")
            return

        # 检查当前刷流任务个数, 同时计算出还需要添加的刷流任务数
        uncompleted_count = self.uncompleted_count
        if uncompleted_count >= self._config.brush.max_downloading_torrents:
            logger.warning(f"qb中刷流任务数已达到配置，停止刷流")
            return
        need_add_count = self._config.brush.max_downloading_torrents - uncompleted_count

        # 从种子库中取出评分较高的种子添加至QB中进行刷流
        torrents = self.get_brush_torrent(need_add_count)
        self.add_brush_torrent(torrents)

        logger.info(f"刷流完成...")
