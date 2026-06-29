import os
from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"


def create_app():
    app = Flask(
        __name__,
        static_folder=str(STATIC_DIR),
        static_url_path="/static",
        template_folder=None,
    )
    CORS(app)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_key_for_ptbrush")

    from web.blueprints.api_config import api_config_bp
    from web.blueprints.api_stats import api_stats_bp

    app.register_blueprint(api_stats_bp)
    app.register_blueprint(api_config_bp)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa(path):
        if path.startswith("api/"):
            return {"error": "Not Found"}, 404
        return send_from_directory(STATIC_DIR, "index.html")

    return app
