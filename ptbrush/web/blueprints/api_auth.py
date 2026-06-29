from flask import Blueprint, jsonify, request, session
from pydantic import ValidationError

from web.auth import (
    SESSION_KEY,
    check_password,
    is_authenticated,
    is_login_required,
    login_required,
)
from web.config_schemas import LoginPayload

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
