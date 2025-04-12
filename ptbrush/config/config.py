from pathlib import Path
import shutil
from typing import List, Optional, Tuple, Type, Union
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
import re
from datetime import time
import datetime


CONFIG_FILE_PATH = Path(__file__).parent.parent / 'data' / "config.toml"


class HeaderParam(BaseModel):
    key: str
    value: str


class SiteModel(BaseModel):
    name: str
    cookie: Optional[str] = ""
    headers: Optional[List[HeaderParam]] = []


class QBConfig(BaseModel):
    url: str
    username: str
    password: str


def parse_size(size: Union[str, int]) -> int:
    """Convert size string with units to bytes
    
    Supports formats like:
    - 1024 (assumed bytes)
    - "1024B"
    - "1KiB", "1MiB", "1GiB", "1TiB"
    - "1KB", "1MB", "1GB", "1TB"
    """
    if isinstance(size, (int, float)):
        return int(size)
        
    size = str(size).upper().strip()
    if size.isdigit():
        return int(size)
        
    units = {
        'B': 1,
        'KIB': 1024,
        'MIB': 1024 ** 2, 
        'GIB': 1024 ** 3,
        'TIB': 1024 ** 4,
        'KB': 1000,
        'MB': 1000 ** 2,
        'GB': 1000 ** 3,
        'TB': 1000 ** 4
    }
    
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([A-Z]+)$', size)
    if not match:
        raise ValueError(f"Invalid size format: {size}")
        
    value, unit = match.groups()
    if unit not in units:
        raise ValueError(f"Invalid unit: {unit}")
        
    return int(float(value) * units[unit])


def parse_speed(speed: Union[str, int]) -> int:
    """Convert speed string with units to bytes per second
    
    Supports formats like:
    - 1024 (assumed B/s)
    - "1KiB/s", "1MiB/s", "1GiB/s"
    """
    if isinstance(speed, (int, float)):
        return int(speed)
        
    speed = str(speed).upper().strip()
    if speed.isdigit():
        return int(speed)
        
    # Handle bytes/s format
    units = {
        'B/S': 1,
        'KIB/S': 1024,
        'MIB/S': 1024 ** 2,
        'GIB/S': 1024 ** 3,
    }
    
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([A-Z/]+)$', speed)
    if not match:
        raise ValueError(f"Invalid speed format: {speed}")
        
    value, unit = match.groups()
    if unit not in units:
        raise ValueError(f"Invalid unit: {unit}")
        
    return int(float(value) * units[unit])


def parse_time_ranges(time_ranges: str) -> list[tuple[time, time]]:
    """Parse time ranges string to list of (start_time, end_time) tuples
    
    Supports formats like:
    - "1-4" (1:00-4:59)
    - "12-18" (12:00-18:59)
    - "20-23,0-6" (20:00-23:59 and 0:00-6:59)
    """
    if not time_ranges:
        return []
        
    result = []
    ranges = time_ranges.split(',')
    
    for time_range in ranges:
        if not re.match(r'^\d{1,2}-\d{1,2}$', time_range):
            raise ValueError(f"Invalid time range format: {time_range}")
            
        start, end = map(int, time_range.split('-'))
        if not (0 <= start <= 23 and 0 <= end <= 23):
            raise ValueError(f"Hours must be between 0-23: {time_range}")
            
        result.append((
            time(hour=start),
            time(hour=end, minute=59, second=59)
        ))
    
    return result


