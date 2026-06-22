from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis

from core.config import settings

logger = logging.getLogger(__name__)

REALTIME_CHANNEL = "quality.realtime"
REALTIME_DLQ_CHANNEL = "quality.realtime.dlq"


async def authenticate_websocket(websocket: WebSocket) -> bool:
    """
    Validate a JWT or API key passed as ?token=<value> in the WS URL.
    Closes the connection with 4401 if missing or invalid.
    Returns True if authenticated, False otherwise (connection already closed).
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Missing authentication token")
        return False

    # Accept plain API key for service-to-service clients
    if token == settings.api_auth_key:
        return True

    # Accept JWT bearer tokens
    try:
        from jose import JWTError, jwt
        from api.auth import ALGORITHM

        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        if payload.get("sub"):
            return True
        raise ValueError("empty sub claim")
    except Exception:
        await websocket.close(code=4401, reason="Invalid authentication token")
        return False


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections)

        if not connections:
            return

        dead: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                dead.append(websocket)

        for websocket in dead:
            await self.disconnect(websocket)


class RealtimeState:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.manager = WebSocketManager()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.redis: Redis | None = None
        self.started = False
        self.tasks: list[asyncio.Task[Any]] = []


state = RealtimeState()


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event)
    payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    return payload


def enqueue_local_event(event: dict[str, Any]) -> None:
    payload = _normalize_event(event)
    if state.loop is not None and state.loop.is_running():
        state.loop.call_soon_threadsafe(state.queue.put_nowait, payload)
    else:
        state.queue.put_nowait(payload)


async def publish_realtime_event(event: dict[str, Any]) -> None:
    payload = _normalize_event(event)
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.publish(REALTIME_CHANNEL, json.dumps(payload))
        await redis.aclose()
    except Exception as exc:
        logger.warning("Realtime publish fell back to local queue: %s", exc)
        enqueue_local_event(payload)


async def publish_dlq_event(event: dict[str, Any]) -> None:
    payload = _normalize_event(event)
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.publish(REALTIME_DLQ_CHANNEL, json.dumps(payload))
        await redis.aclose()
    except Exception as exc:
        logger.warning("DLQ publish fell back to local queue: %s", exc)
        enqueue_local_event({"type": "dlq.fallback", **payload})


async def _broadcast_worker() -> None:
    while True:
        event = await state.queue.get()
        try:
            await state.manager.broadcast(event)
        except Exception:
            logger.exception("Realtime broadcast failed")


async def _redis_listener() -> None:
    backoff = 1.0
    while True:
        redis = None
        try:
            # health_check_interval keeps the idle pub/sub socket alive; we poll
            # with get_message(timeout=...) so an idle channel returns None
            # instead of raising a socket read TimeoutError.
            redis = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                health_check_interval=30,
            )
            pubsub = redis.pubsub()
            await pubsub.subscribe(REALTIME_CHANNEL, REALTIME_DLQ_CHANNEL)
            backoff = 1.0
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=5.0
                )
                if message is None:
                    continue
                data = message.get("data")
                if not data:
                    continue
                try:
                    enqueue_local_event(json.loads(data))
                except Exception:
                    logger.exception("Failed to decode realtime event")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "Realtime Redis listener unavailable (%s: %s); retrying in %.1fs",
                type(exc).__name__,
                exc,
                backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 5.0)
        finally:
            if redis is not None:
                with suppress(Exception):
                    await redis.aclose()


async def start_realtime_runtime() -> None:
    if state.started:
        return

    state.started = True
    state.loop = asyncio.get_running_loop()
    state.tasks = [
        asyncio.create_task(_redis_listener(), name="realtime-redis-listener"),
    ]


async def stop_realtime_runtime() -> None:
    if not state.started:
        return

    for task in state.tasks:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    state.tasks.clear()
    state.started = False
    state.loop = None
