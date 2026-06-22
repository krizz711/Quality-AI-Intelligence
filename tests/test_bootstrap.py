"""Tests for the idempotent first-run bootstrap (scripts/bootstrap.py).

Covers the user-seeding contract that makes the dashboard usable out of the box:
  * a fresh admin is seeded from ADMIN_USERNAME / ADMIN_PASSWORD,
  * re-running never overwrites an existing login,
  * in production no default admin is created without ADMIN_PASSWORD.

DB-backed like the other integration-style tests; each test uses a unique probe
username and cleans up after itself.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

import scripts.bootstrap as bootstrap
from api.auth import verify_password
from db.database import AsyncSessionLocal


async def _fetch_hash(username: str) -> str | None:
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                text("SELECT hashed_password FROM users WHERE username = :u"), {"u": username}
            )
        ).mappings().first()
    return row["hashed_password"] if row else None


async def _delete(username: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
        await session.commit()


@pytest.fixture
def probe_username(monkeypatch):
    username = f"probe_{uuid.uuid4().hex[:10]}"
    monkeypatch.setenv("ADMIN_USERNAME", username)
    yield username


@pytest.mark.asyncio
async def test_ensure_users_seeds_initial_admin(probe_username, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "Sup3rSecret!")
    monkeypatch.setenv("ENVIRONMENT", "development")
    try:
        await bootstrap.ensure_users()
        hashed = await _fetch_hash(probe_username)
        assert hashed is not None
        assert verify_password("Sup3rSecret!", hashed)
    finally:
        await _delete(probe_username)


@pytest.mark.asyncio
async def test_ensure_users_does_not_overwrite_existing(probe_username, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ADMIN_PASSWORD", "FirstPass!")
    try:
        await bootstrap.ensure_users()
        # A later run with a different password must leave the original untouched.
        monkeypatch.setenv("ADMIN_PASSWORD", "SecondPass!")
        await bootstrap.ensure_users()
        hashed = await _fetch_hash(probe_username)
        assert hashed is not None
        assert verify_password("FirstPass!", hashed)
        assert not verify_password("SecondPass!", hashed)
    finally:
        await _delete(probe_username)


@pytest.mark.asyncio
async def test_ensure_users_refuses_default_admin_in_production(probe_username, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    try:
        await bootstrap.ensure_users()  # must refuse to seed without a password
        assert await _fetch_hash(probe_username) is None
    finally:
        await _delete(probe_username)
