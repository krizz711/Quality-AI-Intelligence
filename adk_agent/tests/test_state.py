"""Tests for the TimescaleDB-backed session/state layer (adk_agent.state).

These run with no API key and no Postgres — they use a temp SQLite file to prove the
*persistence* plumbing (the same DatabaseSessionService ADK uses against TimescaleDB).
The headline test writes a finding into session state, throws the service away, opens a
brand-new one on the same file, and shows the state survived — i.e. memory persists
across process restarts.
"""

import pytest

from adk_agent import state as state_mod


# ─── URL normalisation (pure) ────────────────────────────────────────────────

def test_to_async_url_normalises_postgres():
    assert state_mod._to_async_url("postgresql://u:p@h:5433/db") == \
        "postgresql+asyncpg://u:p@h:5433/db"
    assert state_mod._to_async_url("postgres://u:p@h:5433/db") == \
        "postgresql+asyncpg://u:p@h:5433/db"
    assert state_mod._to_async_url("postgresql+psycopg2://u@h/db") == \
        "postgresql+asyncpg://u@h/db"
    # already-async URLs pass through unchanged
    assert state_mod._to_async_url("postgresql+asyncpg://u@h/db") == \
        "postgresql+asyncpg://u@h/db"
    assert state_mod._to_async_url("sqlite:///a.db") == "sqlite+aiosqlite:///a.db"


def test_backend_memory_opts_out(monkeypatch):
    monkeypatch.setenv("ADK_SESSION_BACKEND", "memory")
    assert state_mod._candidate_uris() == []


def test_backend_sqlite_skips_database_url(monkeypatch):
    monkeypatch.setenv("ADK_SESSION_BACKEND", "sqlite")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5433/db")
    uris = [u for u, _ in state_mod._candidate_uris()]
    assert all("postgresql" not in u for u in uris)
    assert uris and uris[-1].startswith("sqlite+aiosqlite://")


# ─── Persistence (SQLite stand-in for TimescaleDB) ───────────────────────────

def _service(db_path):
    from google.adk.sessions import DatabaseSessionService

    return DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{db_path.as_posix()}")


async def _write_state(service, session, **delta):
    from google.adk.events import Event, EventActions

    await service.append_event(
        session, Event(author="process_monitor", actions=EventActions(state_delta=delta)))


@pytest.mark.asyncio
async def test_state_persists_across_service_restarts(tmp_path):
    db = tmp_path / "sessions.db"
    app, user, sid = state_mod.APP_NAME, "tester", "sess-1"

    # First "process": create the session and record a specialist finding in state.
    svc1 = _service(db)
    sess = await state_mod.get_or_create_session(
        svc1, user_id=user, session_id=sid, app_name=app)
    await _write_state(svc1, sess, last_spc_scan="2 special-cause violations on CNC-07")

    # Second "process": a brand-new service/engine on the SAME file must see it.
    svc2 = _service(db)
    again = await state_mod.get_or_create_session(
        svc2, user_id=user, session_id=sid, app_name=app)
    assert again.id == sid
    assert again.state.get("last_spc_scan") == "2 special-cause violations on CNC-07"


@pytest.mark.asyncio
async def test_get_or_create_session_is_idempotent(tmp_path):
    db = tmp_path / "sessions.db"
    app, user, sid = state_mod.APP_NAME, "tester", "dup"
    svc = _service(db)

    first = await state_mod.get_or_create_session(
        svc, user_id=user, session_id=sid, app_name=app)
    await _write_state(svc, first, last_copq="$5,400")
    second = await state_mod.get_or_create_session(
        svc, user_id=user, session_id=sid, app_name=app)

    assert first.id == second.id == sid
    assert second.state.get("last_copq") == "$5,400"  # same session, not a fresh one


@pytest.mark.asyncio
async def test_make_session_service_falls_back_to_sqlite(monkeypatch, tmp_path):
    # No Postgres reachable, no explicit URL → should land on a persistent SQLite store.
    monkeypatch.delenv("ADK_SESSION_DB_URL", raising=False)
    monkeypatch.setenv("ADK_SESSION_BACKEND", "sqlite")
    service, label = await state_mod.make_session_service(probe=False)
    assert "SQLite" in label
    sess = await service.create_session(app_name=state_mod.APP_NAME, user_id="u")
    assert sess.id
