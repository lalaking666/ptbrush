from flask import Blueprint, render_template, jsonify, request
from db import Torrent, BrushTorrent, QBStatus
from model import Torrent as TorrentModel
import peewee
from datetime import datetime, timedelta
import json

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@main_bp.route('/api/stats')
def get_stats():
    """Get current statistics for the dashboard"""
    try:
        # Get latest QBStatus
        latest_status = QBStatus.select().order_by(QBStatus.created_time.desc()).first()
        
        # Get active torrents
        active_torrents = (BrushTorrent
                          .select(BrushTorrent, Torrent)
                          .join(Torrent)
                          .where(Torrent.brushed == True)
                          .order_by(BrushTorrent.created_time.desc(),BrushTorrent.upspeed.desc())
                          .limit(10))
        
        # 查询created_time在最近5分钟的记录数
        total_active = BrushTorrent.select(BrushTorrent.torrent).where((BrushTorrent.upspeed > 0) | (BrushTorrent.dlspeed) > 0 ).where(BrushTorrent.created_time >= datetime.now() - timedelta(minutes=5)).distinct().count()
        
        # total_active = BrushTorrent.select().join(Torrent).where((BrushTorrent.upspeed > 0) & (BrushTorrent.dlspeed) > 0 ).where(Torrent.brushed == True).count()
        
        # Format data for response
        torrents_data = []
        for bt in active_torrents:
            torrent_model = TorrentModel.model_validate(bt.torrent, from_attributes=True)
            
            torrents_data.append({
                'name': torrent_model.name,
                'site': torrent_model.site,
                'upspeed': bt.upspeed,
                'dlspeed': bt.dlspeed,
                'up_total': bt.up_total_size,
                'dl_total': bt.dl_total_size,
                'free_end_time':torrent_model.free_end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'score': torrent_model.score
            })
        
        return jsonify({
            'status': {
                'upspeed': latest_status.upspeed if latest_status else 0,
                'dlspeed': latest_status.dlspeed if latest_status else 0,
                'up_total': latest_status.up_total_size if latest_status else 0,
                'dl_total': latest_status.dl_total_size if latest_status else 0,
                'free_space': latest_status.free_space_size if hasattr(latest_status, 'free_space_size') else 0,
                'timestamp': latest_status.created_time.strftime('%Y-%m-%d %H:%M:%S') if latest_status else '',
            },
            'torrents': torrents_data,
            'total_active': total_active
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/history')
def get_history():
    """Get historical data for charts"""
    try:
        # Get time range from query params (default to last 10 minutes)
        minutes = int(request.args.get('minutes', 10))
        since = datetime.now() - timedelta(minutes=minutes)
        
        # Get QBStatus records for the time period
        history = (QBStatus
                  .select(QBStatus.created_time, 
                          QBStatus.upspeed, 
                          QBStatus.dlspeed)
                  .where(QBStatus.created_time >= since)
                  .order_by(QBStatus.created_time))
        
        # Format data for charts
        data = {
            'timestamps': [],
            'upspeed': [],
            'dlspeed': []
        }
        
        for record in history:
            data['timestamps'].append(record.created_time.strftime('%Y-%m-%d %H:%M:%S'))
            data['upspeed'].append(record.upspeed)
            data['dlspeed'].append(record.dlspeed)
            
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/config')
def get_config():
    """Get current configuration"""
    from config.config import PTBrushConfig
    
    try:
        config = PTBrushConfig()
        return jsonify({
            'brush': {
                'work_time': config.brush.work_time,
                'min_disk_space': config.brush.min_disk_space,
                'max_downloading_torrents': config.brush.max_downloading_torrents,
                'upload_cycle': config.brush.upload_cycle,
                'download_cycle': config.brush.download_cycle,
                'expect_upload_speed': config.brush.expect_upload_speed,
                'expect_download_speed': config.brush.expect_download_speed,
                'torrent_max_size': config.brush.torrent_max_size,
                'max_no_activate_time': config.brush.max_no_activate_time
            },
            'downloader': {
                'url': config.downloader.url if config.downloader else '',
                'username': config.downloader.username if config.downloader else '',
                'password': bool(config.downloader.password) if config.downloader else False
            },
            'sites': [{
                'name': site.name
                # 'api_key': any(header.key.lower().find('api') >= 0 or header.key.lower().find('key') >= 0 
                #               for header in site.headers) if hasattr(site, 'headers') and site.headers else False
            } for site in config.sites]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 