import os
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from version import get_version

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"


def create_app():
    app = Flask(
        __name__,
        static_folder=str(STATIC_DIR),
        static_url_path="/static",
        template_folder=None,
    )
    CORS(app, supports_credentials=True)

    # 优先 env，其次从 toml 读取并自动生成
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        from web.config_io import ensure_secret_key
        secret = ensure_secret_key()
    app.config["SECRET_KEY"] = secret
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    from web.blueprints.api_auth import api_auth_bp
    from web.blueprints.api_config import api_config_bp
    from web.blueprints.api_stats import api_stats_bp

    app.register_blueprint(api_auth_bp)
    app.register_blueprint(api_stats_bp)
    app.register_blueprint(api_config_bp)

    @app.route("/api/version")
    def api_version():
        return jsonify({
            "version": get_version(),
            "name": "ptbrush",
        })

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa(path):
        if path.startswith("api/"):
            return jsonify({"error": "Not Found"}), 404
        return send_from_directory(STATIC_DIR, "index.html")

    return app
