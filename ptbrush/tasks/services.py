#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   task.py
@Time    :   2024/11/04 09:56:17
@Author  :   huihuidehui 
@Version :   1.0
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
        logger.info(f"开始抓取PT站点FREE种子，准备处理{len(sites)}个站点")
        sites = PTBrushConfig().sites
        count = 0
        for site in sites:
            logger.info(f'开始处理站点:{site.name}, 正在初始化抓取器...')
            torrent_fetcher = TorrentFetch(
                site.name, cookie=site.cookie, headers=site.headers
            )
            for torrent in torrent_fetcher.free_torrents:
                logger.info(f"从{site.name}抓取到种子: {torrent.name}, 大小: {torrent.size/1024/1024:.2f}MB, 做种数: {torrent.seeders}, 下载数: {torrent.leechers}, 评分: {torrent.score}")
                self._insert_or_update_torrent(torrent)
                count += 1
            logger.info(f"站点{site.name}处理完成，已抓取{count}个种子")
        logger.info(f"抓取PT站点FREE种子完成，本轮共抓取到{count}个种子，准备进入下一轮抓取")

    def _insert_or_update_torrent(self, torrent: Torrent):
        updated_time = datetime.now()
        logger.info(f"正在更新种子信息: 站点={torrent.site}, ID={torrent.id}, 名称={torrent.name}")
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
        logger.info(f"正在记录QB状态 - 上传速度: {qb_status.upspeed/1024/1024:.2f}MB/s, 下载速度: {qb_status.dlspeed/1024/1024:.2f}MB/s, 剩余空间: {qb_status.free_space_size/1024/1024/1024:.2f}GB")
        QBStatus.create(
            dlspeed=qb_status.dlspeed,
            upspeed=qb_status.upspeed,
            free_space_size=qb_status.free_space_size,
            up_total_size=qb_status.up_total_size,
            dl_total_size=qb_status.dl_total_size,

        )
        pass

    def fetcher(self):
        """
        获取所有正在刷流的种子，记录其信息
        """
        logger.info(f"开始抓取QB中种子状态")
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
            logger.info(f"记录种子状态: {torrent.name} - 上传速度: {torrent.upspeed/1024/1024:.2f}MB/s, 下载速度: {torrent.dlspeed/1024/1024:.2f}MB/s, 已上传: {torrent.up_total_size/1024/1024:.2f}MB, 已下载: {torrent.dl_total_size/1024/1024:.2f}MB")
        logger.info(f"抓取QB中种子状态完成，本轮共记录{count}个种子状态")

    def clean_long_time_no_activate(self):
        """
        清理长时间未活动的种子
        """
        logger.info(f"开始清理长时间未活动的种子")
        qb_torrents = self._qb.torrents

        # 统计出所有正在刷流以及历史刷流的种子ID
        brush_torrents = BrushTorrent.select().group_by(BrushTorrent.torrent)
        torrents = set([brush_torrent.torrent for brush_torrent in brush_torrents])
        logger.info(f"当前数据库中共有{len(torrents)}个种子记录需要检查")
        
        # 处理每个torrent
        cleaned_count = 0
        for torrent in torrents:
            # 查询出所有记录
            brush_torrent_records = list(BrushTorrent.select().where(BrushTorrent.torrent == torrent).order_by(BrushTorrent.created_time.asc()))
            if not brush_torrent_records:
                continue

            # 查询对应的qb中的种子
            target_qb_torrent = [i for i in qb_torrents if f"{torrent.site}.{torrent.torrent_id}" in i.name]
            if not target_qb_torrent:
                # qb中已经删除了此种子，则删除记录
                logger.info(f"种子 {torrent.name} 在QB中已不存在，清理相关记录")
                BrushTorrent.delete().where(BrushTorrent.torrent == torrent).execute()
                continue
            target_qb_torrent = target_qb_torrent[0]
            
            latest_record = brush_torrent_records.pop()

            if latest_record.upspeed != 0 or latest_record.dlspeed != 0:
                # 跳过正在活动的种子
                continue
            
            end_time = latest_record.created_time
            # 统计出无活动的持续时间
            while brush_torrent_records:
                latest_record = brush_torrent_records.pop()
                if latest_record.upspeed != 0 or latest_record.dlspeed != 0:
                    break
            start_time = latest_record.created_time
            if self._config.brush.max_no_activate_time < 5:
                logger.warning(f"max_no_activate_time配置值小于5分钟，使用默认值5分钟")
                max_no_activate_time = 5
            else:
                max_no_activate_time = self._config.brush.max_no_activate_time
            inactive_duration = (end_time - start_time).total_seconds() / 60
            if inactive_duration > max_no_activate_time:
                logger.info(f"清理无活动种子: {torrent.name}, 无活动时长: {inactive_duration:.1f}分钟, 超过配置阈值: {max_no_activate_time}分钟")
                BrushTorrent.delete().where(BrushTorrent.torrent == torrent).execute()
                self._qb.delete_torrent(target_qb_torrent.hash)
                cleaned_count += 1
            
        logger.info(f"开始清理brushtorrent表7天前的历史记录...")
        old_records = BrushTorrent.delete().where(BrushTorrent.created_time < (datetime.now() - timedelta(days=7))).execute()
        logger.info(f"已清理{old_records}条7天前的历史记录")

        # 对数据库瘦身
        logger.info("开始对数据库进行瘦身优化...")
        database.execute_sql('VACUUM;')
        
        logger.info(f"长时间未活动种子清理完成，本次共清理{cleaned_count}个无活动种子")

    def torrent_thinned(self):
        """
        对下载中的种子，进行瘦身
        """
        logger.info(f"开始瘦身种子任务...")
        thinned_count = 0
        for torrent in self._qb.torrents:
            # 跳过已完成任务
            if torrent.completed:
                continue

            # 跳过非大包种子
            if torrent.size < self._config.brush.torrent_max_size:
                continue

            logger.info(f"正在处理大包种子: {torrent.name}, 大小: {torrent.size/1024/1024/1024:.2f}GB")
            files = self._qb.get_torrent_files(torrent.hash)
            all_file_ids = [file['index'] for file in files]

            current_size = sum([file['size']
                               for file in files if file['priority'] != 0])

            download_file_ids = []
            total_files = len(files)
            selected_files = 0
            for file in files:
                if file['priority'] != 0:
                    if current_size > self._config.brush.torrent_max_size:
                        # 超出了大小限制，将文件设置为不下载
                        file['priority'] = 0
                        current_size -= file['size']
                    else:
                        download_file_ids.append(file['index'])
                        selected_files += 1

            no_download_file_ids = list(
                set(all_file_ids) - set(download_file_ids))

            self._qb.set_no_download_files(torrent.hash, no_download_file_ids)
            logger.info(
                f"种子{torrent.name}瘦身完成 - 选择下载: {selected_files}/{total_files}个文件, 预计大小: {current_size/1024/1024:.2f}MB")
            thinned_count += 1

        logger.info(f"瘦身种子任务完成，本次共处理{thinned_count}个大包种子")
        # logger.info(torrent.size)


