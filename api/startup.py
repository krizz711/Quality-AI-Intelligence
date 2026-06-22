from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from typing import Any, AsyncIterator

import asyncpg
from fastapi import FastAPI
from sqlalchemy.engine import make_url

from api.realtime import state as realtime_state, start_realtime_runtime, stop_realtime_runtime
from core.config import settings
from core import settings_store
from db.database import engine
from db.models import Base

logger = logging.getLogger(__name__)

POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 10

_METRICS_INTERVAL = 30  # seconds between metric refresh cycles


def _asyncpg_dsn() -> str:
    url = make_url(settings.database_url)
    if "+asyncpg" in url.drivername:
        url = url.set(drivername=url.drivername.replace("+asyncpg", ""))
    return url.render_as_string(hide_password=False)


async def _initialize_database_schema() -> None:
    if engine.url.drivername.startswith("sqlite"):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)


async def _metrics_refresher(pool: asyncpg.Pool, stop_event: asyncio.Event) -> None:
    """Periodically update Prometheus gauges that require DB queries."""
    from api.main import alert_queue_depth
    while not stop_event.is_set():
        try:
            count = await pool.fetchval(
                "SELECT COUNT(*) FROM quality_violations WHERE alert_sent = FALSE"
            )
            alert_queue_depth.set(count or 0)
        except Exception as exc:
            logger.warning("metrics_refresh_failed error=%s", exc)
        try:
            await asyncio.wait_for(
                asyncio.shield(stop_event.wait()), timeout=_METRICS_INTERVAL
            )
        except asyncio.TimeoutError:
            pass


async def _broadcast_drainer(stop_event: asyncio.Event) -> None:
    while True:
        if stop_event.is_set() and realtime_state.queue.empty():
            break

        batch: list[dict[str, Any]] = []
        try:
            batch.append(await asyncio.wait_for(realtime_state.queue.get(), timeout=0.05))
        except asyncio.TimeoutError:
            continue

        while len(batch) < 50:
            try:
                batch.append(realtime_state.queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        results = await asyncio.gather(
            *(realtime_state.manager.broadcast(event) for event in batch),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.warning("realtime_broadcast_failed error=%s", result)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    realtime_state.loop = asyncio.get_running_loop()
    await _initialize_database_schema()
    # Load DB-stored integration credentials onto the live settings/env.
    await settings_store.apply_to_runtime()
    await start_realtime_runtime()

    try:
        from agent.consumer import run_consumer
    except Exception:
        run_consumer = None

    pool = await asyncpg.create_pool(
        dsn=_asyncpg_dsn(),
        min_size=POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
    )

    stop_event = asyncio.Event()
    consumer_task = None
    if run_consumer is not None:
        consumer_task = asyncio.create_task(
            run_consumer(
                pool=pool,
                broadcast_queue=realtime_state.queue,
                shutdown_event=stop_event,
                broadcast_sink="queue",
            ),
            name="kafka-consumer",
        )
    broadcast_task = asyncio.create_task(
        _broadcast_drainer(stop_event),
        name="realtime-broadcast-drainer",
    )
    metrics_task = asyncio.create_task(
        _metrics_refresher(pool, stop_event),
        name="metrics-refresher",
    )

    monitor_task = None
    if settings.enable_autonomous_monitor and not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            from agent.monitor import ContinuousMonitor

            monitor_task = asyncio.create_task(
                ContinuousMonitor().run_forever(stop_event),
                name="continuous-monitor",
            )
            logger.info(
                "Autonomous monitor enabled (interval=%ss)",
                settings.monitor_interval_seconds,
            )
        except Exception:
            logger.exception("Failed to start autonomous monitor (continuing without it)")

    mes_task = None
    if settings.enable_mes_connector and not os.environ.get("PYTEST_CURRENT_TEST"):
        # Always start when enabled; the connector re-reads its config each poll and
        # no-ops until MES_API_URL is set (e.g. saved from the dashboard at runtime).
        try:
            from agent.mes_connector import MESConnector

            mes_task = asyncio.create_task(
                MESConnector().run_forever(stop_event),
                name="mes-connector",
            )
            logger.info(
                "MES/QMS connector enabled (poll every %ss)",
                settings.mes_poll_interval_seconds,
            )
        except Exception:
            logger.exception("Failed to start MES connector (continuing without it)")

    app.state.db_pool = pool
    app.state.consumer_task = consumer_task
    app.state.broadcast_task = broadcast_task
    app.state.metrics_task = metrics_task
    app.state.monitor_task = monitor_task
    app.state.mes_task = mes_task

    try:
        yield
    finally:
        stop_event.set()
        for task in (consumer_task, broadcast_task, metrics_task, monitor_task, mes_task):
            if task is not None:
                task.cancel()
        await stop_realtime_runtime()
        for task in (consumer_task, broadcast_task, metrics_task, monitor_task, mes_task):
            if task is not None:
                with suppress(asyncio.CancelledError, Exception):
                    await task
        await pool.close()
        realtime_state.loop = None