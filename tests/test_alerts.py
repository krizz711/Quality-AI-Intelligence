"""Tests for Slack and JIRA alerting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agent.alerts import create_jira_ticket, send_slack_alert


@pytest.mark.asyncio
async def test_slack_sends_correct_payload(mock_slack_client: AsyncMock) -> None:
    result = await send_slack_alert(
        "https://fake.webhook",
        "test msg",
        "critical",
        study_id="STUDY-1",
    )

    mock_slack_client.post.assert_awaited_once()
    _, kwargs = mock_slack_client.post.await_args
    payload = kwargs["json"]
    # Block Kit format: check attachments color and blocks content
    assert "attachments" in payload
    assert payload["attachments"][0]["color"] == "#ff0000"
    # The message content lives in blocks
    import json as _json
    s = _json.dumps(payload)
    assert "STUDY-1" in s
    assert "critical" in s.lower()
    assert result is True



@pytest.mark.asyncio
async def test_slack_warning_color(mock_slack_client: AsyncMock) -> None:
    await send_slack_alert("https://fake.webhook", "test msg", "warning")

    _, kwargs = mock_slack_client.post.await_args
    payload = kwargs["json"]
    assert payload["attachments"][0]["color"] == "#ffcc00"


@pytest.mark.asyncio
async def test_slack_empty_webhook_returns_none() -> None:
    with patch("agent.alerts.httpx.AsyncClient") as mock_ac:
        result = await send_slack_alert("", "msg", "info")
        mock_ac.assert_not_called()

    assert result is None


@pytest.mark.asyncio
async def test_send_alert_does_not_raise_on_http_error(
    mock_slack_client: AsyncMock,
) -> None:
    request = httpx.Request("POST", "https://fake.webhook")
    response = httpx.Response(500, request=request)
    http_error = httpx.HTTPStatusError(
        "Server error",
        request=request,
        response=response,
    )
    error_response = MagicMock()
    error_response.raise_for_status.side_effect = http_error
    mock_slack_client.post = AsyncMock(return_value=error_response)

    result = await send_slack_alert("https://fake.webhook", "msg", "info")

    assert result is None


@pytest.mark.asyncio
async def test_jira_returns_none_when_not_configured() -> None:
    with patch("agent.alerts.httpx.AsyncClient") as mock_ac:
        result = await create_jira_ticket("", "", "", "QUAL", "summary", "desc")
        mock_ac.assert_not_called()

    assert result is None