class BrushConfig(BaseModel):

    # 保留最小剩余磁盘空间，支持单位如 "1GiB"、"100MiB" 等，默认单位为B
    min_disk_space: Union[str, int] = 1024 * 1024 * 1024 * 1024

    # 位于下载状态的种子数上限，当qb中下载状态种子数大于此值时不会添加新的任务
    max_downloading_torrents: int = 6

    # 平均速度计算用的时间周期，默认即可，不推荐修改
    upload_cycle: int = 600  # 平均上传速度计算周期，单位秒，默认600秒即10分钟
    download_cycle: int = 600  # 平均下载速度计算周期，单位秒，默认600秒即10分钟

    # 期望达到的整体上传速度，支持以下格式:
    # - 纯数字 (默认单位为B/s)
    # - "1KiB/s", "1MiB/s", "1GiB/s"
    # 推荐设置为上传速率的50%，比如:30MiB/s带宽，推荐设置为"15MiB/s"
    # 默认为1.875MiB/s
    expect_upload_speed: Union[str, int] = 1966080

    # 期望达到的整体下载速度，支持以下格式:
    # - 纯数字 (默认单位为B/s)
    # - "1KiB/s", "1MiB/s", "1GiB/s"
    # 默认值为12MiB/s
    expect_download_speed: Union[str, int] = 12582912

    # 单个种子的文件大小限制，支持以下格式:
    # - 纯数字 (默认单位为B)
    # - "1KiB", "1MiB", "1GiB", "1TiB"
    # 超过此限制后，会将种子中的部分文件设置为不下载
    # 默认值为50GiB
    torrent_max_size: Union[str, int] = 1024 * 1024 * 1024 * 10
    
    # 允许种子最大的无活跃(无下载也无上传)时间，超过此时间将会被删除，单位为:分钟，默认10分钟
    max_no_activate_time: int = 10
    
    # 工作时间范围，格式如: "1-4" 表示1:00-4:59, "20-23,0-6" 表示20:00-23:59和0:00-6:59
    # 留空则表示24小时工作
    work_time: str = "1-3"
    
    @field_validator('min_disk_space')
    def validate_min_disk_space(cls, v):
        try:
            return parse_size(v)
        except ValueError as e:
            raise ValueError(f"Invalid min_disk_space value: {e}")

    @field_validator('expect_upload_speed')
    def validate_expect_upload_speed(cls, v):
        try:
            return parse_speed(v)
        except ValueError as e:
            raise ValueError(f"Invalid expect_upload_speed value: {e}")

    @field_validator('expect_download_speed')
    def validate_expect_download_speed(cls, v):
        try:
            return parse_speed(v)
        except ValueError as e:
            raise ValueError(f"Invalid expect_download_speed value: {e}")

    @field_validator('torrent_max_size')
    def validate_torrent_max_size(cls, v):
        try:
            return parse_size(v)
        except ValueError as e:
            raise ValueError(f"Invalid torrent_max_size value: {e}")

    @field_validator('work_time')
    def validate_work_time(cls, v):
        try:
            parse_time_ranges(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid work_time value: {e}")

    def is_work_time(self) -> bool:
        """Check if current time is in work time ranges"""
        if not self.work_time:
            return True
            
        now = datetime.datetime.now().time()
        ranges = parse_time_ranges(self.work_time)
        return any(start <= now <= end for start, end in ranges)


class PTBrushConfig(BaseSettings):
    downloader: Optional[QBConfig] = None
    sites: Optional[List[SiteModel]] = []
    brush: Optional[BrushConfig] = BrushConfig()

    model_config = SettingsConfigDict(toml_file=str(CONFIG_FILE_PATH))

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls, toml_file=str(CONFIG_FILE_PATH)),)

    @classmethod
    def init_config(cls):
        if not CONFIG_FILE_PATH.exists():
            example_config_path = Path(__file__).parent / "config.example.toml"
            shutil.copy(example_config_path, CONFIG_FILE_PATH)
            logger.info(
                f"配置文件不存在已为您创建新的配置文件：{CONFIG_FILE_PATH.absolute()}"
            )
            logger.info(f"请编辑配置文件添加站点信息以及下载器信息后，开始刷流~")
        else:
            logger.info(
                f"配置文件已存在：{CONFIG_FILE_PATH.absolute()}，跳过初始化配置文件"
            )

    @classmethod
    def override_config(cls, **kwargs):
        example_config_path = Path(__file__).parent / "config.example.toml"
        shutil.copy(example_config_path, CONFIG_FILE_PATH)
        logger.info(f"已覆盖配置文件：{CONFIG_FILE_PATH.absolute()}")

if __name__ == "__main__":
    e = PTBrushConfig()
    e.brush.is_work_time()
# PTBrushConfig.init_config()
# print(PTBrushConfig().model_dump_json())
