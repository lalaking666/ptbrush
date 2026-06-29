"""
登录鉴权：login_required 装饰器 + 当前登录状态判定。

策略：
- [web].password 为空 → 所有人都视为已登录（保持对老用户透明）
- [web].password 非空 → session 必须存在 SESSION_KEY 才视为登录
"""
from functools import wraps
from typing import Callable

from flask import jsonify, session

from config.config import PTBrushConfig

SESSION_KEY = "ptbrush_authed"


def is_login_required() -> bool:
    cfg = PTBrushConfig()
    return bool(cfg.web and cfg.web.password)


def is_authenticated() -> bool:
    if not is_login_required():
        return True
    return bool(session.get(SESSION_KEY))


def check_password(password: str) -> bool:
    cfg = PTBrushConfig()
    if not (cfg.web and cfg.web.password):
        return True
    return password == cfg.web.password


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "未登录"}), 401
        return view(*args, **kwargs)

    return wrapped
