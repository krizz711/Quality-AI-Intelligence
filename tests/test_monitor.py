"""Tests for the autonomous ContinuousMonitor (agent/monitor.py).

These exercise the real SPC analysis + persistence path against the database, so
they require a reachable Postgres (DATABASE_URL) like the other DB-backed tests
in this repo. Each test uses a unique part number and cleans up after itself.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from agent.monitor import ContinuousMonitor
from db.database import AsyncSessionLocal
from db.models import Measurement


async def _seed(part_number: str, characteristic: str, values: list[float]) -> None:
    base = datetime.now(timezone.utc) - timedelta(minutes=len(values))
    async with AsyncSessionLocal() as session:
        for i, v in enumerate(values):
            session.add(
                Measurement(
                    timestamp=base + timedelta(seconds=i),
                    part_number=part_number,
                    characteristic_name=characteristic,
                    nominal_value=12.0,
                    measured_value=float(v),
                    unit="mm",
                    operator_id="OP1",
                    equipment_id="CMM-TEST",
                    shift="A",
                    source_event_id=f"{part_number}-{i}",
                    created_by="test",
                )
            )
        await session.commit()


async def _cleanup(part_number: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM measurements WHERE part_number = :pn"), {"pn": part_number}
        )
        await session.execute(
            text("DELETE FROM quality_violations WHERE part_number = :pn"), {"pn": part_number}
        )
        await session.commit()


@pytest.fixture
async def series():
    part_number = f"MON-{uuid.uuid4().hex[:8]}"
    characteristic = "bore_diameter"
    yield part_number, characteristic
    await _cleanup(part_number)


def _stable(n: int) -> list[float]:
    """A stable in-control series around 12.0 with tiny noise."""
    return [12.0 + (0.001 * ((i % 5) - 2)) for i in range(n)]


@pytest.mark.asyncio
async def test_clean_series_raises_no_violation(series):
    pn, cn = series
    await _seed(pn, cn, _stable(30))

    summary = await ContinuousMonitor(min_points=10, window=30).analyze_series(pn, cn)

    assert summary["status"] == "analyzed"
    assert summary["out_of_control"] is False
    assert summary["rule_1_violations"] == 0


@pytest.mark.asyncio
async def test_out_of_control_latest_point_raises_violation(series):
    pn, cn = series
    await _seed(pn, cn, _stable(29) + [13.0])  # latest point is a clear special cause

    summary = await ContinuousMonitor(min_points=10, window=30).analyze_series(pn, cn)

    assert summary["out_of_control"] is True
    assert summary["rule_1_violations"] == 1

    async with AsyncSessionLocal() as session:
        count = await session.execute(
            text(
                "SELECT count(*) FROM quality_violations "
                "WHERE part_number = :pn AND violation_type = 'nelson_rule_1'"
            ),
            {"pn": pn},
        )
        assert (count.scalar() or 0) == 1


@pytest.mark.asyncio
async def test_out_of_control_midbatch_point_raises_violation(series):
    """A batch upload whose special-cause reading is NOT the final row must still
    raise a violation (regression for the 'latest point only' gap)."""
    pn, cn = series
    await _seed(pn, cn, _stable(15) + [13.0] + _stable(14))  # spike in the middle

    summary = await ContinuousMonitor(min_points=10, window=30).analyze_series(pn, cn)

    assert summary["out_of_control"] is True
    assert summary["rule_1_violations"] == 1


@pytest.mark.asyncio
async def test_insufficient_data_is_skipped(series):
    pn, cn = series
    await _seed(pn, cn, [12.0, 12.01, 11.99, 12.02, 12.0])  # 5 < min_points

    summary = await ContinuousMonitor(min_points=10, window=30).analyze_series(pn, cn)

    assert summary["status"] == "skipped"
    assert summary["reason"] == "insufficient_data"


@pytest.mark.asyncio
async def test_duplicate_violation_is_suppressed(series):
    pn, cn = series
    await _seed(pn, cn, _stable(29) + [13.0])

    monitor = ContinuousMonitor(min_points=10, window=30)
    first = await monitor.analyze_series(pn, cn)
    second = await monitor.analyze_series(pn, cn)

    assert first["rule_1_violations"] == 1
    assert second["rule_1_violations"] == 0  # suppressed inside the dedup window

    async with AsyncSessionLocal() as session:
        count = await session.execute(
            text("SELECT count(*) FROM quality_violations WHERE part_number = :pn"),
            {"pn": pn},
        )
        assert (count.scalar() or 0) == 1


@pytest.mark.asyncio
async def test_scan_once_discovers_and_analyzes(series, monkeypatch):
    pn, cn = series
    await _seed(pn, cn, _stable(29) + [13.0])

    # Never dispatch real alerts during tests (the .env may hold live webhooks).
    async def _no_dispatch(self, session=None):
        return 0

    monkeypatch.setattr(
        "agent.alert_engine.AlertEngine.process_pending_violations", _no_dispatch
    )

    summary = await ContinuousMonitor(min_points=10, window=30).scan_once()

    assert summary["series_total"] >= 1
    assert summary["series_analyzed"] >= 1
