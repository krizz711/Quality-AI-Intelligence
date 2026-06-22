"""Context engineering + state management for the Arad ADK layer (TimescaleDB-backed).

The multi-agent system keeps its conversation and working memory in an ADK
*session*. By default that memory is in-process and lost on restart. This module
persists it in **TimescaleDB** — the same Postgres/Timescale instance the platform
already uses for measurements — through ADK's `DatabaseSessionService`. The payoff:

  * the specialists' structured findings (written to ``session.state`` via each
    agent's ``output_key``) survive across turns **and** across process restarts, so
  * the coordinator can recall a prior GR&R study or SPC scan from state instead of
    recomputing it — genuine context engineering, not a fresh prompt every turn.

Backend resolution (first that works wins; the last option is always available):

  1. ``ADK_SESSION_DB_URL``                       explicit override
  2. ``DATABASE_URL`` → TimescaleDB (async)        the platform DB — the headline path
  3. ``sqlite+aiosqlite:///logs/adk_sessions.db``  file fallback — still persistent
  4. in-memory                                     only if ``ADK_SESSION_BACKEND=memory``
                                                   or everything else fails

Set ``ADK_SESSION_BACKEND=sqlite`` to skip TimescaleDB and use the file DB, or
``ADK_SESSION_BACKEND=memory`` to opt out of persistence entirely.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import adk_agent  # noqa: F401  (loads .env so DATABASE_URL is available)

logger = logging.getLogger(__name__)

APP_NAME = "arad_quality"

# Local file DB used when TimescaleDB is not connected — still survives restarts.
_SQLITE_PATH = Path(__file__).resolve().parent.parent / "logs" / "adk_sessions.db"


def _to_async_url(url: str) -> str:
    """Normalise a SQLAlchemy URL to an async driver ADK's engine can open."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + url[len("postgresql+psycopg2://"):]
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        return "sqlite+aiosqlite://" + url[len("sqlite://"):]
    return url  # already async (asyncpg / aiosqlite) or some other dialect


def _sqlite_uri() -> str:
    _SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{_SQLITE_PATH.as_posix()}"


def _candidate_uris() -> list[tuple[str, str]]:
    """Ordered (uri, human-label) candidates, best first; sqlite always last."""
    backend = os.environ.get("ADK_SESSION_BACKEND", "").lower()
    candidates: list[tuple[str, str]] = []

    if backend == "memory":
        return []  # signals "use in-memory" to make_session_service()

    explicit = os.environ.get("ADK_SESSION_DB_URL")
    if explicit:
        candidates.append((_to_async_url(explicit), "explicit (ADK_SESSION_DB_URL)"))

    database_url = os.environ.get("DATABASE_URL")
    if database_url and backend != "sqlite":
        candidates.append((_to_async_url(database_url), "TimescaleDB (DATABASE_URL)"))

    candidates.append((_sqlite_uri(), "SQLite file (logs/adk_sessions.db)"))
    return candidates


async def _can_connect(uri: str, *, timeout: float = 4.0) -> bool:
    """True if we can open a connection and run ``SELECT 1`` against ``uri``."""
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
    except ImportError:
        return False
    engine = create_async_engine(uri)
    try:
        async with asyncio.timeout(timeout):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # connection refused, auth, missing driver, timeout…
        logger.info("Session backend not reachable (%s): %s", uri.split("@")[-1], exc)
        return False
    finally:
        await engine.dispose()


async def resolve_session_db_uri(*, probe: bool = True) -> str | None:
    """Resolve the best session-store URI, or ``None`` to use in-memory.

    With ``probe=True`` (default) each database URI is connection-tested so a down
    TimescaleDB transparently falls back to the SQLite file. SQLite never needs a
    probe. Returns ``None`` only when ``ADK_SESSION_BACKEND=memory``.
    """
    candidates = _candidate_uris()
    if not candidates:
        return None
    for uri, label in candidates:
        if uri.startswith("sqlite") or not probe or await _can_connect(uri):
            logger.info("ADK session store: %s", label)
            return uri
    return _sqlite_uri()


def resolve_session_db_uri_sync(*, probe: bool = True) -> str | None:
    """Synchronous wrapper for import-time callers (e.g. the FastAPI app)."""
    return asyncio.run(resolve_session_db_uri(probe=probe))


async def make_session_service(*, probe: bool = True):
    """Build the persistent ADK session service, with graceful fallback.

    Returns ``(service, label)`` where ``label`` names the active backend.
    """
    uri = await resolve_session_db_uri(probe=probe)
    if uri is None:
        from google.adk.sessions import InMemorySessionService

        return InMemorySessionService(), "in-memory (not persistent)"
    try:
        from google.adk.sessions import DatabaseSessionService

        label = "TimescaleDB" if uri.startswith("postgresql") else "SQLite file"
        return DatabaseSessionService(db_url=uri), f"{label} ({_safe(uri)})"
    except Exception:
        logger.warning("Falling back to in-memory session store", exc_info=True)
        from google.adk.sessions import InMemorySessionService

        return InMemorySessionService(), "in-memory (DB init failed)"


def build_runner(agent, session_service, *, app_name: str = APP_NAME):
    """Wrap an ADK agent in a Runner backed by the given (persistent) session service."""
    from google.adk.runners import Runner

    return Runner(agent=agent, app_name=app_name, session_service=session_service)


async def get_or_create_session(session_service, *, user_id: str, session_id: str,
                                app_name: str = APP_NAME):
    """Fetch an existing session by id, or create it — so memory persists across runs."""
    try:
        existing = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id)
        if existing is not None:
            return existing
    except Exception:  # backend without a row yet, or transient read error
        logger.debug("get_session miss for %s/%s", user_id, session_id, exc_info=True)
    return await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id)


def _safe(uri: str) -> str:
    """Redact credentials from a URI for logging/printing."""
    if "@" in uri and "://" in uri:
        scheme, rest = uri.split("://", 1)
        return f"{scheme}://…@{rest.split('@', 1)[1]}"
    return uri


async def _info() -> None:
    """`python -m adk_agent.state` — show the active backend and stored sessions."""
    service, label = await make_session_service()
    print(f"ADK session store : {label}")
    try:
        listing = await service.list_sessions(app_name=APP_NAME, user_id="local_user")
        sessions = getattr(listing, "sessions", listing)
        print(f"Sessions (local_user): {len(sessions)}")
        for s in sessions:
            n = len(getattr(s, "state", {}) or {})
            print(f"  - {s.id}  ({n} state keys)")
    except Exception as exc:
        print(f"(could not list sessions: {exc})")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(_info())
