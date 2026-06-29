"""
配置 toml 文件读写：备份、原子写、进程内锁、敏感字段 mask 合并。
"""
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Dict

import tomli_w

try:
    import tomllib  # py3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from config.config import CONFIG_FILE_PATH
from web.config_serializer import MASKED_SENTINEL, is_masked

_LOCK = threading.Lock()
_BAK_PATH = Path(str(CONFIG_FILE_PATH) + ".bak")
_TMP_PATH = Path(str(CONFIG_FILE_PATH) + ".tmp")


def read_raw() -> Dict[str, Any]:
    """以原始 dict 形态读 toml；不存在时返回空 dict（不抛错）。"""
    if not Path(CONFIG_FILE_PATH).exists():
        return {}
    with open(CONFIG_FILE_PATH, "rb") as f:
        return tomllib.load(f)


def atomic_write(data: Dict[str, Any]) -> None:
    """
    把整份配置写回 toml：
    1. 先 copy 现有文件到 .bak
    2. tomli_w.dump 到 .tmp
    3. os.replace(.tmp, config.toml) 原子替换
    全程持锁。
    """
    with _LOCK:
        if Path(CONFIG_FILE_PATH).exists():
            shutil.copy2(CONFIG_FILE_PATH, _BAK_PATH)
        with open(_TMP_PATH, "wb") as f:
            tomli_w.dump(data, f)
        os.replace(_TMP_PATH, CONFIG_FILE_PATH)


def merge_with_mask(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    把前端提交的 new 合并到 old：
    - downloader.password、downloader.api_key、sites[i].cookie、sites[i].headers[j].value
      这些敏感字段
      若提交值是 "" 或 "***"，保留 old 中的值
    - 其他字段直接用 new 的
    - 返回新的 dict，old 不会被改
    """
    merged: Dict[str, Any] = dict(new)  # 浅拷贝
    old_downloader = old.get("downloader", {}) or {}
    old_sites = old.get("sites", []) or []

    # downloader.password / downloader.api_key
    dl = dict(merged.get("downloader") or {})
    if is_masked(dl.get("password", "")):
        dl["password"] = old_downloader.get("password", "")
    if is_masked(dl.get("api_key", "")):
        dl["api_key"] = old_downloader.get("api_key", "")
    merged["downloader"] = dl

    # sites[i].cookie 和 headers[j].value
    new_sites = list(merged.get("sites") or [])
    merged_sites = []
    for i, site in enumerate(new_sites):
        site = dict(site)
        old_site = old_sites[i] if i < len(old_sites) and old_sites[i].get("name") == site.get("name") else {}
        # 按 name 匹配回退到老站点的敏感字段
        if not old_site:
            for cand in old_sites:
                if cand.get("name") == site.get("name"):
                    old_site = cand
                    break

        if is_masked(site.get("cookie", "")):
            site["cookie"] = old_site.get("cookie", "")

        new_headers = []
        old_headers = old_site.get("headers", []) or []
        for h in site.get("headers", []) or []:
            h = dict(h)
            if is_masked(h.get("value", "")):
                # 按 key 找老 header 的 value
                for oh in old_headers:
                    if oh.get("key") == h.get("key"):
                        h["value"] = oh.get("value", "")
                        break
                else:
                    h["value"] = ""
            new_headers.append(h)
        site["headers"] = new_headers
        merged_sites.append(site)
    merged["sites"] = merged_sites

    # web.secret_key 不允许前端覆盖；从 old 继承
    web = dict(merged.get("web") or {})
    if "secret_key" in (old.get("web") or {}):
        web["secret_key"] = (old.get("web") or {}).get("secret_key", "")
    if is_masked(web.get("password", "")):
        web["password"] = (old.get("web") or {}).get("password", "")
    merged["web"] = web

    return merged


def ensure_secret_key() -> str:
    """启动时调用：若 [web].secret_key 为空，生成并写回；返回当前 secret_key。"""
    raw = read_raw()
    web = raw.get("web") or {}
    if web.get("secret_key"):
        return web["secret_key"]
    new_key = os.urandom(32).hex()
    web["secret_key"] = new_key
    raw["web"] = web
    atomic_write(raw)
    return new_key
