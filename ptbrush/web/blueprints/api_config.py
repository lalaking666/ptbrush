from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from config.config import PTBrushConfig
from ptsite import TorrentFetch
from qbittorrent import QBittorrent
from web.auth import login_required
from web.config_io import atomic_write, merge_with_mask, read_raw
from web.config_schemas import (
    ConfigPayload,
    HeaderInput,
    TestDownloaderPayload,
    TestSitePayload,
)
from web.config_serializer import (
    expand_work_time,
    humanize_size,
    humanize_speed,
    mask,
    to_unit_string,
)

api_config_bp = Blueprint("api_config", __name__)


def _serialize_brush(brush) -> dict:
    return {
        "min_disk_space": humanize_size(brush.min_disk_space),
        "torrent_max_size": humanize_size(brush.torrent_max_size),
        "expect_upload_speed": humanize_speed(brush.expect_upload_speed),
        "expect_download_speed": humanize_speed(brush.expect_download_speed),
        "max_downloading_torrents": brush.max_downloading_torrents,
        "max_no_activate_time": brush.max_no_activate_time,
        "work_time": brush.work_time or "",
        "work_time_hours": expand_work_time(brush.work_time or ""),
        "upload_cycle": brush.upload_cycle,
        "download_cycle": brush.download_cycle,
    }


def _serialize_downloader(dl) -> dict:
    if dl is None:
        return {"url": "", "username": "", "password": ""}
    return {
        "url": dl.url,
        "username": dl.username,
        "password": mask(dl.password),
    }


def _serialize_sites(sites) -> list:
    result = []
    for site in sites or []:
        result.append(
            {
                "name": site.name,
                "cookie": mask(site.cookie or ""),
                "headers": [
                    {"key": h.key, "value": mask(h.value)} for h in (site.headers or [])
                ],
            }
        )
    return result


def _payload_to_toml_dict(payload: ConfigPayload) -> dict:
    """把 input schema 转成 toml 写入用的 dict 形态，保留人类可读单位字符串。"""
    b = payload.brush
    brush_dict = {
        "min_disk_space": to_unit_string(b.min_disk_space.value, b.min_disk_space.unit),
        "torrent_max_size": to_unit_string(b.torrent_max_size.value, b.torrent_max_size.unit),
        "expect_upload_speed": to_unit_string(b.expect_upload_speed.value, b.expect_upload_speed.unit),
        "expect_download_speed": to_unit_string(b.expect_download_speed.value, b.expect_download_speed.unit),
        "max_downloading_torrents": b.max_downloading_torrents,
        "max_no_activate_time": b.max_no_activate_time,
        "work_time": b.work_time,
        "upload_cycle": b.upload_cycle,
        "download_cycle": b.download_cycle,
    }
    return {
        "brush": brush_dict,
        "downloader": {
            "url": payload.downloader.url,
            "username": payload.downloader.username,
            "password": payload.downloader.password,
        },
        "sites": [
            {
                "name": s.name,
                "cookie": s.cookie,
                "headers": [{"key": h.key, "value": h.value} for h in s.headers],
            }
            for s in payload.sites
        ],
    }


@api_config_bp.route("/api/config", methods=["GET"])
@login_required
def get_config():
    try:
        config = PTBrushConfig()
        return jsonify(
            {
                "brush": _serialize_brush(config.brush),
                "downloader": _serialize_downloader(config.downloader),
                "sites": _serialize_sites(config.sites),
                "supported_sites": list(TorrentFetch.SITE_SPIDER_MAP.keys()),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_config_bp.route("/api/config", methods=["PUT"])
@login_required
def update_config():
    try:
        payload = ConfigPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "请求格式错误", "details": e.errors()}), 400

    try:
        new_dict = _payload_to_toml_dict(payload)
        old_dict = read_raw()
        merged = merge_with_mask(old_dict, new_dict)

        # 二次校验：跑现有 field_validator（如 parse_size / parse_speed / parse_time_ranges）
        try:
            PTBrushConfig.model_validate(merged)
        except ValidationError as e:
            return jsonify({"error": "配置校验失败", "details": e.errors()}), 400

        atomic_write(merged)
        return jsonify({"ok": True, "message": "已保存，配置将在下次任务周期自动生效（最长 15 分钟）"})
    except Exception as e:
        return jsonify({"error": f"保存失败：{e}"}), 500


def _resolve_secret(value: str, fallback: str) -> str:
    """前端传 *** 或空 → 用 fallback（旧值）；否则用前端的。"""
    return fallback if value in ("", "***") else value


@api_config_bp.route("/api/config/test-downloader", methods=["POST"])
@login_required
def test_downloader():
    try:
        payload = TestDownloaderPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "请求格式错误", "details": e.errors()}), 400

    cfg = PTBrushConfig()
    old_pwd = cfg.downloader.password if cfg.downloader else ""
    password = _resolve_secret(payload.password, old_pwd)

    qb = None
    try:
        qb = QBittorrent(payload.url, payload.username, password)
        # QBittorrent 的 __init__ 已经做了 auth_log_in
        return jsonify({"ok": True, "message": "连接成功"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"连接失败：{e}"}), 200
    finally:
        if qb is not None:
            try:
                qb.close()
            except Exception:
                pass


@api_config_bp.route("/api/config/test-site", methods=["POST"])
@login_required
def test_site():
    try:
        payload = TestSitePayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "请求格式错误", "details": e.errors()}), 400

    if payload.name not in TorrentFetch.SITE_SPIDER_MAP:
        return jsonify({
            "ok": False,
            "message": f"未注册的站点：{payload.name}。支持：{list(TorrentFetch.SITE_SPIDER_MAP.keys())}",
        }), 200

    # 敏感值（cookie/header.value）若为 *** 或空，则从老配置回退
    cfg = PTBrushConfig()
    old_site = None
    for s in cfg.sites or []:
        if s.name == payload.name:
            old_site = s
            break
    old_cookie = old_site.cookie if old_site else ""
    cookie = _resolve_secret(payload.cookie, old_cookie)

    headers = []
    for h in payload.headers:
        old_value = ""
        if old_site:
            for oh in old_site.headers or []:
                if oh.key == h.key:
                    old_value = oh.value
                    break
        headers.append(HeaderInput(key=h.key, value=_resolve_secret(h.value, old_value)))

    try:
        fetcher = TorrentFetch(payload.name, cookie=cookie, headers=headers)
        count = 0
        for _ in fetcher.free_torrents:
            count += 1
            if count >= 5:
                break
        return jsonify({"ok": True, "message": f"成功拉取 {count} 个 Free 种子（演示，仅尝试前 5 条）"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"拉取失败：{e}"}), 200
