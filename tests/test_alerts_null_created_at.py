"""Regression: GET /api/v1/alerts must tolerate alert rows with NULL created_at.

Found during a live end-to-end test — a single orphan row with a NULL created_at
made the whole Alerts list endpoint return 500.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from db.database import AsyncSessionLocal


@pytest.mark.asyncio
async def test_list_alerts_tolerates_null_created_at(async_client, auth_token):
    process = f"NULLALERT-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO alerts (id, type, severity, message, process_name, status, created_at)
                VALUES (gen_random_uuid(), 'spc_violation', 'critical', 'null ts test', :p, 'active', NULL)
                """
            ),
            {"p": process},
        )
        await session.commit()
    try:
        resp = await async_client.get(
            "/api/v1/alerts", headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert resp.status_code == 200, resp.text
        match = [a for a in resp.json()["items"] if a["process_name"] == process]
        assert match, "the null-created_at alert should still be listed"
        assert match[0]["created_at"], "created_at should be coalesced to a real timestamp"
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("DELETE FROM alerts WHERE process_name = :p"), {"p": process}
            )
            await session.commit()
