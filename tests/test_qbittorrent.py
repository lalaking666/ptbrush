from qbittorrent import QBittorrent, _is_torrents_add_success


def test_torrents_add_success_for_legacy_ok_response():
    assert _is_torrents_add_success("Ok.") is True


def test_torrents_add_failure_for_legacy_fails_response():
    assert _is_torrents_add_success("Fails.") is False


def test_torrents_add_success_for_empty_success_response():
    assert _is_torrents_add_success("") is True


def test_torrents_add_success_for_metadata_response():
    response = {
        "added_torrents": [{"hash": "abc", "name": "demo"}],
        "failed_torrents": [],
    }

    assert _is_torrents_add_success(response) is True


def test_torrents_add_failure_for_metadata_response():
    response = {
        "added_torrents": [],
        "failed_torrents": [{"name": "bad.torrent", "reason": "invalid"}],
    }

    assert _is_torrents_add_success(response) is False


def test_torrents_add_success_for_metadata_without_failure_fields():
    assert _is_torrents_add_success({"status": "queued"}) is True


def test_torrents_add_failure_for_unsupported_response_type():
    assert _is_torrents_add_success(object()) is False


def test_qbittorrent_uses_username_password_auth(mocker):
    client_cls = mocker.patch("qbittorrent.qbittorrentapi.Client")
    client = client_cls.return_value
    client.app_default_save_path.return_value = "/downloads"

    QBittorrent("http://qb", "admin", "secret", "password", "qbt_api_key")

    client_cls.assert_called_once_with(
        host="http://qb",
        username="admin",
        password="secret",
    )
    client.auth_log_in.assert_called_once()


def test_qbittorrent_uses_api_key_auth(mocker):
    client_cls = mocker.patch("qbittorrent.qbittorrentapi.Client")
    client = client_cls.return_value
    client.app_default_save_path.return_value = "/downloads"

    QBittorrent("http://qb", "admin", "secret", "api_key", "qbt_api_key")

    client_cls.assert_called_once_with(host="http://qb", api_key="qbt_api_key")
    client.auth_log_in.assert_called_once()
