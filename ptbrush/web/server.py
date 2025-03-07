#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   server.py
@Time    :   2025/03/07 17:05:28
@Version :   1.0
'''

# here put the import lib

from ptbrush.web import create_app
import threading

def run_web_server(host='0.0.0.0', port=8000, debug=False):
    """在单独的线程中运行 web 服务器"""
    app = create_app()
    app.run(host=host, port=port, debug=debug, use_reloader=False)

def start_web_server_thread(host='0.0.0.0', port=8000):
    """在后台线程中启动 web 服务器"""
    web_thread = threading.Thread(
        target=run_web_server,
        args=(host, port, False),
        daemon=True
    )
    web_thread.start()
    return web_thread 