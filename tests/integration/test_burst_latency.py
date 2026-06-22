from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg
import pytest
import pytest_asyncio
import websockets
from aiokafka import AIOKafkaProducer
from sqlalchemy.engine import make_url

from core.config import settings

pytestmark = pytest.mark.integration

TOPIC = os.getenv("MEASUREMENTS_TOPIC", settings.measurements_topic)
WS_URL = "ws://localhost:8000/api/v1/ws/measurements"
BURST_SIZE = 1000
IDEMPOTENCY_SIZE = 50
LOSS_SIZE = 500
METRICS_SIZE = 200
MALFORMED_VALID_SIZE = 6
LOG_RE = re.compile(r"BATCH_METRICS.*?db_upsert_ms=(?P<db_upsert_ms>[0-9.]+)")
SLOW_RE = re.compile(r"BATCH_SLOW.*")
PHASE3_SUMMARY: dict[str, float | int] = {}


def _asyncpg_dsn(raw_url: str) -> str:
    url = make_url(raw_url)
    if "+asyncpg" in url.drivername:
        url = url.set(drivername=url.drivername.replace("+asyncpg", ""))
    return url.render_as_string(hide_password=False)


def _message_payload(event_id: str, *, process_id: str, value: float, timestamp: str) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "process_id": process_id,
        "value": value,
        "unit": "mm",
        "timestamp": timestamp,
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (percentile / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


async def _create_producer() -> AIOKafkaProducer:
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )
    await producer.start()
    return producer


async def _produce_json_messages(
    producer: AIOKafkaProducer,
    messages: list[dict[str, Any]],
    *,
    produce_times: dict[str, float] | None = None,
) -> None:
    pending = []
    for message in messages:
        if produce_times is not None:
            produce_times[message["event_id"]] = time.monotonic()
        pending.append(
            asyncio.create_task(
                producer.send(
                    TOPIC,
                    value=json.dumps(message).encode("utf-8"),
                )
            )
        )
    await asyncio.gather(*pending)
    await producer.flush()


async def _produce_raw_message(producer: AIOKafkaProducer, payload: bytes) -> None:
    await producer.send(TOPIC, value=payload)
    await producer.flush()


def _compose_logs(*, since: str | None = None) -> str:
    command = ["docker", "compose", "logs", "--no-color", "--tail", "500"]
    if since:
        command.extend(["--since", since])
    command.append("api")
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "docker compose logs failed")
    return completed.stdout


def _extract_batch_metrics(log_text: str) -> list[float]:
    metrics: list[float] = []
    for line in io.StringIO(log_text):
        match = LOG_RE.search(line)
        if match:
            metrics.append(float(match.group("db_upsert_ms")))
    return metrics


def _print_slow_batches(log_text: str) -> None:
    slow_lines = [line.rstrip() for line in io.StringIO(log_text) if SLOW_RE.search(line)]
    if slow_lines:
        print("\n".join(slow_lines))


async def _count_matching_rows(db_conn: asyncpg.Connection, prefix: str) -> int:
    return await db_conn.fetchval(
        "SELECT COUNT(*) FROM measurements WHERE source_event_id LIKE $1",
        f"{prefix}%",
    )


async def _wait_for_count(
    db_conn: asyncpg.Connection,
    prefix: str,
    expected: int,
    *,
    timeout_seconds: float,
    poll_seconds: float = 0.5,
) -> int:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        count = await _count_matching_rows(db_conn, prefix)
        if count == expected:
            return count
        await asyncio.sleep(poll_seconds)
    return await _count_matching_rows(db_conn, prefix)


async def _cleanup_prefix(db_conn: asyncpg.Connection, prefix: str) -> None:
    await db_conn.execute("DELETE FROM measurements WHERE source_event_id LIKE $1", f"{prefix}%")


@pytest_asyncio.fixture
async def kafka_producer() -> AIOKafkaProducer:
    producer = await _create_producer()
    try:
        yield producer
    finally:
        await producer.stop()


