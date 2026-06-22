from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

import asyncpg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import TopicPartition
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from api.realtime import publish_dlq_event, publish_realtime_event
from core.config import settings
from schemas.measurement import MeasurementEvent

logger = logging.getLogger(__name__)

TOPIC = settings.measurements_topic
DLQ_TOPIC = settings.measurements_dlq_topic
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "arad-quality-agent-consumer")
BATCH_SIZE = 50
BATCH_TIMEOUT_MS = 50
MAX_POLL_RECORDS = 100
POLL_TIMEOUT_MS = 50
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 10
BroadcastSink = Literal["queue", "redis"]


@dataclass(slots=True)
class BufferedRecord:
    payload: dict[str, Any] | str
    event: MeasurementEvent | None
    kafka_timestamp_ms: int | None
    received_at_ms: float
    topic: str
    partition: int
    offset: int
    error: str | None = None


def _asyncpg_dsn() -> str:
    url = make_url(settings.database_url)
    if "+asyncpg" in url.drivername:
        url = url.set(drivername=url.drivername.replace("+asyncpg", ""))
    return url.render_as_string(hide_password=False)


def _decode_record(record: Any) -> BufferedRecord:
    raw_text = record.value.decode("utf-8", errors="replace")
    received_at_ms = time.time() * 1000

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return BufferedRecord(
            payload=raw_text,
            event=None,
            kafka_timestamp_ms=record.timestamp,
            received_at_ms=received_at_ms,
            topic=record.topic,
            partition=record.partition,
            offset=record.offset,
            error=f"invalid_json: {exc.msg}",
        )

    normalized_payload = _normalize_measurement_payload(payload)

    try:
        event = MeasurementEvent.model_validate(normalized_payload)
    except ValidationError as exc:
        return BufferedRecord(
            payload=normalized_payload,
            event=None,
            kafka_timestamp_ms=record.timestamp,
            received_at_ms=received_at_ms,
            topic=record.topic,
            partition=record.partition,
            offset=record.offset,
            error=f"validation_error: {exc.errors()}",
        )

    return BufferedRecord(
        payload=normalized_payload,
        event=event,
        kafka_timestamp_ms=record.timestamp,
        received_at_ms=received_at_ms,
        topic=record.topic,
        partition=record.partition,
        offset=record.offset,
    )


def _normalize_measurement_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if "value" in payload or "process_id" in payload:
        event_id = payload.get("event_id") or uuid.uuid4().hex
        process_id = payload.get("process_id") or payload.get("equipment_id") or event_id
        measured_value = payload.get("measured_value", payload.get("value"))
        return {
            "event_id": event_id,
            "timestamp": payload["timestamp"],
            "part_number": payload.get("part_number") or process_id,
            "characteristic_name": payload.get("characteristic_name") or "value",
            "nominal_value": payload.get("nominal_value"),
            "measured_value": measured_value,
            "unit": payload.get("unit"),
            "operator_id": payload.get("operator_id"),
            "equipment_id": payload.get("equipment_id") or process_id,
            "shift": payload.get("shift"),
        }

    return payload


def _measurement_row(event: MeasurementEvent) -> tuple[Any, ...]:
    return (
        event.timestamp,
        event.part_number,
        event.characteristic_name,
        event.nominal_value,
        event.measured_value,
        event.unit,
        event.operator_id,
        event.equipment_id,
        event.shift,
        event.event_id,
        "system",
    )


def _measurement_realtime_payload(event: MeasurementEvent) -> dict[str, Any]:
    payload = event.model_dump(mode="json")
    payload["type"] = "measurement.processed"
    payload["source_event_id"] = event.event_id
    return payload


def _dlq_payload(item: BufferedRecord, error: str) -> dict[str, Any]:
    source_event_id = None
    if isinstance(item.payload, dict):
        source_event_id = item.payload.get("event_id")

    return {
        "type": "measurement.dlq",
        "topic": item.topic,
        "partition": item.partition,
        "offset": item.offset,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_event_id": source_event_id,
        "error": error,
        "raw_payload": item.payload,
    }


async def _publish_realtime_event(
    event: dict[str, Any],
    *,
    broadcast_sink: BroadcastSink,
    broadcast_queue: asyncio.Queue[dict[str, Any]] | None,
) -> None:
    if broadcast_sink == "queue":
        if broadcast_queue is None:
            raise RuntimeError("broadcast_queue is required when broadcast_sink='queue'")
        await broadcast_queue.put(event)
        return

    await publish_realtime_event(event)


