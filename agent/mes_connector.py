"""
MES/QMS API connector — scheduled, hands-off measurement ingestion.

Polls an organisation's Manufacturing Execution System / Quality Management
System REST API on a fixed interval, pulls *new* measurement records
(incrementally, using a server-side "since" watermark), maps them onto the
internal measurement schema, and ingests them. The autonomous monitor
(``agent/monitor.py``) then analyses the new data and raises alerts — so once
``MES_API_URL`` is configured the whole load → analyse → alert loop runs with no
human action.

It is configuration-driven so it works against most JSON REST APIs without code
changes (all read from the environment):

  MES_API_URL              measurements endpoint URL (presence enables the connector)
  MES_API_TOKEN            bearer token -> sent as ``Authorization: Bearer <token>``
  MES_AUTH_HEADER          custom auth header name (use instead of bearer)
  MES_AUTH_VALUE           custom auth header value
  MES_RECORDS_PATH         dotted path to the records array in the response
                           ("" = top-level array, or e.g. "data" / "result.items")
  MES_FIELD_MAP            JSON mapping our_field -> their_field (identity by default)
  MES_ID_FIELD             record field to use as the dedup id (optional)
  MES_SINCE_PARAM          query-param name for the incremental watermark (e.g. "since")
  MES_POLL_INTERVAL_SECONDS poll cadence (falls back to settings.mes_poll_interval_seconds)
  MES_HTTP_TIMEOUT         per-request timeout in seconds (default 15)

The watermark is simply ``max(timestamp)`` of rows already ingested from the
connector, so it survives restarts with no extra storage, and ingestion upserts
with ``ON CONFLICT (source_event_id, timestamp) DO NOTHING`` so re-pulls are safe.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text

from core.config import settings
from db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Fields we map from the source record onto the measurements table.
_TARGET_FIELDS = [
    "timestamp",
    "part_number",
    "characteristic_name",
    "nominal_value",
    "measured_value",
    "unit",
    "operator_id",
    "equipment_id",
    "shift",
]

_INGEST_SQL = text(
    """
    INSERT INTO measurements (
        timestamp, part_number, characteristic_name, nominal_value, measured_value,
        unit, operator_id, equipment_id, shift, source_event_id, created_by
    ) VALUES (
        :timestamp, :part_number, :characteristic_name, :nominal_value, :measured_value,
        :unit, :operator_id, :equipment_id, :shift, :source_event_id, 'mes-connector'
    )
    ON CONFLICT (source_event_id, timestamp) DO NOTHING
    """
)


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text_value = str(value)
    return text_value[:64] if text_value else None


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class MESConnector:
    """Polls an MES/QMS REST API and ingests new measurements."""

    def __init__(self) -> None:
        self._reload()

    def _reload(self) -> None:
        """(Re-)read configuration from the environment.

        ``core.settings_store.apply_to_runtime()`` pushes dashboard-saved settings
        onto ``os.environ``, so re-reading here each poll lets an operator configure
        the whole connector from the UI with no process restart.
        """
        self.url = os.getenv("MES_API_URL", "").strip()
        self.token = os.getenv("MES_API_TOKEN", "").strip()
        self.auth_header = os.getenv("MES_AUTH_HEADER", "").strip()
        self.auth_value = os.getenv("MES_AUTH_VALUE", "").strip()
        self.records_path = os.getenv("MES_RECORDS_PATH", "").strip()
        self.id_field = os.getenv("MES_ID_FIELD", "").strip()
        self.since_param = os.getenv("MES_SINCE_PARAM", "").strip()
        self.timeout = _to_float(os.getenv("MES_HTTP_TIMEOUT")) or 15.0
        self.interval = int(
            os.getenv("MES_POLL_INTERVAL_SECONDS", str(settings.mes_poll_interval_seconds))
        )
        self.field_map = self._load_field_map()

    # ── configuration ─────────────────────────────────────────────────────────

    def _load_field_map(self) -> dict[str, str]:
        raw = os.getenv("MES_FIELD_MAP", "").strip()
        mapping: dict[str, str] = {}
        if raw:
            try:
                mapping = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("MES_FIELD_MAP is not valid JSON; using identity field mapping")
        # Identity default: an unmapped field is read from the same-named source key.
        return {field: str(mapping.get(field, field)) for field in _TARGET_FIELDS}

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.auth_header and self.auth_value:
            headers[self.auth_header] = self.auth_value
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # ── response shaping ───────────────────────────────────────────────────────

    def _extract_records(self, payload: Any) -> list[Any]:
        if not self.records_path:
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                for key in ("data", "results", "items", "measurements"):
                    if isinstance(payload.get(key), list):
                        return payload[key]
            return []
        node: Any = payload
        for part in self.records_path.split("."):
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return []
        return node if isinstance(node, list) else []

    def _map_record(self, record: Any) -> dict[str, Any] | None:
        if not isinstance(record, dict):
            return None
        fmap = self.field_map

        def src(field: str) -> Any:
            return record.get(fmap[field])

        timestamp = _parse_timestamp(src("timestamp"))
        measured_value = _to_float(src("measured_value"))
        if timestamp is None or measured_value is None:
            return None  # a record without a timestamp + numeric value is unusable

        part_number = _str_or_none(src("part_number")) or _str_or_none(src("equipment_id")) or "UNKNOWN"
        characteristic_name = (_str_or_none(src("characteristic_name")) or "value")[:128]

        if self.id_field and record.get(self.id_field) is not None:
            source_event_id = str(record[self.id_field])[:64]
        else:
            digest = hashlib.sha1(
                f"{part_number}|{characteristic_name}|{timestamp.isoformat()}|{measured_value}".encode()
            ).hexdigest()
            source_event_id = digest[:32]

        return {
            "timestamp": timestamp,
            "part_number": part_number[:64],
            "characteristic_name": characteristic_name,
            "nominal_value": _to_float(src("nominal_value")),
            "measured_value": measured_value,
            "unit": _str_or_none(src("unit")),
            "operator_id": _str_or_none(src("operator_id")),
            "equipment_id": _str_or_none(src("equipment_id")),
            "shift": _str_or_none(src("shift")),
            "source_event_id": source_event_id,
        }

    # ── fetch + ingest ─────────────────────────────────────────────────────────

    async def _watermark(self) -> datetime | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT max(timestamp) FROM measurements WHERE created_by = 'mes-connector'")
            )
            return result.scalar()

    async def _fetch(self, params: dict[str, Any]) -> Any:
        """Perform the HTTP GET and return parsed JSON. Isolated for testability."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.url, headers=self._headers(), params=params)
            response.raise_for_status()
            return response.json()

    async def _ingest(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        async with AsyncSessionLocal() as session:
            await session.execute(_INGEST_SQL, rows)
            await session.commit()
        return len(rows)

    async def poll_once(self) -> dict[str, Any]:
        """Pull one batch of new records and ingest them. Never raises."""
        self._reload()
        if not self.url:
            return {"status": "disabled"}

        watermark = None
        params: dict[str, Any] = {}
        if self.since_param:
            try:
                watermark = await self._watermark()
            except Exception:
                logger.debug("mes_connector.watermark_failed", exc_info=True)
            if watermark is not None:
                params[self.since_param] = watermark.isoformat()

        try:
            payload = await self._fetch(params)
        except Exception as exc:
            logger.warning("mes_connector.poll_failed url=%s error=%s", self.url, exc)
            return {"status": "error", "error": str(exc)}

        records = self._extract_records(payload)
        mapped = [m for m in (self._map_record(r) for r in records) if m is not None]
        try:
            ingested = await self._ingest(mapped)
        except Exception as exc:
            logger.warning("mes_connector.ingest_failed error=%s", exc)
            return {"status": "error", "error": str(exc), "fetched": len(records)}

        if records:
            logger.info(
                "mes_connector.poll fetched=%s mapped=%s ingested=%s",
                len(records),
                len(mapped),
                ingested,
            )
        return {"status": "ok", "fetched": len(records), "mapped": len(mapped), "ingested": ingested}

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        logger.info("MESConnector started (url=%s interval=%ss)", self.url, self.interval)
        while not stop_event.is_set():
            try:
                await self.poll_once()
            except Exception:
                logger.exception("mes_connector.cycle_failed")
            try:
                await asyncio.wait_for(asyncio.shield(stop_event.wait()), timeout=self.interval)
            except asyncio.TimeoutError:
                pass
        logger.info("MESConnector stopped")
