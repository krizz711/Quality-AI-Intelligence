"""Tests for the unified GET /api/v1/integrations/status onboarding endpoint."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_integrations_status_shape(async_client, auth_token):
    resp = await async_client.get(
        "/api/v1/integrations/status",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) >= {"environment", "services", "integrations", "features", "summary"}

    # The database is up in the test environment.
    assert data["services"]["database"]["status"] == "ok"
    # Core services and integrations are always reported (configured true/false).
    assert {"database", "redis", "kafka", "mlflow"} <= set(data["services"])
    assert {"slack", "email", "sms", "jira", "qms", "gemini"} <= set(data["integrations"])
    # Feature flags surface the autonomous monitor.
    assert "autonomous_monitor" in data["features"]
    assert isinstance(data["features"]["autonomous_monitor"]["enabled"], bool)
    assert data["summary"]["services_total"] == 4


@pytest.mark.asyncio
async def test_integrations_status_requires_auth(async_client):
    resp = await async_client.get("/api/v1/integrations/status")
    assert resp.status_code in (401, 403)
