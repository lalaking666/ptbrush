#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   mteam.py
@Time    :   2024/11/02 14:37:48
@Author  :   huihuidehui 
@Desc    :   None
"""


from datetime import datetime, timedelta
import json
from time import sleep
from typing import Generator, Optional

from loguru import logger
from model import Torrent
from ptsite import BaseSiteSpider
import jsonpath


class MTeamSpider(BaseSiteSpider):
    NAME = "M-Team"
    HOST = "api.m-team.cc"
    API = "api/torrent/search"
    TORRENT_API = "api/torrent/genDlToken"
    PAGE_SIZE = 200
    BODYS = [
        # 电影最新
        {
            "categories": [],
            "mode": "movie",
            "visible": 1,
            "pageNumber": 1,
            "pageSize": 100,
            "sortDirection": "DESC",
            "sortField": "CREATED_DATE",
        },
        # 成人最新
        {
            "categories": [],
            "mode": "adult",
            "visible": 1,
            "pageNumber": 1,
            "pageSize": 100,
            "sortDirection": "DESC",
            "sortField": "CREATED_DATE",
        },
        # 电视最新
        {
            "categories": [],
            "mode": "tvshow",
            "visible": 1,
            "pageNumber": 1,
            "pageSize": 100,
            "sortDirection": "DESC",
            "sortField": "CREATED_DATE",
        },
        # 综合最新
        {
            "categories": [],
            "mode": "normal",
            "visible": 1,
            "pageNumber": 1,
            "pageSize": 100,
            "sortDirection": "DESC",
            "sortField": "CREATED_DATE",
        },
        # 排行榜 下载数最多
        {
            "categories": [],
            "mode": "rankings",
            "visible": 1,
            "pageNumber": 1,
            "pageSize": 100,
            "sortDirection": "DESC",
            "sortField": "LEECHERS",
        },
    ]

    

    def free_torrents(self) -> Generator[Torrent, Torrent, Torrent]:
        for body in self.BODYS:
            logger.debug(
                f"searching mt body:{json.dumps(body, separators=(',', ':'), ensure_ascii=False)}"
            )
            text = self.fetch(
                url=f"https://{self.HOST}/{self.API}",
                method="POST",
                data=json.dumps(body),
            ).text
            try:
                data = json.loads(text).get("data", {}).get("data")
            except:
                logger.error(f"mt search error:{text}, will sleep 60s")
                sleep(60)
                continue
            if data:
                for item in data:

                    # free种子，且有free结束时间
                    if self._is_free_torrent(item) and self._parse_free_end_time(item):
                        yield self._parse_torrent(item)

            # 睡会，别请求太快
            sleep(60)

    def _is_free_torrent(self, item: dict) -> bool:
        """
        满足以下任意即为free,规则如下：
        1. discount = FREE or _2X_FREE
        2. mallSingleFree.status = ONGOING
        """
        discounts = jsonpath.jsonpath(item, "$.status.discount")

        mall_single_free_statuss = jsonpath.jsonpath(
            item, "$.status.mallSingleFree.status")

        if discounts and discounts[0] in ["FREE", "_2X_FREE"]:
            return True
        if mall_single_free_statuss and mall_single_free_statuss[0] == "ONGOING":
            return True
        return False

    def _parse_free_end_time(self, item:dict)->Optional[str]:
        discount_end_times_1 = jsonpath.jsonpath(item, "$.status.discountEndTime")
        if discount_end_times_1 and discount_end_times_1[0]:
            return discount_end_times_1[0]
        discount_end_times_2 = jsonpath.jsonpath(item, "$.status.mallSingleFree.endDate")
        if discount_end_times_2 and discount_end_times_2[0]:
            return discount_end_times_2[0]
        return None
        

    def _parse_torrent(self, item: dict) -> Torrent:
        free_end_time_str = self._parse_free_end_time(item)
        free_end_time = datetime.strptime(free_end_time_str, "%Y-%m-%d %H:%M:%S")

        torrent = Torrent(
            name=item.get("name"),
            id=item.get("id"),
            seeders=item.get("status").get("seeders"),
            leechers=item.get("status").get("leechers"),
            size=int(item.get("size")),
            created_time=datetime.strptime(
                item.get("createdDate"), "%Y-%m-%d %H:%M:%S"
            ),
            free_end_time=free_end_time,
            site=self.NAME
        )

        return torrent

    def parse_torrent_link(self, torrent_id: str) -> str:
        """
        获取种子下载链接
        """
        response = self.fetch(
            url=f"https://{self.HOST}/{self.TORRENT_API}",
            method="POST",
            data={"id": str(torrent_id)},
            timeout=120
        )
        torrent_url = json.loads(response.text).get("data")
        return torrent_url

    def download_torrent_content(self, torrent_link:str)->Optional[bytes]:
        """
        获取种子内容
        """
        torrent_download_res = self.fetch(torrent_link, timeout=30, verify=False)
        try:
            text = torrent_download_res.text
            json.loads(text)
            logger.error(f"mt download torrent link error:{text} link:{torrent_link}")
            return None
        except:
            return torrent_download_res.content
                