"""Tests for the MES/QMS scheduled connector (agent/mes_connector.py)."""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import text

from agent.mes_connector import MESConnector
from db.database import AsyncSessionLocal


def _fresh_connector(monkeypatch, **env) -> MESConnector:
    """Build a connector with a clean MES_* environment plus the given overrides."""
    for key in list(os.environ):
        if key.startswith("MES_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("MES_API_URL", env.pop("MES_API_URL", "http://mes.local/api/measurements"))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return MESConnector()


# ── pure mapping / extraction (no DB, no HTTP) ──────────────────────────────────

def test_field_map_and_record_mapping(monkeypatch):
    conn = _fresh_connector(
        monkeypatch,
        MES_FIELD_MAP='{"timestamp":"measuredAt","part_number":"partNo","characteristic_name":"feature","measured_value":"value","equipment_id":"machine"}',
        MES_ID_FIELD="id",
    )
    mapped = conn._map_record(
        {
            "id": "rec-1",
            "measuredAt": "2026-06-15T10:00:00Z",
            "partNo": "ABC-123",
            "feature": "bore_dia",
            "value": "12.01",
            "machine": "CMM-7",
        }
    )
    assert mapped is not None
    assert mapped["part_number"] == "ABC-123"
    assert mapped["characteristic_name"] == "bore_dia"
    assert mapped["measured_value"] == 12.01
    assert mapped["equipment_id"] == "CMM-7"
    assert mapped["source_event_id"] == "rec-1"
    assert mapped["timestamp"].year == 2026


def test_record_missing_required_fields_is_skipped(monkeypatch):
    conn = _fresh_connector(monkeypatch)
    assert conn._map_record({"timestamp": "2026-06-15T10:00:00Z"}) is None  # no value
    assert conn._map_record({"measured_value": 1.0}) is None  # no timestamp
    assert conn._map_record("not-a-dict") is None


def test_extract_records_paths(monkeypatch):
    top = _fresh_connector(monkeypatch)
    assert top._extract_records([{"a": 1}]) == [{"a": 1}]
    assert top._extract_records({"data": [{"a": 1}]}) == [{"a": 1}]  # common-key fallback
    nested = _fresh_connector(monkeypatch, MES_RECORDS_PATH="result.items")
    assert nested._extract_records({"result": {"items": [{"a": 1}]}}) == [{"a": 1}]


def test_synthesized_id_is_stable(monkeypatch):
    conn = _fresh_connector(monkeypatch)  # no MES_ID_FIELD -> hash of content
    rec = {
        "timestamp": "2026-06-15T10:00:00Z",
        "measured_value": 5.0,
        "part_number": "P1",
        "characteristic_name": "c",
    }
    first = conn._map_record(rec)["source_event_id"]
    second = conn._map_record(rec)["source_event_id"]
    assert first == second and len(first) == 32


# ── poll_once + ingest (DB-backed, mocked HTTP) ─────────────────────────────────

async def _cleanup(part_number: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM measurements WHERE part_number = :pn"), {"pn": part_number}
        )
        await session.commit()


async def _count(part_number: str) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT count(*) FROM measurements WHERE part_number = :pn"), {"pn": part_number}
        )
    return int(result.scalar() or 0)


@pytest.mark.asyncio
async def test_poll_once_ingests_and_dedups(monkeypatch):
    part = f"MES-{uuid.uuid4().hex[:8]}"
    conn = _fresh_connector(monkeypatch, MES_ID_FIELD="id")

    payload = {
        "data": [
            {
                "id": f"{part}-{i}",
                "timestamp": f"2026-06-15T10:{i:02d}:00Z",
                "part_number": part,
                "characteristic_name": "dia",
                "measured_value": 10.0 + i * 0.01,
            }
            for i in range(10)
        ]
    }

    async def fake_fetch(params):
        return payload

    monkeypatch.setattr(conn, "_fetch", fake_fetch)

    try:
        first = await conn.poll_once()
        assert first["status"] == "ok"
        assert first["fetched"] == 10 and first["mapped"] == 10
        assert await _count(part) == 10

        # Re-poll the identical payload — ON CONFLICT means no duplicates.
        await conn.poll_once()
        assert await _count(part) == 10
    finally:
        await _cleanup(part)


@pytest.mark.asyncio
async def test_poll_once_handles_http_error(monkeypatch):
    conn = _fresh_connector(monkeypatch)

    async def boom(params):
        raise RuntimeError("MES down")

    monkeypatch.setattr(conn, "_fetch", boom)
    result = await conn.poll_once()
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_disabled_without_url(monkeypatch):
    for key in list(os.environ):
        if key.startswith("MES_"):
            monkeypatch.delenv(key, raising=False)
    conn = MESConnector()  # no MES_API_URL configured
    assert (await conn.poll_once())["status"] == "disabled"


@pytest.mark.asyncio
async def test_poll_once_rereads_runtime_config(monkeypatch):
    """Configuring the connector from the UI (env applied at runtime) must take
    effect on the next poll with no restart."""
    for key in list(os.environ):
        if key.startswith("MES_"):
            monkeypatch.delenv(key, raising=False)
    conn = MESConnector()
    assert (await conn.poll_once())["status"] == "disabled"

    # Simulate settings_store.apply_to_runtime() setting the URL after startup.
    monkeypatch.setenv("MES_API_URL", "http://mes.local/api/measurements")

    async def fake_fetch(params):
        return []

    monkeypatch.setattr(conn, "_fetch", fake_fetch)
    assert (await conn.poll_once())["status"] == "ok"
