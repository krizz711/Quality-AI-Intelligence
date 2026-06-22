"""T-U4: Audit logging — trigger an action, verify the DB entry is written."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# Unit tests: audit_logger.log_event
# ---------------------------------------------------------------------------

class TestAuditLogEvent:
    """Tests for backend.services.audit_logger.log_event."""

    @pytest.mark.asyncio
    async def test_log_event_writes_correct_fields(self):
        """log_event must persist actor, event_type, component, and metadata."""
        mock_session = AsyncMock()
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        captured_log = {}

        async def fake_add(obj):
            captured_log.update({
                "actor": obj.actor,
                "event_type": obj.action if hasattr(obj, "action") else obj.event_type,
                "component": obj.component if hasattr(obj, "component") else None,
                "metadata": obj.details if hasattr(obj, "details") else obj.metadata,
            })

        mock_session.add = MagicMock(side_effect=lambda obj: captured_log.update({
            "actor": getattr(obj, "actor", None),
            "action": getattr(obj, "action", None),
            "entity_type": getattr(obj, "entity_type", None),
            "details": getattr(obj, "details", None),
        }))

        with patch("backend.services.audit_logger.AsyncSessionLocal", return_value=mock_session_ctx):
            from backend.services.audit_logger import log_event
            await log_event(
                actor="qa-engineer-1",
                event_type="grr_study_submitted",
                component="api",
                metadata={"study_id": "abc-123", "method": "xbar_r"},
            )

        mock_session.add.assert_called_once()
        assert captured_log["actor"] == "qa-engineer-1"
        assert captured_log["details"]["study_id"] == "abc-123"
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_log_event_includes_ip_address(self):
        """IP address is stored in metadata when provided."""
        mock_session = AsyncMock()
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        captured = {}
        mock_session.add = MagicMock(side_effect=lambda obj: captured.update({
            "ip": getattr(obj, "ip_address", None),
        }))

        with patch("backend.services.audit_logger.AsyncSessionLocal", return_value=mock_session_ctx):
            from backend.services.audit_logger import log_event
            await log_event(
                actor="system",
                event_type="alert_sent",
                component="alert_engine",
                metadata={},
                ip_address="192.168.1.42",
            )

        assert captured.get("ip") == "192.168.1.42"

    @pytest.mark.asyncio
    async def test_log_event_does_not_raise_on_db_failure(self):
        """log_event must swallow DB errors — alerting must not crash the caller."""
        mock_session = AsyncMock()
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock(side_effect=RuntimeError("DB unreachable"))

        with patch("backend.services.audit_logger.AsyncSessionLocal", return_value=mock_session_ctx):
            from backend.services.audit_logger import log_event
            # Must not raise
            await log_event(actor="test", event_type="test_event", component="test")

    @pytest.mark.asyncio
    async def test_auth_failure_is_logged_by_middleware(self):
        """The enforce_authentication middleware must log 401/403 attempts to the audit trail."""
        logged_events: list[dict] = []

        async def capture_log_event(actor, event_type, component, metadata=None, **kwargs):
            logged_events.append({
                "actor": actor,
                "event_type": event_type,
                "component": component,
                "metadata": metadata or {},
            })

        with patch("api.main.audit_log_event", side_effect=capture_log_event):
            from httpx import AsyncClient, ASGITransport
            from api.main import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                resp = await client.get("/api/v1/studies/grr/nonexistent")

        assert resp.status_code in (401, 403)
        auth_failures = [e for e in logged_events if e["event_type"] == "auth_failure"]
        assert len(auth_failures) >= 1
        assert auth_failures[0]["component"] == "api_middleware"
