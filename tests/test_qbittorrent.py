from qbittorrent import _is_torrents_add_success


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
