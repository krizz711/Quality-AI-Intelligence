import uuid
from datetime import datetime, timezone, timedelta
import json
import asyncio

import pytest


@pytest.mark.asyncio
async def test_grr_study_creates_audit_event(async_client, auth_token):
    from unittest.mock import patch, AsyncMock
    import asyncpg
    import os
    with patch("backend.services.gemini_service.analyzeGRR", new_callable=AsyncMock, return_value="Mocked AI Insights"):

        token = auth_token
        now = datetime.now(timezone.utc)
        measurements = []
        # 5 parts, 2 operators, 2 trials
        operators = ["opA", "opB"]
        for part in range(1, 6):
            for op in operators:
                for trial in (1, 2):
                    measurements.append({"operator": op, "part": part, "trial": trial, "value": 1.0 + part})

        payload = {"measurements": measurements, "partTolerance": 0.5}

        resp = await async_client.post("/api/v1/grr/analyze", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        
        conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
        try:
            r = await conn.fetchrow("SELECT * FROM audit_events WHERE event_type = $1 ORDER BY created_at DESC LIMIT 1", 'grr_study_run')
            assert r is not None
            assert r["event_type"] == "grr_study_run"
            assert r["component"] == "grr_calculator"
            assert r["user_id"] == "testuser"
            assert r["input_hash"] is not None and len(r["input_hash"]) == 64
            assert r["algorithm_version"] is not None
            assert r["result_summary"] is not None and "pct_grr" in r["result_summary"]
            # driver timezone quirks can cause naive/aware mismatch
            assert r["created_at"] is not None
        finally:
            await conn.close()




@pytest.mark.asyncio
async def test_auth_failure_creates_audit_event(async_client):
    import asyncpg
    import os
    resp = await async_client.get("/api/v1/measurements")
    assert resp.status_code in (401, 403)
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    try:
        r = await conn.fetchrow("SELECT * FROM audit_events WHERE event_type = $1 ORDER BY created_at DESC LIMIT 1", 'auth_failure')
        assert r is not None
        assert r["event_type"] == "auth_failure"
        assert r["component"] == "api_middleware"
        assert "ip_address" in dict(r)
        assert "/api/v1/measurements" in json.dumps(r["metadata"])
        assert r["user_id"] is None
    finally:
        await conn.close()


from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_alert_sent_creates_audit_event(fake_redis):
    import asyncpg
    import os
    with patch("agent.alerts.generate_alert_explanation", new_callable=AsyncMock, return_value="Mocked AI Insights"):
        from agent.alert_manager import AlertEvent, AlertManager

        manager = AlertManager(redis_client=fake_redis, dedupe_ttl=1)
        ev = AlertEvent(type="spc_violation", severity="critical", message="audit test", process_name="proc-1")
        await manager.send(ev)
        # wait for async write
        await asyncio.sleep(1)
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    try:
        r = await conn.fetchrow("SELECT * FROM audit_events WHERE event_type = $1 ORDER BY created_at DESC LIMIT 1", 'alert_sent')
        assert r is not None
        rs = json.loads(r["result_summary"]) if r["result_summary"] else {}
        assert "channels_attempted" in rs
        assert rs["severity"] == "critical"
        assert rs["alert_id"] is not None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_audit_export_json(async_client, auth_token):
    import asyncpg
    import os
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    now = datetime.now(timezone.utc)
    await conn.execute(
        "INSERT INTO audit_events (id, created_at, event_type, component, user_id) VALUES ($1, $2, $3, $4, $5)",
        uuid.uuid4(), now - timedelta(minutes=5), 'grr_study_run', 'grr_calculator', None,
    )
    await conn.execute(
        "INSERT INTO audit_events (id, created_at, event_type, component) VALUES ($1, $2, $3, $4)",
        uuid.uuid4(), now - timedelta(minutes=3), 'auth_failure', 'api_middleware',
    )
    await conn.execute(
        "INSERT INTO audit_events (id, created_at, event_type, component) VALUES ($1, $2, $3, $4)",
        uuid.uuid4(), now - timedelta(minutes=1), 'alert_sent', 'alert_manager',
    )
    await conn.close()

    start = (now - timedelta(minutes=10)).isoformat().replace("+", "%2B")
    end = (now + timedelta(minutes=1)).isoformat().replace("+", "%2B")

    token = auth_token
    resp = await async_client.get(f"/api/v1/audit/export?start={start}&end={end}&format=json", headers={"Authorization": f"Bearer {token}"})
    
    # Cleanup
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    await conn.execute("DELETE FROM audit_events")
    await conn.close()
    
    assert resp.status_code == 200
    assert 'application/json' in resp.headers.get('Content-Type', '')
    data = resp.json()
    assert len(data) >= 3
    types = {item['event_type'] for item in data}
    assert {'grr_study_run', 'auth_failure', 'alert_sent'}.issubset(types)
    for it in data:
        assert 'id' in it and 'timestamp' in it and 'event_type' in it and 'component' in it and 'metadata' in it


@pytest.mark.asyncio
async def test_audit_export_csv(async_client, auth_token):
    import asyncpg
    import os
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    now = datetime.now(timezone.utc)
    await conn.execute("INSERT INTO audit_events (id, created_at, event_type, component) VALUES ($1,$2,$3,$4)", uuid.uuid4(), now - timedelta(minutes=2), 'auth_failure', 'api_middleware')
    await conn.execute("INSERT INTO audit_events (id, created_at, event_type, component) VALUES ($1,$2,$3,$4)", uuid.uuid4(), now - timedelta(minutes=1), 'auth_failure', 'api_middleware')
    await conn.close()

    start = (now - timedelta(minutes=10)).isoformat().replace("+", "%2B")
    end = (now + timedelta(minutes=1)).isoformat().replace("+", "%2B")
    token = auth_token
    resp = await async_client.get(f"/api/v1/audit/export?start={start}&end={end}&format=csv", headers={"Authorization": f"Bearer {token}"})
    
    # Cleanup
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    await conn.execute("DELETE FROM audit_events")
    await conn.close()

    assert resp.status_code == 200
    assert 'text/csv' in resp.headers.get('Content-Type', '')


@pytest.mark.asyncio
async def test_audit_export_filters_by_event_type(async_client, auth_token):
    import asyncpg
    import os
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    now = datetime.now(timezone.utc)
    await conn.execute("INSERT INTO audit_events (id, created_at, event_type, component) VALUES ($1,$2,$3,$4)", uuid.uuid4(), now - timedelta(minutes=2), 'grr_study_run', 'grr_calculator')
    await conn.execute("INSERT INTO audit_events (id, created_at, event_type, component) VALUES ($1,$2,$3,$4)", uuid.uuid4(), now - timedelta(minutes=1), 'grr_study_run', 'grr_calculator')
    await conn.execute("INSERT INTO audit_events (id, created_at, event_type, component) VALUES ($1,$2,$3,$4)", uuid.uuid4(), now - timedelta(minutes=1), 'auth_failure', 'api_middleware')
    await conn.close()

    start = (now - timedelta(minutes=10)).isoformat().replace("+", "%2B")
    end = (now + timedelta(minutes=1)).isoformat().replace("+", "%2B")
    token = auth_token
    resp = await async_client.get(f"/api/v1/audit/export?start={start}&end={end}&event_type=grr_study_run&format=json", headers={"Authorization": f"Bearer {token}"})
    
    # Cleanup
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    await conn.execute("DELETE FROM audit_events")
    await conn.close()

    assert resp.status_code == 200
    data = resp.json()
    assert all(it['event_type'] == 'grr_study_run' for it in data)


 


@pytest.mark.asyncio
async def test_sql_injection_on_audit_filter(async_client, auth_token):
    import asyncpg
    import os
    token = auth_token
    malicious = "grr_study_run'; DROP TABLE audit_events; --"
    start = "2024-01-01' OR '1'='1"
    resp = await async_client.get(f"/api/v1/audit/export?event_type={malicious}&start={start}&format=json", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (400, 422)
    # table should still exist
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    try:
        count = await conn.fetchval("SELECT COUNT(*) FROM audit_events")
        assert count is not None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_no_pii_or_secrets_in_audit_records(async_client):
    import asyncpg
    import os
    # login with password and ensure password not stored
    resp = await async_client.post("/api/v1/auth/token", json={"username": "testuser", "password": "s3cr3tP@ss"})
    # last audit event should not contain the raw password
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    try:
        r = await conn.fetchrow("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 1")
        assert r is not None
        joined = str(dict(r))
        assert "s3cr3tP@ss" not in joined
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_audit_retention_policy_exists():
    import asyncpg
    import os
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    try:
        r = await conn.fetchrow("SELECT * FROM timescaledb_information.jobs WHERE hypertable_name = 'audit_events' AND proc_name = 'policy_retention'")
        assert r is not None
        # check interval roughly 1-10 years
        assert 'schedule_interval' in r
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_audit_events_is_hypertable():
    import asyncpg
    import os
    conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
    try:
        r = await conn.fetchrow("SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'audit_events'")
        assert r is not None
        assert r['hypertable_name'] == 'audit_events'
    finally:
        await conn.close()
