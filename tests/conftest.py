"""
tests/conftest.py — shared pytest configuration.

pytest-asyncio is configured project-wide via pyproject.toml
(asyncio_mode = "auto"), so no explicit event-loop fixture is needed here.
This file exists to ensure the project root is on sys.path so that
all internal packages (core, db, schemas, …) are importable during tests.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import asyncio

# Make the project root importable when running pytest from any directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("API_AUTH_KEY", "test-api-key")
# Provide a dummy DATABASE_URL so Settings() can be instantiated without a real DB.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/arad_quality")

# On Windows, asyncpg works best with the SelectorEventLoop policy
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass


@pytest.fixture
async def fake_redis():
    """Provide a fresh fakeredis.aioredis.FakeRedis instance for each test."""
    try:
        import fakeredis.aioredis as fr
        r = fr.FakeRedis()
        yield r
        await r.flushall()
    except Exception:
        # Lightweight fallback for environments without fakeredis installed.
        import time
        import fnmatch

        class SimpleFakeRedis:
            def __init__(self):
                self.store = {}
                self.expiry = {}

            async def get(self, key):
                v = self.store.get(key)
                if v is None:
                    return None
                exp = self.expiry.get(key)
                if exp and time.time() > exp:
                    await self.delete(key)
                    return None
                return v

            async def set(self, key, value, ex=None):
                self.store[key] = value
                if ex:
                    self.expiry[key] = time.time() + ex
                return True

            async def keys(self, pattern):
                return [k for k in self.store.keys() if fnmatch.fnmatch(k, pattern)]

            async def ttl(self, key):
                exp = self.expiry.get(key)
                if not exp:
                    return -1
                return int(max(0, exp - time.time()))

            async def flushall(self):
                self.store.clear()
                self.expiry.clear()

            async def delete(self, key):
                self.store.pop(key, None)
                self.expiry.pop(key, None)

        r = SimpleFakeRedis()
        yield r
        await r.flushall()


@pytest.fixture
async def async_client():
    """Async HTTP client bound to the FastAPI app using ASGITransport."""
    try:
        from httpx import AsyncClient, ASGITransport
        from api.main import app
    except Exception:
        pytest.skip("httpx or api.main.app is not importable")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def db_conn():
    """Provide an asyncpg.Connection with an active transaction that is
    rolled back after the test to keep the test DB clean.

    Requires TEST_DATABASE_URL to be set. Skips the test if not available,
    so pure unit tests run cleanly in CI without a live database.
    """
    import asyncpg

    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL is not set — skipping DB-dependent test. "
            "Run: docker compose up -d timescaledb "
            "then: set TEST_DATABASE_URL=postgresql://arad:arad_pass@localhost:5432/arad_quality"
        )

    conn = await asyncpg.connect(url)
    tr = conn.transaction()
    await tr.start()
    try:
        yield conn
    finally:
        try:
            await tr.rollback()
        except Exception:
            pass
        try:
            await conn.close()
        except Exception:
            pass


@pytest.fixture
async def auth_token(async_client):
    # Single shared auth token fixture; create user if needed.
    resp = await async_client.post(
        "/api/v1/auth/token",
        json={"username": "testuser", "password": "testpass"},
    )
    if resp.status_code == 401:
        await async_client.post(
            "/api/v1/auth/register",
            json={"username": "testuser", "password": "testpass"},
        )
        resp = await async_client.post(
            "/api/v1/auth/token",
            json={"username": "testuser", "password": "testpass"},
        )
    assert resp.status_code == 200, f"Auth failed: {resp.text}"
    return resp.json()["access_token"]

@pytest.fixture
def mock_slack_client():
    """Mock httpx.AsyncClient for Slack webhook tests."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("agent.alerts.httpx.AsyncClient") as mock_ac:
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ac.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_client


@pytest.fixture(autouse=True)
async def cleanup_database_engine():
    yield
    import db.database as db_mod
    if db_mod._engine is not None:
        try:
            await db_mod._engine.dispose()
        except Exception:
            pass
        db_mod._engine = None
        db_mod._AsyncSessionLocal = None

