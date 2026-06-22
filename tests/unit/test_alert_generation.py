"""T-U3: Alert generation logic with mock violation fixtures.

Tests the AlertEngine.process_pending_violations path for all violation
types, severity mapping, deduplication, and audit marking — all without
a live database.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from agent.alert_engine import AlertEngine


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _violation(
    *,
    violation_type: str = "nelson_rule_1",
    part_number: str = "PN-001",
    characteristic_name: str = "diameter",
    measured_value: float = 12.5,
    ucl: float = 11.0,
    lcl: float = 9.0,
    id: str = "00000000-0000-0000-0000-000000000001",
) -> dict:
    return {
        "id": id,
        "part_number": part_number,
        "characteristic_name": characteristic_name,
        "violation_type": violation_type,
        "measured_value": measured_value,
        "ucl": ucl,
        "lcl": lcl,
    }


def _select_result(rows):
    mock_mappings = MagicMock()
    mock_mappings.all.return_value = rows
    result = MagicMock()
    result.mappings.return_value = mock_mappings
    return result


def _count_result(n: int):
    result = MagicMock()
    result.scalar.return_value = n
    return result


# ---------------------------------------------------------------------------
# Severity mapping (T-U3 sub-task)
# ---------------------------------------------------------------------------

class TestSeverityScoring:

    def test_rule_1_is_critical(self):
        engine = AlertEngine()
        assert engine._score_severity("nelson_rule_1") == "critical"

    def test_rule_2_is_warning(self):
        engine = AlertEngine()
        assert engine._score_severity("nelson_rule_2") == "warning"

    def test_rule_3_is_warning(self):
        engine = AlertEngine()
        assert engine._score_severity("nelson_rule_3") == "warning"

    @pytest.mark.parametrize("rule", [
        "nelson_rule_4", "nelson_rule_5", "nelson_rule_6",
        "nelson_rule_7", "nelson_rule_8",
    ])
    def test_remaining_rules_are_info(self, rule: str):
        engine = AlertEngine()
        assert engine._score_severity(rule) == "info"

    def test_unknown_violation_type_is_info(self):
        engine = AlertEngine()
        assert engine._score_severity("unknown_violation") == "info"
        assert engine._score_severity("") == "info"


# ---------------------------------------------------------------------------
# Alert dispatch flow
# ---------------------------------------------------------------------------

class TestAlertDispatch:

    @pytest.mark.asyncio
    @patch("agent.alert_engine.AlertManager.send", new_callable=AsyncMock)
    @patch("agent.alert_engine.settings")
    async def test_dispatches_one_alert_per_unsent_violation(
        self, mock_settings, mock_send
    ):
        """One unsent violation → one AlertManager.send call."""
        mock_settings.slack_webhook_url = "https://hooks.slack.com/fake"
        mock_settings.jira_url = ""

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _select_result([_violation()]),
            _count_result(0),   # no dedup
            MagicMock(),        # UPDATE
        ])

        engine = AlertEngine()
        sent = await engine.process_pending_violations(session=session)

        assert sent == 1
        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("agent.alert_engine.AlertManager.send", new_callable=AsyncMock)
    @patch("agent.alert_engine.settings")
    async def test_dispatches_multiple_violations(self, mock_settings, mock_send):
        """Three independent unsent violations → three dispatches."""
        mock_settings.slack_webhook_url = "https://hooks.slack.com/fake"
        mock_settings.jira_url = ""

        violations = [
            _violation(id=f"00000000-0000-0000-0000-00000000000{i}", characteristic_name=f"char-{i}")
            for i in range(1, 4)
        ]
        side_effects = []
        for _ in violations:
            side_effects.append(_select_result(violations) if not side_effects else MagicMock())
            side_effects.append(_count_result(0))
            side_effects.append(MagicMock())

        # Simpler: re-query each time returns same list; dedup always 0
        session = AsyncMock()
        call_count = 0

        async def execute_side_effect(query, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _select_result(violations)
            if call_count % 2 == 0:
                return _count_result(0)
            return MagicMock()

        session.execute = AsyncMock(side_effect=execute_side_effect)

        engine = AlertEngine()
        sent = await engine.process_pending_violations(session=session)

        assert sent == 3
        assert mock_send.await_count == 3

    @pytest.mark.asyncio
    @patch("agent.alert_engine.AlertManager.send", new_callable=AsyncMock)
    @patch("agent.alert_engine.settings")
    async def test_no_violations_returns_zero(self, mock_settings, mock_send):
        """Empty violations table → 0 alerts sent."""
        mock_settings.slack_webhook_url = ""
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_select_result([]))

        engine = AlertEngine()
        sent = await engine.process_pending_violations(session=session)

        assert sent == 0
        mock_send.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("agent.alert_engine.AlertManager.send", new_callable=AsyncMock)
    @patch("agent.alert_engine.settings")
    async def test_marks_violation_alert_sent(self, mock_settings, mock_send):
        """The engine must set alert_sent=TRUE after dispatching."""
        mock_settings.slack_webhook_url = "https://hooks.slack.com/fake"

        v = _violation()
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _select_result([v]),
            _count_result(0),
            MagicMock(),
        ])

        engine = AlertEngine()
        await engine.process_pending_violations(session=session)

        update_call = session.execute.await_args_list[2]
        sql = str(update_call.args[0])
        assert "alert_sent=TRUE" in sql
        params = update_call.args[1]
        assert params["id"] == v["id"]
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("agent.alert_engine.AlertManager.send", new_callable=AsyncMock)
    @patch("agent.alert_engine.settings")
    async def test_alert_event_severity_matches_violation_type(self, mock_settings, mock_send):
        """The AlertEvent severity forwarded to AlertManager reflects the violation type."""
        mock_settings.slack_webhook_url = "https://hooks.slack.com/fake"

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _select_result([_violation(violation_type="nelson_rule_1")]),
            _count_result(0),
            MagicMock(),
        ])

        engine = AlertEngine()
        await engine.process_pending_violations(session=session)

        event = mock_send.call_args[0][0]
        assert event.severity == "critical"
        assert event.type == "spc_violation"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:

    @pytest.mark.asyncio
    @patch("agent.alert_engine.AlertManager.send", new_callable=AsyncMock)
    @patch("agent.alert_engine.settings")
    async def test_skips_violation_already_alerted_recently(self, mock_settings, mock_send):
        """Dedup count > 0 → violation is skipped, not dispatched."""
        mock_settings.slack_webhook_url = "https://hooks.slack.com/fake"

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _select_result([_violation()]),
            _count_result(1),   # already alerted in last 4h
        ])

        engine = AlertEngine()
        sent = await engine.process_pending_violations(session=session)

        assert sent == 0
        mock_send.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("agent.alert_engine.AlertManager.send", new_callable=AsyncMock)
    @patch("agent.alert_engine.settings")
    async def test_sends_when_no_recent_duplicate(self, mock_settings, mock_send):
        """Dedup count == 0 → violation is sent normally."""
        mock_settings.slack_webhook_url = "https://hooks.slack.com/fake"

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _select_result([_violation()]),
            _count_result(0),
            MagicMock(),
        ])

        engine = AlertEngine()
        sent = await engine.process_pending_violations(session=session)

        assert sent == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestAlertEngineErrorHandling:

    @pytest.mark.asyncio
    async def test_returns_zero_on_db_error(self):
        """If the DB query raises, engine catches it and returns 0."""
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=RuntimeError("DB timeout"))

        engine = AlertEngine()
        sent = await engine.process_pending_violations(session=session)

        assert sent == 0
        session.rollback.assert_awaited()