async def _publish_dlq_event(
    event: dict[str, Any],
    *,
    broadcast_sink: BroadcastSink,
    broadcast_queue: asyncio.Queue[dict[str, Any]] | None,
) -> None:
    if broadcast_sink == "queue":
        if broadcast_queue is None:
            raise RuntimeError("broadcast_queue is required when broadcast_sink='queue'")
        await broadcast_queue.put(event)
        return

    await publish_dlq_event(event)


async def _persist_batch(pool: asyncpg.Pool, batch: list[BufferedRecord]) -> tuple[list[MeasurementEvent], int]:
    unique_events: list[MeasurementEvent] = []
    seen_ids: set[str] = set()
    duplicates_skipped = 0
    timestamps: list[Any] = []
    part_numbers: list[str] = []
    characteristic_names: list[str] = []
    nominal_values: list[float | None] = []
    measured_values: list[float] = []
    units: list[str | None] = []
    operator_ids: list[str | None] = []
    equipment_ids: list[str | None] = []
    shifts: list[str | None] = []
    source_event_ids: list[str] = []
    created_bys: list[str] = []

    for item in batch:
        event = item.event
        if event is None:
            continue
        if event.event_id in seen_ids:
            duplicates_skipped += 1
            continue
        seen_ids.add(event.event_id)
        unique_events.append(event)
        timestamps.append(event.timestamp)
        part_numbers.append(event.part_number)
        characteristic_names.append(event.characteristic_name)
        nominal_values.append(event.nominal_value)
        measured_values.append(event.measured_value)
        units.append(event.unit)
        operator_ids.append(event.operator_id)
        equipment_ids.append(event.equipment_id)
        shifts.append(event.shift)
        source_event_ids.append(event.event_id)
        created_bys.append("system")

    if not source_event_ids:
        return unique_events, duplicates_skipped

    insert_sql = """
        WITH incoming AS (
            SELECT *
            FROM UNNEST(
                $1::timestamptz[],
                $2::text[],
                $3::text[],
                $4::double precision[],
                $5::double precision[],
                $6::text[],
                $7::text[],
                $8::text[],
                $9::text[],
                $10::text[],
                $11::text[]
            ) AS t(
                timestamp,
                part_number,
                characteristic_name,
                nominal_value,
                measured_value,
                unit,
                operator_id,
                equipment_id,
                shift,
                source_event_id,
                created_by
            )
        )
        INSERT INTO measurements (
            timestamp,
            part_number,
            characteristic_name,
            nominal_value,
            measured_value,
            unit,
            operator_id,
            equipment_id,
            shift,
            source_event_id,
            created_by
        )
        SELECT
            timestamp,
            part_number,
            characteristic_name,
            nominal_value,
            measured_value,
            unit,
            operator_id,
            equipment_id,
            shift,
            source_event_id,
            created_by
        FROM incoming
        ON CONFLICT (source_event_id, timestamp) DO NOTHING
        RETURNING source_event_id
    """

    async with pool.acquire() as connection:
        async with connection.transaction():
            inserted_rows = await connection.fetch(
                insert_sql,
                timestamps,
                part_numbers,
                characteristic_names,
                nominal_values,
                measured_values,
                units,
                operator_ids,
                equipment_ids,
                shifts,
                source_event_ids,
                created_bys,
            )

    inserted_ids = {row["source_event_id"] for row in inserted_rows}
    unique_events = [event for event in unique_events if event.event_id in inserted_ids]

    return unique_events, duplicates_skipped


