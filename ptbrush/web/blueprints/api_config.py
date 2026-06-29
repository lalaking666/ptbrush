from flask import Blueprint, jsonify

from config.config import PTBrushConfig
from ptsite import TorrentFetch
from web.config_serializer import (
    expand_work_time,
    humanize_size,
    humanize_speed,
    mask,
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


@api_config_bp.route("/api/config", methods=["GET"])
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