@pytest_asyncio.fixture
async def db_conn() -> asyncpg.Connection:
    raw_dsn = os.getenv("TEST_DATABASE_URL") or settings.database_url
    conn = await asyncpg.connect(_asyncpg_dsn(raw_dsn))
    try:
        yield conn
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def ws_client():
    deadline = time.monotonic() + 15
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            async with websockets.connect(WS_URL, ping_interval=None, open_timeout=5) as websocket:
                yield websocket
                return
        except Exception as exc:  # pragma: no cover - only exercised against live services
            last_error = exc
            await asyncio.sleep(0.5)
    if last_error is not None:
        raise last_error


@pytest_asyncio.fixture(scope="session", autouse=True)
async def phase3_summary_printer(request: pytest.FixtureRequest):
    yield
    if request.session.testsfailed == 0 and PHASE3_SUMMARY:
        print(
            "Phase 3 SLA verified: "
            f"p99={PHASE3_SUMMARY['p99_ms']:.1f}ms, "
            f"1000 messages, {PHASE3_SUMMARY['lost_count']} lost, {PHASE3_SUMMARY['duplicate_count']} duplicates"
        )


@pytest.mark.asyncio
async def test_idempotency_no_duplicate_inserts(kafka_producer: AIOKafkaProducer, db_conn: asyncpg.Connection) -> None:
    prefix = f"idempotency-test-{uuid.uuid4()}"
    await _cleanup_prefix(db_conn, prefix)
    event_ids = [f"{prefix}-{index}" for index in range(50)]
    timestamp = datetime.now(timezone.utc).isoformat()
    messages = [
        _message_payload(event_id, process_id="test-process-1", value=10.0 + index * 0.01, timestamp=timestamp)
        for index, event_id in enumerate(event_ids)
    ]

    await _produce_json_messages(kafka_producer, messages)
    await asyncio.sleep(3)

    count_after_first_batch = await _wait_for_count(
        db_conn,
        prefix,
        50,
        timeout_seconds=60,
    )
    assert count_after_first_batch == 50

    await _produce_json_messages(kafka_producer, messages)
    await asyncio.sleep(3)

    count_after_second_batch = await _wait_for_count(
        db_conn,
        prefix,
        50,
        timeout_seconds=60,
    )
    assert count_after_second_batch == 50

    await _cleanup_prefix(db_conn, prefix)
    PHASE3_SUMMARY["duplicate_count"] = count_after_second_batch - 50


