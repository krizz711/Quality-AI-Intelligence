import os
import subprocess
import pytest
import asyncpg

REQUIRED_TABLES = [
    "measurements",
    "alerts",
    "notification_deliveries",
    "audit_logs",
    "users",
]

REQUIRED_INDEXES = [
    ("measurements", "idx_measurements_source_event_id"),
]


@pytest.mark.asyncio
async def test_all_required_tables_exist():
    # asyncpg expects a DSN with scheme 'postgresql'; strip any SQLAlchemy driver
    # suffix like '+asyncpg' if present so tests can consume SQLAlchemy-style URLs.
    dsn = os.environ["TEST_DATABASE_URL"]
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn)
    try:
        existing = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """)
        existing_names = {row["tablename"] for row in existing}

        missing = [t for t in REQUIRED_TABLES if t not in existing_names]
        assert missing == [], (
            f"These tables are missing after alembic upgrade head: {missing}\n"
            f"Existing tables: {sorted(existing_names)}"
        )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_all_required_indexes_exist():
    dsn = os.environ["TEST_DATABASE_URL"]
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn)
    try:
        for table, index_name in REQUIRED_INDEXES:
            exists = await conn.fetchval("""
                SELECT COUNT(*) FROM pg_indexes
                WHERE tablename = $1 AND indexname = $2
            """, table, index_name)
            assert exists == 1, (
                f"Missing index {index_name} on table {table}"
            )
    finally:
        await conn.close()


def _run_alembic():
    return subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)


def test_migrations_are_idempotent():
    result1 = _run_alembic()
    assert result1.returncode == 0, f"First alembic upgrade head failed:\n{result1.stderr}"

    result2 = _run_alembic()
    assert result2.returncode == 0, f"Second alembic upgrade head failed:\n{result2.stderr}"


def test_downgrade_and_upgrade_roundtrip():
    # Use an explicit revision rather than -1 to avoid an "Ambiguous walk"
    # error. Relative steps cannot be resolved when the history graph contains
    # a merge point (2b2656005ada) with two parents. We step back to the last
    # linear revision before the branch diverged.
    down = subprocess.run(
        ["alembic", "downgrade", "e9501605a8c2"],
        capture_output=True, text=True,
    )
    assert down.returncode == 0, f"alembic downgrade e9501605a8c2 failed:\n{down.stderr}"

    up = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    assert up.returncode == 0, f"alembic upgrade head after downgrade failed:\n{up.stderr}"
