"""Tests for the CSV/Excel bulk-upload endpoint and UI-configurable MES settings."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from db.database import AsyncSessionLocal


async def _count(part_number: str) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT count(*) FROM measurements WHERE part_number = :pn"), {"pn": part_number}
        )
    return int(result.scalar() or 0)


async def _cleanup(part_number: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM measurements WHERE part_number = :pn"), {"pn": part_number}
        )
        await session.commit()


def _csv(part_number: str, rows: int = 12) -> bytes:
    lines = ["timestamp,part_number,characteristic,value,unit"]
    for i in range(rows):
        lines.append(f"2026-06-15T10:{i:02d}:00Z,{part_number},bore_dia,{12.0 + i * 0.001},mm")
    return "\n".join(lines).encode()


@pytest.mark.asyncio
async def test_upload_csv_ingests_and_dedups(async_client, auth_token):
    part = f"UP-{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer {auth_token}"}
    try:
        resp = await async_client.post(
            "/api/v1/measurements/upload",
            files={"file": ("measurements.csv", _csv(part), "text/csv")},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["received"] == 12
        assert data["ingested"] == 12
        assert data["skipped"] == 0
        assert await _count(part) == 12

        # Re-uploading the same file must not create duplicates.
        resp2 = await async_client.post(
            "/api/v1/measurements/upload",
            files={"file": ("measurements.csv", _csv(part), "text/csv")},
            headers=headers,
        )
        assert resp2.status_code == 200
        assert await _count(part) == 12
    finally:
        await _cleanup(part)


@pytest.mark.asyncio
async def test_upload_column_mapping_override(async_client, auth_token):
    part = f"UP-{uuid.uuid4().hex[:8]}"
    # Headers the auto-detector won't recognise — supplied via an explicit mapping.
    csv = (
        "when,which_part,feat,reading\n"
        f"2026-06-15T11:00:00Z,{part},dia,12.5\n"
        f"2026-06-15T11:01:00Z,{part},dia,12.6\n"
    ).encode()
    mapping = '{"timestamp":"when","part_number":"which_part","characteristic_name":"feat","measured_value":"reading"}'
    try:
        resp = await async_client.post(
            "/api/v1/measurements/upload",
            files={"file": ("custom.csv", csv, "text/csv")},
            data={"mapping": mapping},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["ingested"] == 2
        assert await _count(part) == 2
    finally:
        await _cleanup(part)


@pytest.mark.asyncio
async def test_upload_rejects_unmappable_file(async_client, auth_token):
    resp = await async_client.post(
        "/api/v1/measurements/upload",
        files={"file": ("bad.csv", b"foo,bar\n1,2\n3,4", "text/csv")},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_requires_auth(async_client):
    resp = await async_client.post(
        "/api/v1/measurements/upload",
        files={"file": ("m.csv", b"timestamp,value\n2026-01-01,1.0", "text/csv")},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_mes_connector_settings_exposed_for_ui():
    """The MES connector must be configurable through the settings UI/API."""
    from core import settings_store

    masked = await settings_store.get_masked()
    keys = {entry["key"] for entry in masked}
    assert {"mes.api_url", "mes.api_token", "mes.field_map"} <= keys
    token_entry = next(entry for entry in masked if entry["key"] == "mes.api_token")
    assert token_entry["secret"] is True  # never returned with a value
