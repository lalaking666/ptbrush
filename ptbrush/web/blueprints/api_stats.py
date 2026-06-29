from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from db import BrushTorrent, QBStatus, Torrent
from model import Torrent as TorrentModel

api_stats_bp = Blueprint("api_stats", __name__)


@api_stats_bp.route("/api/stats")
def get_stats():
    try:
        latest_status = QBStatus.select().order_by(QBStatus.created_time.desc()).first()

        active_torrents = (
            BrushTorrent.select(BrushTorrent, Torrent)
            .join(Torrent)
            .where(Torrent.brushed == True)
            .order_by(BrushTorrent.created_time.desc(), BrushTorrent.upspeed.desc())
            .limit(10)
        )

        total_active = (
            BrushTorrent.select(BrushTorrent.torrent)
            .where((BrushTorrent.upspeed > 0) | (BrushTorrent.dlspeed) > 0)
            .where(BrushTorrent.created_time >= datetime.now() - timedelta(minutes=5))
            .distinct()
            .count()
        )

        torrents_data = []
        for bt in active_torrents:
            torrent_model = TorrentModel.model_validate(bt.torrent, from_attributes=True)
            torrents_data.append(
                {
                    "name": torrent_model.name,
                    "site": torrent_model.site,
                    "upspeed": bt.upspeed,
                    "dlspeed": bt.dlspeed,
                    "up_total": bt.up_total_size,
                    "dl_total": bt.dl_total_size,
                    "free_end_time": torrent_model.free_end_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "score": torrent_model.score,
                }
            )

        return jsonify(
            {
                "status": {
                    "upspeed": latest_status.upspeed if latest_status else 0,
                    "dlspeed": latest_status.dlspeed if latest_status else 0,
                    "up_total": latest_status.up_total_size if latest_status else 0,
                    "dl_total": latest_status.dl_total_size if latest_status else 0,
                    "free_space": latest_status.free_space_size if hasattr(latest_status, "free_space_size") else 0,
                    "timestamp": latest_status.created_time.strftime("%Y-%m-%d %H:%M:%S") if latest_status else "",
                },
                "torrents": torrents_data,
                "total_active": total_active,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_stats_bp.route("/api/history")
def get_history():
    try:
        minutes = int(request.args.get("minutes", 10))
        since = datetime.now() - timedelta(minutes=minutes)

        history = (
            QBStatus.select(QBStatus.created_time, QBStatus.upspeed, QBStatus.dlspeed)
            .where(QBStatus.created_time >= since)
            .order_by(QBStatus.created_time)
        )

        data = {"timestamps": [], "upspeed": [], "dlspeed": []}
        for record in history:
            data["timestamps"].append(record.created_time.strftime("%Y-%m-%d %H:%M:%S"))
            data["upspeed"].append(record.upspeed)
            data["dlspeed"].append(record.dlspeed)

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
