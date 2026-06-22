"""
Integration test — end-to-end measurement pipeline.

Requires live Docker services:
  - Kafka reachable at settings.kafka_bootstrap_servers
  - TimescaleDB reachable at settings.database_url

Run with:
  poetry run pytest -m integration -v
Skip in CI (unit-only):
  poetry run pytest -m "not integration"

IMPORTANT: Requires the Kafka consumer to be running before executing:
  poetry run python -m agent.consumer
"""

import asyncio
import random
import uuid
from datetime import UTC, datetime

import pytest
from confluent_kafka import Producer
from sqlalchemy import text

from core.config import settings
from db.database import AsyncSessionLocal
from schemas.measurement import MeasurementEvent

TEST_EQUIPMENT_ID = f"TEST-INTEGRATION-{uuid.uuid4()}"
TOPIC = "quality.measurements"
NUM_RECORDS = 10
CONSUMER_SETTLE_SECONDS = 8


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_event(index: int) -> MeasurementEvent:
    return MeasurementEvent(
        timestamp=datetime.now(UTC),
        part_number=f"PART-{(index % 5) + 1:03d}",
        characteristic_name="diameter",
        nominal_value=25.0,
        measured_value=round(random.normalvariate(25.0, 0.02), 4),
        unit="mm",
        operator_id="OP-001",
        equipment_id=TEST_EQUIPMENT_ID,
        shift="A",
    )


def _publish_events(bootstrap_servers: str, n: int) -> None:
    """Synchronously publish *n* events and flush."""
    delivered: list[Exception | None] = []

    def _delivery_cb(err, _msg) -> None:
        delivered.append(err)

    producer = Producer({"bootstrap.servers": bootstrap_servers})
    for i in range(1, n + 1):
        event = _build_event(i)
        producer.produce(
            TOPIC,
            key=event.part_number,
            value=event.model_dump_json(),
            callback=_delivery_cb,
        )
        producer.poll(0)

    producer.flush(timeout=30)

    errors = [e for e in delivered if e is not None]
    assert not errors, f"Kafka delivery errors: {errors}"
    assert len(delivered) == n, f"Expected {n} delivery callbacks, got {len(delivered)}"


# ─── Test ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_measurement_pipeline_end_to_end() -> None:
    """
    Publishes 10 test measurements to Kafka.
    Waits for the consumer to process them.
    Asserts all 10 appear in TimescaleDB.
    Cleans up after itself.
    """

    # ── Step 0: Pre-test cleanup (idempotency guard) ─────────────────────────
    # Delete any rows left by a previous failed/aborted run so the count
    # assertion always starts from a known-zero baseline.
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM measurements WHERE equipment_id = :eq_id"),
            {"eq_id": TEST_EQUIPMENT_ID},
        )
        await session.commit()

    # ── Step 1: Publish 10 records ───────────────────────────────────────────
    _publish_events(settings.kafka_bootstrap_servers, NUM_RECORDS)

    # ── Step 2: Wait for consumer to process ────────────────────────────────
    await asyncio.sleep(CONSUMER_SETTLE_SECONDS)

    # ── Step 3: Assert all records landed in DB ──────────────────────────────
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM measurements WHERE equipment_id = :eq_id"),
            {"eq_id": TEST_EQUIPMENT_ID},
        )
        count = result.scalar_one()

    assert count == NUM_RECORDS, (
        f"Expected {NUM_RECORDS} rows in measurements for equipment_id="
        f"{TEST_EQUIPMENT_ID!r}, found {count}. "
        "Is the Kafka consumer running? (poetry run python -m agent.consumer)"
    )

    # ── Step 4: Cleanup ───────────────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM measurements WHERE equipment_id = :eq_id"),
            {"eq_id": TEST_EQUIPMENT_ID},
        )
        await session.commit()

    # ── Step 5: Verify cleanup ────────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM measurements WHERE equipment_id = :eq_id"),
            {"eq_id": TEST_EQUIPMENT_ID},
        )
        count_after = result.scalar_one()

    assert count_after == 0, f"Cleanup failed: {count_after} rows remain for {TEST_EQUIPMENT_ID!r}"
