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
import re
from typing import List, Optional
from loguru import logger
from config.config import PTBrushConfig, SiteModel
from model import Torrent
from db import Torrent as TorrentDB, BrushTorrent, QBStatus, database
from qbittorrent import QBittorrent
from ptsite import TorrentFetch
import peewee


# 从PT站获取种子
class PtTorrentService():

    def fetcher(self):
        """
        抓取种子，并进行存储
        """
        logger.info(f"开始抓取PT站点FREE种子")
        sites = PTBrushConfig().sites
        count = 0
        for site in sites:
            logger.info(f'开始处理站点:{site.name}')
            torrent_fetcher = TorrentFetch(
                site.name, cookie=site.cookie, headers=site.headers
            )
            for torrent in torrent_fetcher.free_torrents:
                logger.info(f"从{site.name}抓取到种子: {torrent.name}, 大小:{torrent.size}, 做种数:{torrent.seeders}, 下载数:{torrent.leechers}, Free结束时间:{torrent.free_end_time}")
                self._insert_or_update_torrent(torrent)
                count += 1
        logger.info(f"抓取PT站点FREE种子完成，本轮共抓取到{count}个种子")

    def _insert_or_update_torrent(self, torrent: Torrent):
        updated_time = datetime.now()
        logger.info(f"更新或插入种子:{torrent.site} {torrent.id}, 名称:{torrent.name}, 评分:{torrent.score}")
        TorrentDB.insert(name=torrent.name, site=torrent.site, torrent_id=torrent.id, leechers=torrent.leechers, seeders=torrent.seeders,
                         size=torrent.size, free_end_time=torrent.free_end_time, score=torrent.score,
                         ).on_conflict(conflict_target=[TorrentDB.site, TorrentDB.torrent_id], update=dict(
                             updated_time=updated_time, leechers=torrent.leechers, seeders=torrent.seeders, free_end_time=torrent.free_end_time, score=torrent.score)).execute()


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
        logger.info(f"记录QB状态 - 剩余空间: {qb_status.free_space_size}, 下载速度: {qb_status.dlspeed}, 上传速度: {qb_status.upspeed}, 总上传: {qb_status.up_total_size}, 总下载: {qb_status.dl_total_size}")
        QBStatus.create(
            free_space_size=qb_status.free_space_size,
            dlspeed=qb_status.dlspeed,
            upspeed=qb_status.upspeed,

            up_total_size=qb_status.up_total_size,
            dl_total_size=qb_status.dl_total_size,

        )

    def fetcher(self):
        """
        获取所有正在刷流的种子，记录其信息
        """
        logger.info(f"开始抓取qb中种子状态")
        count = 0
        for torrent in self._qb.torrents:
            count += 1
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
            logger.info(f"记录种子状态: {torrent.name}, 上传速度: {torrent.upspeed}, 下载速度: {torrent.dlspeed}, 总上传: {torrent.up_total_size}, 总下载: {torrent.dl_total_size}")
        logger.info(f"抓取qb中种子状态完成，本轮共记录{count}个种子状态")

    def clean_long_time_no_activate(self):
        """
        清理长时间未活动的种子
        """
        logger.info(f"开始清理长时间未活动的种子")
        qb_torrents = self._qb.torrents

        brush_torrents = BrushTorrent.select().group_by(BrushTorrent.torrent)
        torrents = set([brush_torrent.torrent for brush_torrent in brush_torrents])
        logger.info(f"当前共有{len(torrents)}个种子需要检查活动状态")

        cleaned_count = 0
        for torrent in torrents:
            brush_torrent_records = list(BrushTorrent.select().where(BrushTorrent.torrent == torrent).order_by(BrushTorrent.created_time.asc()))
            if not brush_torrent_records:
                continue

            target_qb_torrent = [i for i in qb_torrents if f"{torrent.site}.{torrent.torrent_id}" in i.name]
            if not target_qb_torrent:
                logger.info(f"种子{torrent.name}已从QB中删除，清理相关记录")
                BrushTorrent.delete().where(BrushTorrent.torrent == torrent).execute()
                continue
            target_qb_torrent = target_qb_torrent[0]
            
            latest_record = brush_torrent_records.pop()

            if latest_record.upspeed != 0 or latest_record.dlspeed != 0:
                continue
            
            end_time = latest_record.created_time
            while brush_torrent_records:
                latest_record = brush_torrent_records.pop()
                if latest_record.upspeed != 0 or latest_record.dlspeed != 0:
                    break
            start_time = latest_record.created_time
            inactive_hours = (end_time - start_time).total_seconds() / 3600
            if inactive_hours > 24:
                logger.info(f"删除长时间无活动种子: {torrent.name}, 无活动时长: {inactive_hours:.2f}小时")
                BrushTorrent.delete().where(BrushTorrent.torrent == torrent).execute()
                self._qb.delete_torrent(target_qb_torrent.hash)
                cleaned_count += 1

        logger.info(f"清理完成，共删除{cleaned_count}个长时间无活动种子")
        logger.info(f"开始清理brushtorrent表7天前的记录数据...")
        deleted_count = BrushTorrent.delete().where(BrushTorrent.created_time < (datetime.now() - timedelta(days=7))).execute()
        logger.info(f"清理完成，共删除{deleted_count}条7天前的记录")

        database.execute_sql('VACUUM;')
        logger.info("数据库优化完成")

    def clean_will_expired(self):
        """
        清理临近过期的种子
        """
        logger.info(f'开始清理即将过期的种子')
        count = 0
        current_timestamp = datetime.now().timestamp()
        expire_timestamp = current_timestamp + 3600

        for torrent in self._qb.torrents:
            if torrent.completed:
                continue

            free_timestamp = torrent.free_end_time.timestamp()
            if free_timestamp > expire_timestamp:
                continue

            remaining_time = (torrent.free_end_time - datetime.now()).total_seconds() / 60
            logger.info(f"删除即将过期种子: {torrent.name}, 剩余Free时间: {remaining_time:.2f}分钟")
            self._qb.cancel_download(torrent.hash)
            count += 1

        logger.info(f"清理即将过期的种子完成，本次删除种子数:{count}")

    def torrent_thinned(self):
        """
        对下载中的种子，进行瘦身
        """
        logger.info(f"开始瘦身种子任务...")
        thinned_count = 0
        for torrent in self._qb.torrents:
            if torrent.completed:
                continue

            if torrent.size < self._config.brush.torrent_max_size:
                continue

            files = self._qb.get_torrent_files(torrent.hash)
            all_file_ids = [file['index'] for file in files]
            current_size = sum([file['size'] for file in files if file['priority'] != 0])
            
            logger.info(f"开始瘦身种子: {torrent.name}, 当前大小: {current_size}, 目标大小: {self._config.brush.torrent_max_size}")
            
            download_file_ids = []
            for file in files:
                if file['priority'] != 0:
                    if current_size > self._config.brush.torrent_max_size:
                        file['priority'] = 0
                        current_size -= file['size']
                        logger.info(f"设置文件不下载: {file['name']}, 大小: {file['size']}")
                    else:
                        download_file_ids.append(file['index'])

            no_download_file_ids = list(set(all_file_ids) - set(download_file_ids))
            self._qb.set_no_download_files(torrent.hash, no_download_file_ids)
            logger.info(f"种子瘦身完成: {torrent.name}, 下载文件数: {len(download_file_ids)}, 不下载文件数: {len(no_download_file_ids)}, 最终大小: {current_size}")
            thinned_count += 1

        logger.info(f"瘦身种子任务完成，本次瘦身种子数: {thinned_count}")


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
        logger.info(f"上一个周期({self._config.brush.download_cycle}秒)内的最大下载速度: {avg_dlspeed if avg_dlspeed != None else '未采集'}")
        # 如果还没有采集过qb的信息，那么应该等采集完再决定要不要刷流，因此这里返回最大值
        return avg_dlspeed if avg_dlspeed != None else 9999999999999

    @property
    def qb_free_space_size(self) -> int:
        """
        当前qb剩余空间
        """
        free_space = self._qb.status.free_space_size
        logger.info(f"当前QB剩余空间: {free_space}")
        return free_space

    @property
    def last_cycle_average_upspeed(self) -> int:
        """
        上一个周期内，qb的平均上传速度
        """
        start_time = datetime.now() - timedelta(seconds=self._config.brush.upload_cycle)
        avg_upspeed, = QBStatus.select(peewee.fn.AVG(QBStatus.upspeed)).where(
            QBStatus.created_time > start_time).scalar(as_tuple=True)
        logger.info(f"上一个周期({self._config.brush.upload_cycle}秒)内的平均上传速度: {avg_upspeed if avg_upspeed != None else '未采集'}")
        # 如果还没有采集过qb的信息，那么应该等采集完再决定要不要刷流，因此这里返回最大值
        return avg_upspeed if avg_upspeed != None else 9999999999999

    @property
    def uncompleted_count(self) -> int:
        """
        当前qb中未完成的刷流任务数
        """
        count = len([i for i in self._qb.torrents if i.completed == 0])
        logger.info(f"当前QB中未完成的刷流任务数: {count}")
        return count

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
            logger.info(f"选择种子: {i.name}, 评分: {i.score}, Free结束时间: {i.free_end_time}")

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
        logger.info(f"标记种子已刷流: {torrent.name}")

    def add_brush_torrent(self, torrents: List[Torrent]):
        for torrent in torrents:
            site_config = self._get_site_config(torrent.site)
            if not site_config:
                logger.error(f"未找到站点配置: {torrent.site}, 种子: {torrent.name}")
                continue

            torrent_fetch = TorrentFetch(
                torrent.site, site_config.cookie, site_config.headers)
            torrent_link = torrent_fetch.parse_torrent_link(torrent.id)
            if not torrent_link:
                logger.error(f"解析种子链接失败: {torrent.name}")
                continue
            torrent_rename = f'{torrent.name}__meta.{torrent.site}.{torrent.id}.endTime.{torrent.free_end_time.strftime("%Y-%m-%d-%H:%M:%S")}'
            res = self._qb.download_torrent_url(torrent_link, torrent_rename)
            if res:
                logger.info(f"添加种子成功: {torrent.name}, 大小: {torrent.size}, 做种数: {torrent.seeders}, 下载数: {torrent.leechers}")
                self._set_brushed(torrent)
            else:
                logger.error(f"添加种子失败: {torrent.name}")

    def brush(self):
        """
        刷流入口
        """
        logger.info("开始执行刷流任务...")
        
        # 检查当前qb下载器的剩余空间
        if self.qb_free_space_size < self._config.brush.min_disk_space:
            logger.info(f"QB剩余空间({self.qb_free_space_size})小于配置值({self._config.brush.min_disk_space})，停止刷流")
            return

        # 检查过去一段时间内，qb的下载速度是否超过配置
        if self.last_cycle_max_dlspeed > self._config.brush.expect_download_speed:
            logger.info(f"QB下载速度({self.last_cycle_max_dlspeed})超过配置值({self._config.brush.expect_download_speed})，停止刷流")
            return

        # 检查过去一段时间内，qb的上传速度是否超过配置
        if self.last_cycle_average_upspeed > self._config.brush.expect_upload_speed:
            logger.info(f"QB上传速度({self.last_cycle_average_upspeed})已达到期望值({self._config.brush.expect_upload_speed})，停止刷流")
            return

        # 检查当前刷流任务个数, 同时计算出还需要添加的刷流任务数
        uncompleted_count = self.uncompleted_count
        if uncompleted_count >= self._config.brush.max_downloading_torrents:
            logger.info(f"QB中刷流任务数({uncompleted_count})已达到配置值({self._config.brush.max_downloading_torrents})，停止刷流")
            return
        need_add_count = self._config.brush.max_downloading_torrents - uncompleted_count
        logger.info(f"当前需要添加{need_add_count}个刷流任务")

        # 从种子库中取出评分较高的种子添加至QB中进行刷流
        torrents = self.get_brush_torrent(need_add_count)
        self.add_brush_torrent(torrents)

        logger.info(f"刷流任务完成，本次添加种子数: {len(torrents)}")