async def _emit_batch(
    batch: list[BufferedRecord],
    *,
    batch_id: int,
    pool: asyncpg.Pool,
    producer: AIOKafkaProducer,
    broadcast_sink: BroadcastSink,
    broadcast_queue: asyncio.Queue[dict[str, Any]] | None,
    seen_ids: set[str],
) -> None:
    if not batch:
        return

    batch_started_ms = min(item.kafka_timestamp_ms or item.received_at_ms for item in batch)
    flush_started_ms = time.time() * 1000

    invalid_items = [item for item in batch if item.event is None]
    if invalid_items:
        for item in invalid_items:
            dlq_event = _dlq_payload(item, item.error or "invalid_message")
            await producer.send_and_wait(DLQ_TOPIC, json.dumps(dlq_event).encode("utf-8"))
            await _publish_dlq_event(dlq_event, broadcast_sink=broadcast_sink, broadcast_queue=broadcast_queue)

    valid_items = [item for item in batch if item.event is not None and item.event.event_id not in seen_ids]
    duplicates_skipped = len(batch) - len(valid_items) - len(invalid_items)

    db_started_ms = time.time() * 1000
    inserted_events: list[MeasurementEvent] = []

    if valid_items:
        try:
            inserted_events, batch_duplicates = await _persist_batch(pool, valid_items)
            duplicates_skipped += batch_duplicates
        except Exception as exc:
            logger.exception("batch_insert_failed batch_id=%s size=%s", batch_id, len(batch))
            for item in valid_items:
                dlq_event = _dlq_payload(item, f"database_error: {exc}")
                await producer.send_and_wait(DLQ_TOPIC, json.dumps(dlq_event).encode("utf-8"))
                await _publish_dlq_event(dlq_event, broadcast_sink=broadcast_sink, broadcast_queue=broadcast_queue)
            raise

    db_finished_ms = time.time() * 1000

    realtime_payloads = [_measurement_realtime_payload(event) for event in inserted_events]
    if realtime_payloads:
        await asyncio.gather(
            *(
                _publish_realtime_event(
                    payload,
                    broadcast_sink=broadcast_sink,
                    broadcast_queue=broadcast_queue,
                )
                for payload in realtime_payloads
            ),
            return_exceptions=True,
        )

    broadcast_finished_ms = time.time() * 1000

    offsets: dict[TopicPartition, int] = {}
    for item in batch:
        tp = TopicPartition(item.topic, item.partition)
        offsets[tp] = max(offsets.get(tp, item.offset + 1), item.offset + 1)

    kafka_to_accumulate_ms = round(flush_started_ms - batch_started_ms, 2)
    db_upsert_ms = round(db_finished_ms - db_started_ms, 2)
    broadcast_ms = round(broadcast_finished_ms - db_finished_ms, 2)
    total_ms = round(broadcast_finished_ms - batch_started_ms, 2)

    logger.info(
        (
            "BATCH_METRICS batch_id=%s size=%s db_rows=%s kafka_to_accumulate_ms=%s "
            "db_upsert_ms=%s broadcast_ms=%s total_ms=%s duplicates_skipped=%s"
        ),
        batch_id,
        len(batch),
        len(inserted_events),
        kafka_to_accumulate_ms,
        db_upsert_ms,
        broadcast_ms,
        total_ms,
        duplicates_skipped,
    )
    if db_upsert_ms > 100 or total_ms > 1000:
        logger.warning(
            "batch_slow batch_id=%s db_upsert_ms=%s total_ms=%s size=%s",
            batch_id,
            db_upsert_ms,
            total_ms,
            len(batch),
        )

    return offsets


async def run_consumer(
    *,
    pool: asyncpg.Pool,
    broadcast_queue: asyncio.Queue[dict[str, Any]] | None = None,
    shutdown_event: asyncio.Event | None = None,
    broadcast_sink: BroadcastSink = "redis",
) -> None:
    shutdown_event = shutdown_event or asyncio.Event()
    seen_ids: set[str] = set()
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=GROUP_ID,
        enable_auto_commit=False,
        auto_offset_reset="latest",
        max_poll_records=MAX_POLL_RECORDS,
        fetch_max_wait_ms=POLL_TIMEOUT_MS,
    )

    batch: list[BufferedRecord] = []
    batch_id = 0

    async def flush_batch() -> None:
        nonlocal batch_id
        if not batch:
            return

        batch_id += 1
        offsets = await _emit_batch(
            batch,
            batch_id=batch_id,
            pool=pool,
            producer=producer,
            broadcast_sink=broadcast_sink,
            broadcast_queue=broadcast_queue,
            seen_ids=seen_ids,
        )
        if offsets:
            await consumer.commit(offsets)
        for item in batch:
            if item.event is not None:
                seen_ids.add(item.event.event_id)
        batch.clear()

    await producer.start()
    await consumer.start()
    try:
        while True:
            if shutdown_event.is_set() and not batch:
                break

            records_by_partition = await consumer.getmany(timeout_ms=POLL_TIMEOUT_MS, max_records=MAX_POLL_RECORDS)
            now_ms = time.time() * 1000

            for records in records_by_partition.values():
                for record in records:
                    batch.append(_decode_record(record))
                    if batch and (
                        len(batch) >= BATCH_SIZE
                        or (now_ms - batch[0].received_at_ms) >= BATCH_TIMEOUT_MS
                    ):
                        await flush_batch()

            if batch and (now_ms - batch[0].received_at_ms) >= BATCH_TIMEOUT_MS:
                await flush_batch()

        if batch:
            await flush_batch()
    finally:
        with suppress(Exception):
            await consumer.stop()
        with suppress(Exception):
            await producer.stop()


async def main() -> None:
    pool = await asyncpg.create_pool(
        dsn=_asyncpg_dsn(),
        min_size=POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
    )
    try:
        await run_consumer(pool=pool, broadcast_sink="redis")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())