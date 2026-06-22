import asyncio
import json
import os
import uuid

from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest
from httpx import AsyncClient

from agent.alert_manager import AlertEvent, AlertManager
from api.main import app
from db.models import Alert


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def ensure_env(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("ALERT_EMAIL_RECIPIENTS", "")
    monkeypatch.setenv("JIRA_URL", "")
    monkeypatch.setenv("JIRA_EMAIL", "")
    monkeypatch.setenv("JIRA_API_TOKEN", "")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "")
    monkeypatch.setenv("SMS_WEBHOOK_URL", "")
    monkeypatch.setenv("SMS_TO_NUMBERS", "")
    monkeypatch.setenv("QMS_API_URL", "")
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bind_alerting_settings(
    monkeypatch,
    *,
    enable_slack: bool = True,
    enable_email: bool = False,
    enable_sms: bool = False,
    enable_jira: bool = False,
    enable_qms: bool = False,
):
    import agent.alert_manager as am_mod

    monkeypatch.setattr(am_mod.settings, "slack_webhook_url", "http://localhost:0/slack/webhook" if enable_slack else "")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "http://localhost:0/slack/webhook" if enable_slack else "")
    monkeypatch.setattr(am_mod.settings, "smtp_host", "smtp.example.com" if enable_email else "")
    monkeypatch.setattr(am_mod.settings, "smtp_port", 587)
    monkeypatch.setattr(am_mod.settings, "smtp_user", "user")
    monkeypatch.setattr(am_mod.settings, "smtp_password", "pass")
    monkeypatch.setattr(am_mod.settings, "smtp_from_address", "alerts@example.com")
    monkeypatch.setattr(
        am_mod.settings,
        "alert_email_recipients",
        "qa@example.com,manager@example.com" if enable_email else "",
    )
    monkeypatch.setattr(am_mod.settings, "sms_webhook_url", "http://sms.example/webhook" if enable_sms else "")
    monkeypatch.setattr(am_mod.settings, "sms_auth_token", "sms-token" if enable_sms else "")
    monkeypatch.setattr(am_mod.settings, "sms_from_number", "+15550000" if enable_sms else "")
    monkeypatch.setattr(am_mod.settings, "sms_to_numbers", "+15550001,+15550002" if enable_sms else "")
    monkeypatch.setattr(am_mod.settings, "jira_url", "http://jira.example" if enable_jira else "")
    monkeypatch.setattr(am_mod.settings, "jira_email", "bot@example.com" if enable_jira else "")
    monkeypatch.setattr(am_mod.settings, "jira_api_token", "token" if enable_jira else "")
    monkeypatch.setattr(am_mod.settings, "jira_project_key", "QUAL" if enable_jira else "")
    monkeypatch.setattr(am_mod.settings, "qms_api_url", "http://qms.example/api/results" if enable_qms else "")


def _mock_slack_http(monkeypatch, side_effect=None, response_json=None):
    mock_client = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=response_json or {"ok": True})
    if side_effect is None:
        mock_client.post = AsyncMock(return_value=response)
    else:
        mock_client.post = AsyncMock(side_effect=side_effect)

    class DummyCM:
        def __init__(self, client):
            self.client = client

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("agent.alert_manager.httpx.AsyncClient", lambda *a, **k: DummyCM(mock_client))
    return mock_client


def _mock_llm_explanation(monkeypatch, text=""):
    import agent.alert_manager as am_mod

    async def _fake(self, ev):
        return text

    monkeypatch.setattr(am_mod.AlertManager, "_generate_llm_explanation", _fake)


