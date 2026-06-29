from types import SimpleNamespace

from flask import Flask

from web.blueprints import api_config


def _config(downloader):
    return SimpleNamespace(downloader=downloader, sites=[SimpleNamespace(
        name="M-Team",
        cookie="",
        headers=[SimpleNamespace(key="x-api-key", value="site-key")],
    )])


def _health_json(mocker, cfg):
    mocker.patch.object(api_config, "PTBrushConfig", return_value=cfg)
    app = Flask(__name__)
    with app.app_context():
        response = api_config.config_health.__wrapped__()
    return response.get_json()


def test_config_health_accepts_api_key_without_username_password(mocker):
    cfg = _config(SimpleNamespace(
        url="http://qb",
        auth_type="api_key",
        username="",
        password="",
        api_key="qbt_api_key",
    ))

    data = _health_json(mocker, cfg)

    assert data == {"ok": True, "missing": []}


def test_config_health_requires_api_key_in_api_key_mode(mocker):
    cfg = _config(SimpleNamespace(
        url="http://qb",
        auth_type="api_key",
        username="",
        password="",
        api_key="",
    ))

    data = _health_json(mocker, cfg)

    assert data["ok"] is False
    assert "downloader.api_key" in data["missing"]
    assert "downloader.username" not in data["missing"]
    assert "downloader.password" not in data["missing"]


def test_config_health_requires_password_but_not_username_in_password_mode(mocker):
    cfg = _config(SimpleNamespace(
        url="http://qb",
        auth_type="password",
        username="",
        password="",
        api_key="qbt_api_key",
    ))

    data = _health_json(mocker, cfg)

    assert data["ok"] is False
    assert "downloader.username" not in data["missing"]
    assert "downloader.password" in data["missing"]
    assert "downloader.api_key" not in data["missing"]


def test_config_health_accepts_password_mode_without_username(mocker):
    cfg = _config(SimpleNamespace(
        url="http://qb",
        auth_type="password",
        username="",
        password="qb-password",
        api_key="",
    ))

    data = _health_json(mocker, cfg)

    assert data == {"ok": True, "missing": []}


def test_test_downloader_uses_api_key_auth_and_mask_fallback(mocker):
    cfg = _config(SimpleNamespace(
        url="http://old-qb",
        auth_type="api_key",
        username="",
        password="",
        api_key="old-api-key",
    ))
    mocker.patch.object(api_config, "PTBrushConfig", return_value=cfg)
    client_cls = mocker.patch.object(api_config.qbittorrentapi, "Client")
    client = client_cls.return_value
    app = Flask(__name__)

    with app.test_request_context(
        json={
            "url": "http://qb",
            "auth_type": "api_key",
            "username": "",
            "password": "",
            "api_key": "***",
        }
    ):
        response = api_config.test_downloader.__wrapped__()

    assert response.get_json()["ok"] is True
    client_cls.assert_called_once_with(
        host="http://qb",
        api_key="old-api-key",
        REQUESTS_ARGS={"timeout": api_config.TEST_DOWNLOADER_TIMEOUT},
    )
    client.auth_log_in.assert_called_once()
    client.auth_log_out.assert_called_once()
