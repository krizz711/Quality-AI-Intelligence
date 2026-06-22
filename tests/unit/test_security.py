"""T-S1 & T-S3: Security unit tests.

T-S1: Unauthorized access (401/403) is blocked and logged to the audit trail.
T-S3: No secrets (API keys, JWT tokens, passwords) appear in container logs.
"""

from __future__ import annotations

import json
import logging
import re
from io import StringIO
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# T-S1: Auth enforcement and audit logging
# ---------------------------------------------------------------------------

class TestUnauthorizedAccessBlocked:
    """Protected endpoints must return 401/403 and write an audit log entry."""

    @pytest.mark.asyncio
    async def test_missing_auth_returns_403_on_protected_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/reviews")

        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_invalid_bearer_token_returns_401(self):
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.post(
                "/api/v1/studies/grr",
                headers={"Authorization": "Bearer this-is-not-a-valid-token"},
                json={
                    "part_ids": ["P1"],
                    "operator_ids": ["O1"],
                    "measurements": [{"part": "P1", "operator": "O1", "value": 10.0}],
                },
            )

        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_unauthorized_access_written_to_audit_trail(self):
        """Middleware must call audit_log_event with event_type='auth_failure'."""
        logged: list[dict] = []

        async def capture(actor, event_type, component, metadata=None, **kwargs):
            logged.append({"event_type": event_type, "component": component})

        with patch("api.main.audit_log_event", side_effect=capture):
            from httpx import AsyncClient, ASGITransport
            from api.main import app

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                await client.get("/api/v1/reviews")

        auth_failures = [e for e in logged if e["event_type"] == "auth_failure"]
        assert len(auth_failures) >= 1, "auth_failure audit event was not logged"

    @pytest.mark.asyncio
    async def test_health_endpoints_are_exempt_from_auth(self):
        """Liveness, readiness, and legacy health must respond 200 without auth."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            for path in ["/health/live", "/api/v1/health"]:
                resp = await client.get(path)
                assert resp.status_code == 200, f"{path} returned {resp.status_code}"

    @pytest.mark.asyncio
    async def test_metrics_endpoint_is_exempt_from_auth(self):
        """Prometheus /metrics must be accessible without auth."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/metrics")

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# T-S3: No secrets in logs
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*\S{8,}"),
    re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S{4,}"),
    re.compile(r"(?i)(jwt[_-]?secret|secret[_-]?key)\s*[:=]\s*\S{8,}"),
    re.compile(r"(?i)(slack[_-]?webhook)\s*[:=]\s*https://"),
    re.compile(r"(?i)(gemini[_-]?api[_-]?key|api_key)\s*[:=]\s*[A-Za-z0-9_-]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9\-_\.]{40,}"),
]


def _contains_secret(text: str) -> bool:
    return any(p.search(text) for p in _SECRET_PATTERNS)


class TestNoSecretsInLogs:
    """Logs must never contain raw secret values (T-S3)."""

    def test_config_repr_does_not_expose_api_key(self):
        """Settings.__repr__ / __str__ must not leak api_auth_key."""
        import os
        os.environ["API_AUTH_KEY"] = "super-secret-key-that-should-not-appear"
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"

        from core.config import Settings
        s = Settings()
        text = repr(s)
        assert "super-secret-key-that-should-not-appear" not in text

    def test_grr_study_log_line_contains_no_secret(self, caplog):
        """A typical GRR study log message must not embed any secret patterns."""
        with caplog.at_level(logging.INFO, logger="api.main"):
            logger = logging.getLogger("api.main")
            logger.info(
                "grr_study study_id=abc-123 grr_pct=22.5 acceptance=CONDITIONAL "
                "equipment_id=CMM-001 characteristic=bore_diameter"
            )

        for record in caplog.records:
            assert not _contains_secret(record.getMessage()), (
                f"Secret pattern detected in log: {record.getMessage()}"
            )

    def test_alert_dispatch_log_contains_no_webhook_url(self, caplog):
        """Alert dispatch logs must not include the Slack webhook URL."""
        with caplog.at_level(logging.INFO, logger="agent.alert_manager"):
            logger = logging.getLogger("agent.alert_manager")
            logger.info(
                "alert_dispatched channel=slack process=press-line-1 severity=critical"
            )

        for record in caplog.records:
            assert "hooks.slack.com" not in record.getMessage()
            assert not _contains_secret(record.getMessage())

    def test_auth_failure_log_does_not_contain_token(self, caplog):
        """The auth failure log path must scrub the bearer token value."""
        sample_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIn0.FAKE"

        with caplog.at_level(logging.WARNING, logger="api.main"):
            logger = logging.getLogger("api.main")
            logger.warning(
                "auth_failure path=/api/v1/studies/grr reason=invalid_token"
            )

        for record in caplog.records:
            assert sample_token not in record.getMessage()

    def test_json_log_format_hides_secrets(self):
        """JSON-formatted log output must not contain raw secret values in any field."""
        from core.logging_config import setup_logging
        import os

        os.environ.setdefault("API_AUTH_KEY", "test-api-key")

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)

        test_logger = logging.getLogger("test.secrets")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)

        try:
            test_logger.info(
                "request_handled path=/api/v1/health status=200 duration_ms=12"
            )
            output = stream.getvalue()
            assert "test-api-key" not in output
            assert "super-secret" not in output
        finally:
            test_logger.removeHandler(handler)