@pytest.mark.asyncio
async def test_1000_message_burst_latency(
    kafka_producer: AIOKafkaProducer,
    db_conn: asyncpg.Connection,
    ws_client,
) -> None:
    event_ids = [f"test-{uuid.uuid4()}" for _ in range(BURST_SIZE)]
    messages: list[dict[str, Any]] = []

    for index, event_id in enumerate(event_ids):
        messages.append(
            _message_payload(
                event_id,
                process_id="test-process-1",
                value=round(9.5 + (index % 100) * 0.01, 4),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    produced_at: dict[str, float] = {}

    received_at: dict[str, float] = {}

    async def collect_messages() -> None:
        deadline = time.monotonic() + 30
        while len(received_at) < BURST_SIZE and time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                raw_message = await asyncio.wait_for(ws_client.recv(), timeout=remaining)
            except asyncio.TimeoutError as exc:
                raise AssertionError("Timed out waiting for websocket burst messages") from exc
            payload = json.loads(raw_message)
            event_id = payload.get("event_id") or payload.get("source_event_id")
            if event_id in produced_at and event_id not in received_at:
                received_at[event_id] = time.monotonic()

    collector = asyncio.create_task(collect_messages())
    try:
        await _produce_json_messages(kafka_producer, messages, produce_times=produced_at)
        await asyncio.wait_for(collector, timeout=35)
    finally:
        if not collector.done():
            collector.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await collector

    latencies = [(received_at[event_id] - produced_at[event_id]) * 1000 for event_id in event_ids if event_id in received_at]
    p50 = _percentile(latencies, 50)
    p99 = _percentile(latencies, 99)
    p100 = max(latencies) if latencies else 0.0

    print(f"p50={p50:.1f}ms  p99={p99:.1f}ms  max={p100:.1f}ms  total={len(latencies)}")

    await _wait_for_count(db_conn, "test-", BURST_SIZE, timeout_seconds=60)
    await _cleanup_prefix(db_conn, "test-")

    PHASE3_SUMMARY.update({"p99_ms": p99, "lost_count": BURST_SIZE - len(latencies), "duplicate_count": 0})

    assert len(received_at) == BURST_SIZE
    assert p99 <= 1000


@pytest.mark.asyncio
async def test_no_message_loss_under_burst(kafka_producer: AIOKafkaProducer, db_conn: asyncpg.Connection) -> None:
    await _cleanup_prefix(db_conn, "loss-test-")
    event_ids = [f"loss-test-{uuid.uuid4()}" for _ in range(LOSS_SIZE)]
    timestamp = datetime.now(timezone.utc).isoformat()
    messages = [
        _message_payload(event_id, process_id="test-process-1", value=9.8, timestamp=timestamp)
        for event_id in event_ids
    ]

    await _produce_json_messages(kafka_producer, messages)
    count = await _wait_for_count(db_conn, "loss-test-", LOSS_SIZE, timeout_seconds=10)

    assert count == LOSS_SIZE

    await _cleanup_prefix(db_conn, "loss-test-")


@pytest.mark.asyncio
async def test_batch_metrics_log_output(kafka_producer: AIOKafkaProducer) -> None:
    test_started_at = datetime.now(timezone.utc).isoformat()
    event_ids = [f"metrics-test-{uuid.uuid4()}" for _ in range(METRICS_SIZE)]
    timestamp = datetime.now(timezone.utc).isoformat()
    messages = [
        _message_payload(event_id, process_id="test-process-1", value=10.1, timestamp=timestamp)
        for event_id in event_ids
    ]

    await _produce_json_messages(kafka_producer, messages)
    await asyncio.sleep(5)

    log_text = _compose_logs(since=test_started_at)
    metrics = _extract_batch_metrics(log_text)
    _print_slow_batches(log_text)

    assert metrics, "No BATCH_METRICS lines were emitted"
    assert all(db_upsert_ms < 100 for db_upsert_ms in metrics)


@pytest.mark.asyncio
async def test_malformed_message_skipped_not_crashed(
    kafka_producer: AIOKafkaProducer,
    db_conn: asyncpg.Connection,
    ws_client,
) -> None:
    await _cleanup_prefix(db_conn, "malformed-test-")
    valid_event_ids = [f"malformed-test-{uuid.uuid4()}" for _ in range(MALFORMED_VALID_SIZE)]
    timestamp = datetime.now(timezone.utc).isoformat()
    first_batch = [
        _message_payload(event_id, process_id="test-process-1", value=10.0, timestamp=timestamp)
        for event_id in valid_event_ids[:3]
    ]
    second_batch = [
        _message_payload(event_id, process_id="test-process-1", value=10.2, timestamp=timestamp)
        for event_id in valid_event_ids[3:]
    ]

    await _produce_json_messages(kafka_producer, first_batch)
    await _produce_raw_message(kafka_producer, b"this is not json at all")
    await _produce_json_messages(kafka_producer, second_batch)

    count = await _wait_for_count(db_conn, "malformed-test-", MALFORMED_VALID_SIZE, timeout_seconds=5)
    assert count == MALFORMED_VALID_SIZE

    pong_waiter = await ws_client.ping()
    await asyncio.wait_for(pong_waiter, timeout=2)

    await _cleanup_prefix(db_conn, "malformed-test-")
