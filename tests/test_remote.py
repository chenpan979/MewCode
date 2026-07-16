from __future__ import annotations

from types import SimpleNamespace

import pytest

from mewcode.remote import RemoteServer


def _request(
    path: str,
    *,
    origin: str = "http://localhost:18888",
    host: str = "localhost:18888",
):
    return SimpleNamespace(
        path=path,
        headers={"Origin": origin, "Host": host},
    )


def test_remote_defaults_to_loopback():
    server = RemoteServer(providers=[])
    assert server.addr == "127.0.0.1"


def test_external_remote_requires_token():
    with pytest.raises(ValueError, match="authentication token"):
        RemoteServer(providers=[], addr="0.0.0.0")


def test_remote_websocket_accepts_valid_query_token():
    server = RemoteServer(
        providers=[],
        addr="0.0.0.0",
        auth_token="secret-token",
    )
    response = server._process_http_request(
        None,
        _request("/ws?token=secret-token"),
    )
    assert response is None


def test_remote_websocket_rejects_invalid_token():
    server = RemoteServer(
        providers=[],
        addr="0.0.0.0",
        auth_token="secret-token",
    )
    response = server._process_http_request(None, _request("/ws?token=wrong"))
    assert response is not None
    assert response.status_code == 401


def test_remote_websocket_rejects_cross_origin():
    server = RemoteServer(providers=[])
    response = server._process_http_request(
        None,
        _request("/ws", origin="https://evil.example"),
    )
    assert response is not None
    assert response.status_code == 403
