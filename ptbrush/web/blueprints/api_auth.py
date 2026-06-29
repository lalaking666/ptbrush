from flask import Blueprint, jsonify, request, session
from pydantic import ValidationError

from web.auth import (
    SESSION_KEY,
    check_password,
    is_authenticated,
    is_login_required,
    login_required,
)
from web.config_io import atomic_write, read_raw
from web.config_schemas import ChangePasswordPayload, LoginPayload

api_auth_bp = Blueprint("api_auth", __name__)


@api_auth_bp.route("/api/auth/state", methods=["GET"])
def state():
    return jsonify({
        "login_required": is_login_required(),
        "authenticated": is_authenticated(),
    })


@api_auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    try:
        payload = LoginPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "请求格式错误", "details": e.errors()}), 400

    if not check_password(payload.password):
        return jsonify({"error": "密码错误"}), 401

    session[SESSION_KEY] = True
    session.permanent = True
    return jsonify({"ok": True})


@api_auth_bp.route("/api/auth/logout", methods=["POST"])
@login_required
def logout():
    session.pop(SESSION_KEY, None)
    return jsonify({"ok": True})


@api_auth_bp.route("/api/auth/change-password", methods=["POST"])
@login_required
def change_password():
    try:
        payload = ChangePasswordPayload.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "请求格式错误", "details": e.errors()}), 400

    if not check_password(payload.current_password):
        return jsonify({"error": "当前密码错误"}), 401

    raw = read_raw()
    web = dict(raw.get("web") or {})
    web["password"] = payload.new_password
    raw["web"] = web
    atomic_write(raw)

    # 改密码后清除当前 session 强制重新登录（除非新密码为空表示关闭登录）
    if payload.new_password:
        session.pop(SESSION_KEY, None)
        return jsonify({"ok": True, "message": "密码已更新，请重新登录", "require_relogin": True})
    return jsonify({"ok": True, "message": "已关闭 Web 登录", "require_relogin": False})
