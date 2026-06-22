"""Tests for AlertEngine — dedup, severity scoring, and alert_sent updates."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.alert_engine import AlertEngine

_VIOLATION = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "part_number": "P1",
    "characteristic_name": "diameter",
    "violation_type": "nelson_rule_1",
    "measured_value": 10.5,
    "ucl": 12.0,
    "lcl": 8.0,
}


def _select_result(rows: list[dict]) -> MagicMock:
    mock_mappings = MagicMock()
    mock_mappings.all.return_value = rows
    result = MagicMock()
    result.mappings.return_value = mock_mappings
    return result


def _count_result(count: int) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = count
    return result


@pytest.mark.asyncio
@patch("agent.alert_engine.AlertManager.send", new_callable=AsyncMock)
@patch("agent.alert_engine.settings")
async def test_engine_marks_violation_sent(
    mock_settings: MagicMock,
    mock_alert_manager_send: AsyncMock,
) -> None:
    mock_settings.slack_webhook_url = "https://hooks.slack.com/fake"
    mock_settings.jira_url = ""

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        side_effect=[
            _select_result([_VIOLATION]),
            _count_result(0),
            MagicMock(),
        ]
    )

    engine = AlertEngine()
    sent = await engine.process_pending_violations(session=mock_session)

    assert sent == 1
    mock_alert_manager_send.assert_called_once()
    
    # Check what was passed to alert manager
    ev = mock_alert_manager_send.call_args[0][0]
    assert ev.severity == "critical"

    update_call = mock_session.execute.await_args_list[2]
    assert "alert_sent=TRUE" in str(update_call.args[0])
    update_params = update_call.args[1]
    assert update_params["id"] == str(_VIOLATION["id"])
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch("agent.alert_engine.AlertManager.send", new_callable=AsyncMock)
@patch("agent.alert_engine.settings")
async def test_engine_dedup_skips_recent_alert(
    mock_settings: MagicMock,
    mock_alert_manager_send: AsyncMock,
) -> None:
    mock_settings.slack_webhook_url = "https://hooks.slack.com/fake"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        side_effect=[
            _select_result([_VIOLATION]),
            _count_result(1),
        ]
    )

    engine = AlertEngine()
    sent = await engine.process_pending_violations(session=mock_session)

    assert sent == 0
    mock_alert_manager_send.assert_not_called()
    mock_session.commit.assert_not_awaited()


def test_engine_scores_rule_1_as_critical() -> None:
    engine = AlertEngine()
    assert engine._score_severity("nelson_rule_1") == "critical"
    assert engine._score_severity("nelson_rule_2") == "warning"
    assert engine._score_severity("nelson_rule_3") == "warning"
    assert engine._score_severity("nelson_rule_4") == "info"
