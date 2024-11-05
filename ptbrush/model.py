#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   model.py
@Time    :   2024/11/02 14:25:38
@Author  :   huihuidehui 
@Desc    :   None
'''
from datetime import datetime
from math import sqrt
import math
from pydantic import BaseModel, computed_field





class Torrent(BaseModel):
    id:str
    leechers:int = 0
    seeders:int = 0
    name:str
    created_time:datetime
    free_end_time:datetime
    size: int # 字节大小
    site:str
    @computed_field
    def score(self)->int:
        return int((self.leechers/sqrt(self.seeders + 1)) * (math.log(self.size//1024//1024)) * math.log(self.seeders + 1))
        
