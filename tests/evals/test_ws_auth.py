"""
Eval: WebSocket authentication — validates that:
1. Connections without a token are rejected with code 4401.
2. Connections with a valid API key are accepted.
3. Connections with a valid JWT are accepted.
4. Connections with an invalid token are rejected.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_websocket(token: str | None = None) -> MagicMock:
    """Build a mock WebSocket whose query_params returns the given token."""
    ws = MagicMock()
    ws.query_params = {"token": token} if token is not None else {}
    ws.close = AsyncMock()
    ws.accept = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_ws_rejects_missing_token():
    from api.realtime import authenticate_websocket

    ws = _make_websocket(token=None)
    result = await authenticate_websocket(ws)

    assert result is False
    ws.close.assert_awaited_once_with(code=4401, reason="Missing authentication token")


@pytest.mark.asyncio
async def test_ws_accepts_valid_api_key():
    from api.realtime import authenticate_websocket

    with patch("api.realtime.settings") as mock_settings:
        mock_settings.api_auth_key = "valid-api-key-123"
        mock_settings.jwt_secret = "secret"
        ws = _make_websocket(token="valid-api-key-123")
        result = await authenticate_websocket(ws)

    assert result is True
    ws.close.assert_not_awaited()


@pytest.mark.asyncio
async def test_ws_accepts_valid_jwt():
    from api.realtime import authenticate_websocket
    from api.auth import create_access_token

    token = create_access_token({"sub": "testuser"})

    # Ensure the API key doesn't accidentally match the JWT
    with patch("api.realtime.settings") as mock_settings:
        mock_settings.api_auth_key = "something-else"
        mock_settings.jwt_secret = __import__("core.config", fromlist=["settings"]).settings.jwt_secret

        ws = _make_websocket(token=token)
        result = await authenticate_websocket(ws)

    assert result is True


@pytest.mark.asyncio
async def test_ws_rejects_invalid_token():
    from api.realtime import authenticate_websocket

    with patch("api.realtime.settings") as mock_settings:
        mock_settings.api_auth_key = "correct-api-key"
        mock_settings.jwt_secret = "secret"
        ws = _make_websocket(token="totally-wrong-token")
        result = await authenticate_websocket(ws)

    assert result is False
    ws.close.assert_awaited_once_with(code=4401, reason="Invalid authentication token")


@pytest.mark.asyncio
async def test_ws_rejects_expired_jwt():
    from datetime import timedelta
    from api.auth import create_access_token
    from api.realtime import authenticate_websocket

    expired_token = create_access_token({"sub": "user"}, expires_delta=timedelta(seconds=-1))

    with patch("api.realtime.settings") as mock_settings:
        mock_settings.api_auth_key = "some-other-key"
        mock_settings.jwt_secret = __import__("core.config", fromlist=["settings"]).settings.jwt_secret

        ws = _make_websocket(token=expired_token)
        result = await authenticate_websocket(ws)

    assert result is False
