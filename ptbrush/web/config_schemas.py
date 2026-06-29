"""
PUT /api/config 的输入校验 schema。

跟 PTBrushConfig 区分开：这里接受"前端友好的 {value, unit}"形态，
校验通过后再走 web.config_serializer.to_unit_string 拼成 toml 中的字符串字段。
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from config.config import parse_time_ranges


SizeUnit = Literal["B", "KiB", "MiB", "GiB", "TiB"]
SpeedUnit = Literal["B/s", "KiB/s", "MiB/s", "GiB/s"]


class SizeWithUnit(BaseModel):
    value: float = Field(ge=0)
    unit: SizeUnit


class SpeedWithUnit(BaseModel):
    value: float = Field(ge=0)
    unit: SpeedUnit


class BrushInput(BaseModel):
    min_disk_space: SizeWithUnit
    torrent_max_size: SizeWithUnit
    expect_upload_speed: SpeedWithUnit
    expect_download_speed: SpeedWithUnit
    max_downloading_torrents: int = Field(ge=1, le=100)
    max_no_activate_time: int
    work_time: str = ""
    upload_cycle: int = Field(default=600, ge=60)
    download_cycle: int = Field(default=600, ge=60)

    @field_validator("work_time")
    @classmethod
    def _validate_work_time(cls, v: str) -> str:
        if v:
            parse_time_ranges(v)
        return v


class DownloaderInput(BaseModel):
    url: str
    auth_type: Literal["password", "api_key"] = "password"
    username: str = ""
    password: str = ""
    api_key: str = ""


class HeaderInput(BaseModel):
    key: str
    value: str = ""


class SiteInput(BaseModel):
    name: str
    cookie: str = ""
    headers: List[HeaderInput] = []


class ConfigPayload(BaseModel):
    brush: BrushInput
    downloader: DownloaderInput
    sites: List[SiteInput] = []


class TestDownloaderPayload(BaseModel):
    url: str
    auth_type: Literal["password", "api_key"] = "password"
    username: str = ""
    password: str = ""
    api_key: str = ""


class TestSitePayload(BaseModel):
    name: str
    cookie: str = ""
    headers: List[HeaderInput] = []


class LoginPayload(BaseModel):
    password: str


class ChangePasswordPayload(BaseModel):
    # 当前密码：若当前未启用登录，可传空串
    current_password: str = ""
    # 新密码：传空串表示"关闭登录"
    new_password: str