async def _db() -> asyncpg.Connection:
    """Open a fresh asyncpg connection for verification queries."""
    return await asyncpg.connect(os.environ["TEST_DATABASE_URL"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_slack_alert_dispatched_records_delivery_and_audit(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch)
    _mock_slack_http(monkeypatch)
    _mock_llm_explanation(monkeypatch, "LLM explanation")

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    ev = AlertEvent(
        type="spc_violation",
        severity="critical",
        message="Measurement 12.7 exceeds UCL 10.5",
        process_name="press-line-1",
        payload={"rule": "Nelson Rule 1"},
    )
    alert_id = await manager.send(ev)

    assert alert_id is not None
    conn = await _db()
    try:
        alert_row = await conn.fetchrow(
            "SELECT type, severity, message, process_name, status FROM alerts WHERE id = $1",
            str(alert_id),
        )
        assert alert_row["type"] == "spc_violation"
        assert alert_row["severity"] == "critical"
        assert alert_row["process_name"] == "press-line-1"

        delivery_count = await conn.fetchval(
            "SELECT count(*) FROM notification_deliveries WHERE alert_id = $1",
            str(alert_id),
        )
        assert int(delivery_count) >= 1

        audit_count = await conn.fetchval(
            "SELECT count(*) FROM audit_logs WHERE entity_id = $1 AND action = 'send_slack'",
            str(alert_id),
        )
        assert int(audit_count) >= 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_slack_retry_on_failure(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch)
    _mock_llm_explanation(monkeypatch, "")

    bad_resp = MagicMock()
    bad_resp.raise_for_status = MagicMock(side_effect=Exception("500"))
    good_resp = MagicMock()
    good_resp.raise_for_status = MagicMock()
    good_resp.json = MagicMock(return_value={"ok": True})
    mock_client = _mock_slack_http(monkeypatch, side_effect=[bad_resp, good_resp])

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    ev = AlertEvent(type="spc_violation", severity="critical", message="retry test", process_name="press-line-1")
    alert_id = await manager.send(ev)

    assert mock_client.post.call_count == 2
    conn = await _db()
    try:
        delivery = await conn.fetchrow(
            "SELECT channel, status FROM notification_deliveries WHERE alert_id = $1 AND channel = 'slack'",
            str(alert_id),
        )
        assert delivery["channel"] == "slack"
        assert delivery["status"] == "sent"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_slack_all_retries_exhausted_logs_failure(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch)
    _mock_llm_explanation(monkeypatch, "")

    bad_resp = MagicMock()
    bad_resp.raise_for_status = MagicMock(side_effect=Exception("500"))
    mock_client = _mock_slack_http(monkeypatch, side_effect=[bad_resp] * 5)

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    ev = AlertEvent(type="spc_violation", severity="critical", message="exhausted", process_name="press-line-1")
    alert_id = await manager.send(ev)

    assert mock_client.post.call_count == 5
    conn = await _db()
    try:
        delivery = await conn.fetchrow(
            "SELECT channel, status FROM notification_deliveries WHERE alert_id = $1 AND channel = 'slack'",
            str(alert_id),
        )
        assert delivery["channel"] == "slack"
        assert delivery["status"] == "failed"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_email_alert_dispatched_records_delivery(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch, enable_slack=False, enable_email=True)
    _mock_llm_explanation(monkeypatch, "")

    calls = []

    async def fake_send(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr("agent.alerts.send_email_alert", fake_send)

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    ev = AlertEvent(
        type="spc_violation",
        severity="warning",
        message="email test: Nelson Rule 2",
        process_name="press-line-1",
    )
    alert_id = await manager.send(ev)

    assert len(calls) == 1
    conn = await _db()
    try:
        email_delivery = await conn.fetchrow(
            "SELECT channel, status, recipient FROM notification_deliveries WHERE alert_id = $1 AND channel = 'email'",
            str(alert_id),
        )
        assert email_delivery["channel"] == "email"
        assert email_delivery["status"] == "sent"
        assert "qa@example.com" in email_delivery["recipient"]
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_sms_alert_only_for_critical(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch, enable_slack=False, enable_sms=True)
    _mock_llm_explanation(monkeypatch, "")

    sms_calls = []

    async def fake_sms(*args, **kwargs):
        sms_calls.append((args, kwargs))
        return True

    monkeypatch.setattr("agent.alerts.send_sms_alert", fake_sms)

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    ev = AlertEvent(type="spc_violation", severity="critical", message="sms test", process_name="press-line-1")
    alert_id = await manager.send(ev)

    assert len(sms_calls) == 1
    conn = await _db()
    try:
        sms_delivery = await conn.fetchrow(
            "SELECT channel, status FROM notification_deliveries WHERE alert_id = $1 AND channel = 'sms'",
            str(alert_id),
        )
        assert sms_delivery["channel"] == "sms"
        assert sms_delivery["status"] == "sent"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_jira_ticket_created_with_llm_summary(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch, enable_slack=False, enable_jira=True)
    _mock_llm_explanation(monkeypatch, "LLM summary for GRR")

    jira_calls = []

    async def fake_create_jira_ticket(*args, **kwargs):
        jira_calls.append(kwargs)
        return "QUAL-42"

    monkeypatch.setattr("agent.alerts.create_jira_ticket", fake_create_jira_ticket)
    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    ev = AlertEvent(
        type="grr_fail",
        severity="critical",
        message="grr fail >30%",
        process_name="press-line-1",
        grr_pct=35.0,
    )
    alert_id = await manager.send(ev)

    assert len(jira_calls) == 1
    assert "LLM summary for GRR" in jira_calls[0]["description"]
    conn = await _db()
    try:
        jira_delivery = await conn.fetchrow(
            "SELECT channel, status, response_reference FROM notification_deliveries WHERE alert_id = $1 AND channel = 'jira'",
            str(alert_id),
        )
        assert jira_delivery["channel"] == "jira"
        assert jira_delivery["status"] == "created"
        assert jira_delivery["response_reference"] == "QUAL-42"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_jira_not_created_for_warning(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch, enable_slack=False, enable_jira=True)
    _mock_llm_explanation(monkeypatch, "")

    called = []

    async def fake_create_jira_ticket(*args, **kwargs):
        called.append(True)
        return "QUAL-1"

    monkeypatch.setattr("agent.alerts.create_jira_ticket", fake_create_jira_ticket)

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    ev = AlertEvent(type="grr_fail", severity="warning", message="minor", process_name="press-line-1", grr_pct=10.0)
    alert_id = await manager.send(ev)

    assert not called
    conn = await _db()
    try:
        count = await conn.fetchval(
            "SELECT count(*) FROM notification_deliveries WHERE alert_id = $1 AND channel = 'jira'",
            str(alert_id),
        )
        assert int(count) == 0
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_qms_integration_posts_results_and_logs_delivery(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch, enable_slack=False, enable_qms=True)
    _mock_llm_explanation(monkeypatch, "")

    qms_client = MagicMock()
    qms_resp = MagicMock()
    qms_resp.raise_for_status = MagicMock()
    qms_client.post = AsyncMock(return_value=qms_resp)

    class DummyCM:
        def __init__(self, client):
            self.client = client

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("agent.alert_manager.httpx.AsyncClient", lambda *a, **k: DummyCM(qms_client))

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    ev = AlertEvent(
        type="spc_violation",
        severity="warning",
        message="qms payload",
        process_name="press-line-1",
        payload={"study_id": "study-1", "grr_pct": 12.5},
    )
    alert_id = await manager.send(ev)

    assert qms_client.post.call_count == 1
    conn = await _db()
    try:
        qms_delivery = await conn.fetchrow(
            "SELECT channel, status FROM notification_deliveries WHERE alert_id = $1 AND channel = 'qms'",
            str(alert_id),
        )
        assert qms_delivery["channel"] == "qms"
        assert qms_delivery["status"] == "sent"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_redis_deduplication_blocks_second_send(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch)
    _mock_llm_explanation(monkeypatch, "")
    mock_client = _mock_slack_http(monkeypatch)

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    unique_process = f"press-line-{uuid.uuid4().hex[:8]}"
    unique_message = f"dedup test {uuid.uuid4().hex[:8]}"
    ev = AlertEvent(type="spc_violation", severity="critical", message=unique_message, process_name=unique_process)
    first_id = await manager.send(ev)
    second_id = await manager.send(ev)

    assert first_id is not None
    assert second_id is None
    assert mock_client.post.call_count == 1
    conn = await _db()
    try:
        count = await conn.fetchval(
            "SELECT count(*) FROM alerts WHERE process_name = $1 AND message = $2",
            unique_process, unique_message,
        )
        assert int(count) >= 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_deduplication_resets_after_ttl(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch)
    _mock_llm_explanation(monkeypatch, "")
    mock_client = _mock_slack_http(monkeypatch)

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=1)
    ev = AlertEvent(type="spc_violation", severity="critical", message="ttl test", process_name="press-line-1")
    await manager.send(ev)
    await asyncio.sleep(1.1)
    await manager.send(ev)
    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_acknowledge_endpoint_updates_real_alert():
    from httpx import ASGITransport
    from api.auth import create_access_token

    alert_id = uuid.uuid4()
    # Insert the alert directly via asyncpg
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    try:
        await conn.execute(
            "INSERT INTO alerts (id, type, severity, message, process_name, status) VALUES ($1,$2,$3,$4,$5,$6)",
            str(alert_id), "spc_violation", "critical", "ack test", "press-line-1", "active",
        )
    finally:
        await conn.close()

    jwt_token = create_access_token({"sub": "test-user"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.patch(
            f"/api/v1/alerts/{alert_id}/acknowledge",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

    assert response.status_code == 200
    assert response.json()["alert_id"] == str(alert_id)

    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    try:
        row = await conn.fetchrow(
            "SELECT status, resolved_by FROM alerts WHERE id = $1", str(alert_id)
        )
        assert row["status"] == "acknowledged"
        assert row["resolved_by"] == "test-user"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_acknowledge_requires_auth():
    from httpx import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.patch("/api/v1/alerts/not-found/acknowledge", headers={"x-api-key": "test-api-key"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_alert_accuracy_benchmark(monkeypatch, fake_redis):
    _bind_alerting_settings(monkeypatch)
    _mock_llm_explanation(monkeypatch, "")
    _mock_slack_http(monkeypatch)

    manager = AlertManager(redis_client=fake_redis, dedupe_ttl=900)
    true_pos = 0
    false_pos = 0
    unique_process = f"proc-{uuid.uuid4().hex[:8]}"

    for i in range(20):
        ev = AlertEvent(type="spc_violation", severity="critical", message=f"bad {i} {uuid.uuid4().hex[:6]}", process_name=unique_process)
        await manager.send(ev)
        true_pos += 1

    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    try:
        count = await conn.fetchval(
            "SELECT count(*) FROM alerts WHERE process_name = $1", unique_process
        )
        assert int(count) >= 20
    finally:
        await conn.close()

    precision = true_pos / (true_pos + false_pos)
    fp_rate = false_pos / 100
    assert precision >= 0.95
    assert fp_rate <= 0.05