# 刷流逻辑
class BrushService():
    def __init__(self):
        self._config = PTBrushConfig()
        self._qb = QBittorrent(self._config.downloader.url,
                               self._config.downloader.username, self._config.downloader.password)

    
    def clean_will_expired(self):
        """
        清理临近过期的种子
        """
        logger.info(f'开始清理即将过期的种子')
        count = 0
        current_timestamp = datetime.now().timestamp()
        # 截止时间戳，1小时后
        # 当free时间不足1小时时，取消下载所有文件，但不删除种子，已下载的文件会继续做种.
        expire_timestamp = current_timestamp + 3600
        for torrent in self._qb.torrents:
            if torrent.completed:
                continue

            free_timestamp = torrent.free_end_time.timestamp()
            if free_timestamp > expire_timestamp:
                continue

            logger.info(
                f"删除Free即将结束的种子，种子名称:{torrent.name}, Free结束时间:{torrent.free_end_time}")

            # 直接删除种子
            self._qb.cancel_download(torrent.hash)
            count += 1

        logger.info(f"清理即将过期的种子完成，本次删除种子数:{count}")

    
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
                logger.error(f"获取站点{torrent.site}配置失败，跳过种子{torrent.name}")
                continue
            
            logger.info(f"正在处理种子: {torrent.name} (站点:{torrent.site}, ID:{torrent.id})")
            torrent_fetch = TorrentFetch(
                torrent.site, site_config.cookie, site_config.headers)
            torrent_link = torrent_fetch.parse_torrent_link(torrent.id)
            if not torrent_link:
                logger.error(f"获取种子下载链接失败，跳过种子{torrent.name}")
                continue
            torrent_rename = f'{torrent.name}__meta.{torrent.site}.{torrent.id}.endTime.{torrent.free_end_time.strftime("%Y-%m-%d-%H:%M:%S")}'
            torrent_content = torrent_fetch.download_torrent_content(torrent_link)
            if not torrent_content:
                logger.error(f"下载种子内容失败，跳过种子{torrent.name}")
                continue
            
            res = self._qb.download_torrent_url(torrent_content, torrent_rename)
            if res:
                logger.info(f"成功添加种子到QB: {torrent.name} (大小:{torrent.size/1024/1024:.2f}MB)")
                self._set_brushed(torrent)
            else:
                logger.error(f"添加种子到QB失败: {torrent.name}")

            # return res

    def brush(self)->int:
        """
        刷流入口,返回添加种子的个数
        """
        logger.info(f"刷流任务开始...")
        # 检查当前qb下载器的剩余空间
        if self.qb_free_space_size < self._config.brush.min_disk_space:
            logger.info(f"qb剩余空间不足，停止刷流，当前剩余空间为:{self.qb_free_space_size/1024/1024/1024:.2f}GB")
            return 0

        # 检查过去一段时间内，qb的下载速度是否超过配置
        if self.last_cycle_max_dlspeed > self._config.brush.expect_download_speed:
            logger.info(f"qb下载速度超过配置，停止刷流, 过去一段时间内，qb的最大下载速度为:{self.last_cycle_max_dlspeed/1024/1024:.2f}MB/s")
            return 0

        # 检查过去一段时间内，qb的上传速度是否超过配置
        if self.last_cycle_average_upspeed > self._config.brush.expect_upload_speed:
            logger.info(f"qb上传速度已达到期望值，停止刷流, 过去一段时间内，qb的平均上传速度为:{self.last_cycle_average_upspeed/1024/1024:.2f}MB/s")
            return 0

        # 检查当前刷流任务个数, 同时计算出还需要添加的刷流任务数
        uncompleted_count = self.uncompleted_count
        if uncompleted_count >= self._config.brush.max_downloading_torrents:
            logger.info(f"qb中刷流任务数已达到配置上限({self._config.brush.max_downloading_torrents})，停止刷流")
            return 0
        need_add_count = self._config.brush.max_downloading_torrents - uncompleted_count
        logger.info(f"qb中刷流任务数:{uncompleted_count}, 还需要添加的种子数:{need_add_count}")

        # 从种子库中取出评分较高的种子添加至QB中进行刷流
        torrents = self.get_brush_torrent(need_add_count)
        logger.info(f"从种子库中获取到{len(torrents)}个待添加种子，开始添加到QB中...")
        self.add_brush_torrent(torrents)

        logger.info(f"刷流任务完成，本次成功添加{len(torrents)}个新种子")
        return len(torrents)


