from pathlib import Path
import shutil
from typing import List, Optional, Tuple, Type
from loguru import logger
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


CONFIG_FILE_PATH = Path(__file__).parent.parent / 'data' / "config.toml"


class HeaderParam(BaseModel):
    key: str
    value: str

class OptionParam(BaseModel):
    free_only: Optional[bool] = False  # 是否只获取免费种子

class SiteModel(BaseModel):
    name: str
    cookie: Optional[str] = ""
    options: Optional[OptionParam] = OptionParam()
    headers: Optional[List[HeaderParam]] = []


class QBConfig(BaseModel):
    url: str
    username: str
    password: str


class BrushConfig(BaseModel):

    # 保留最小剩余磁盘空间，单位 B，默认1024GiB即1024 * 1024 * 1024 * 1024，剩余空间小于此值不会再添加新的任务
    min_disk_space: int = 1099511627776

    # 位于下载状态的种子数上限，当qb中下载状态种子数大于此值时不会添加新的任务
    max_downloading_torrents: int = 6

    # 平均速度计算用的时间周期，默认即可，不推荐修改
    upload_cycle: int = 600  # 平均上传速度计算周期，单位秒，默认600秒即10分钟
    download_cycle: int = 600  # 平均下载速度计算周期，单位秒，默认600秒即10分钟

    # 期望达到的整体上传速度，单位 B/s， 推荐设置为上传速率的50%，比如:30M上行速率，推荐设置为 (15/8) * 1024 * 1024 = 1966080
    # 一个时间周期内的平均上传速度大于此值的情况下，不会添加新的任务
    # 刷流：上传速度上限，单位 B/s，默认3932160B/s即30M上传带宽对应值(30 / 8 * 1024 * 1024)。当qb中上传速度大于此值时不会添加新的任务
    expect_upload_speed: int = 1966080

    # 期望达到的整体下载速度，单位 B/s，默认值: 13,107,200 B/s 即 100M下行速率对应的值
    # 一个时间周期内的最大下载速度大于此值的情况下，不会添加新的任务
    # 为什么要有这个逻辑， 因为我发现QB中如果有正在下载的任务且下载速度较快达到了10MiB/s，那么其他正在上传的种子会受到影响上传速度会降低很多。
    # 当但下载任务完成时或下载速度放慢时，其他正在上传的种子会恢复正常上传速度。
    # 因此，当下载速度达到一定值时，不再添加新的任务，避免下载任务过多导致上传速度降低。直到下载速度降低后一段时间，上传速度还没有达标再进行添加新的任务。
    expect_download_speed: int = 13107200

    
    # 单个种子的文件大小限制，超过此限制后，会将种子中的部分文件设置为不下载。
    # 单位为：B，默认值 50GiB，一般不需要修改
    torrent_max_size:int = 53687091200

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


# PTBrushConfig.init_config()
# print(PTBrushConfig().model_dump_json())
