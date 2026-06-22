"""
Idempotent first-run bootstrap for the Arad Quality Agent.

Runs automatically from the Docker API entrypoint (after Alembic migrations) and
can also be run by hand:

    python scripts/bootstrap.py

Goal: an organisation only ever has to fill in secrets in ``.env`` — on first
boot the platform configures the rest of itself. Every step below is:

  * idempotent  — safe to run on every container start,
  * best-effort — a failing optional step logs a warning and never aborts boot,
  * driven by env — no interactive input.

Steps:
  1. Seed an initial admin login so the dashboard is usable immediately
     (ADMIN_USERNAME / ADMIN_PASSWORD).
  2. Create the MLflow experiments the app logs runs to.
  3. Ensure the Kafka measurement + dead-letter topics exist.
  4. Optionally seed a tiny demo dataset (SEED_DEMO_DATA=true) so the dashboard
     and the autonomous monitor have something to show on a fresh install.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make the project importable when executed as a plain script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("bootstrap")


# ─── helpers ──────────────────────────────────────────────────────────────────

def _asyncpg_dsn() -> str | None:
    """Return an asyncpg-compatible DSN from DATABASE_URL (drops the +asyncpg suffix)."""
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    return url.replace("+asyncpg", "")


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _tcp_reachable(servers: str, timeout: float = 2.0) -> bool:
    """Quick TCP probe of the first host:port in a comma-separated server list."""
    first = servers.split(",")[0].strip()
    if "://" in first:
        first = first.split("://", 1)[1]
    if ":" not in first:
        return False
    host, _, port = first.rpartition(":")
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _hash_password(password: str) -> str:
    """Hash a password with the same bcrypt scheme the API auth layer verifies against."""
    try:
        from passlib.context import CryptContext

        return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)
    except Exception:
        import bcrypt

        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# ─── 1. initial login ─────────────────────────────────────────────────────────

async def ensure_users() -> None:
    """Seed the initial admin login so the dashboard is usable out of the box."""
    dsn = _asyncpg_dsn()
    if not dsn:
        logger.warning("bootstrap.users skipped — DATABASE_URL is not set")
        return

    username = (os.getenv("ADMIN_USERNAME") or "admin").strip() or "admin"
    password = (os.getenv("ADMIN_PASSWORD") or "").strip()
    if not password:
        if _is_production():
            logger.error(
                "bootstrap.users — ADMIN_PASSWORD is not set in production; refusing to seed a "
                "default admin. Set ADMIN_PASSWORD in your environment and restart."
            )
            return
        password = "admin"
        logger.warning(
            "bootstrap.users — ADMIN_PASSWORD not set; seeding dev default admin/'admin'. "
            "Set ADMIN_PASSWORD for any shared or production deployment."
        )

    try:
        import asyncpg

        conn = await asyncpg.connect(dsn)
    except Exception as exc:
        logger.warning("bootstrap.users skipped — cannot connect to database: %s", exc)
        return

    try:
        status = await conn.execute(
            """
            INSERT INTO users (id, username, hashed_password, created_at)
            VALUES ($1::uuid, $2, $3, now())
            ON CONFLICT (username) DO NOTHING
            """,
            uuid.uuid4(),
            username,
            _hash_password(password),
        )
        if status.endswith("1"):
            logger.info("bootstrap.users — seeded initial login '%s'", username)
        else:
            logger.info("bootstrap.users — login '%s' already exists; left unchanged", username)
    except Exception as exc:
        logger.warning("bootstrap.users skipped — %s", exc)
    finally:
        await conn.close()


# ─── 2. MLflow experiments ────────────────────────────────────────────────────

def ensure_mlflow_experiments() -> None:
    """Create the experiments the GR&R / SPC code logs to, if MLflow is reachable."""
    uri = os.getenv("MLFLOW_TRACKING_URI", "").strip()
    if not uri:
        logger.info("bootstrap.mlflow skipped — MLFLOW_TRACKING_URI not set")
        return
    if uri.startswith("http") and not _tcp_reachable(uri):
        logger.warning("bootstrap.mlflow skipped — tracking server %s unreachable", uri)
        return
    try:
        import mlflow

        mlflow.set_tracking_uri(uri)
        for name in ("grr_studies", "spc_models", "spc_predictions"):
            if mlflow.get_experiment_by_name(name) is None:
                mlflow.create_experiment(name)
                logger.info("bootstrap.mlflow — created experiment '%s'", name)
            else:
                logger.info("bootstrap.mlflow — experiment '%s' already exists", name)
    except Exception as exc:
        logger.warning("bootstrap.mlflow skipped — %s", exc)


# ─── 3. Kafka topics ──────────────────────────────────────────────────────────

def ensure_kafka_topics() -> None:
    """Ensure the measurement + DLQ topics exist (the broker also auto-creates them)."""
    servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "").strip()
    if not servers:
        logger.info("bootstrap.kafka skipped — KAFKA_BOOTSTRAP_SERVERS not set")
        return
    if not _tcp_reachable(servers):
        logger.warning("bootstrap.kafka skipped — broker %s unreachable", servers)
        return

    topic = os.getenv("MEASUREMENTS_TOPIC", "quality.measurements")
    dlq = os.getenv("MEASUREMENTS_DLQ_TOPIC", "quality.measurements.dlq")
    try:
        from confluent_kafka.admin import AdminClient, NewTopic

        admin = AdminClient({"bootstrap.servers": servers})
        existing = set(admin.list_topics(timeout=5).topics)
        wanted = [NewTopic(t, num_partitions=1, replication_factor=1) for t in (topic, dlq) if t not in existing]
        if not wanted:
            logger.info("bootstrap.kafka — topics already present")
            return
        for name, future in admin.create_topics(wanted).items():
            try:
                future.result()
                logger.info("bootstrap.kafka — created topic '%s'", name)
            except Exception as exc:  # noqa: PERF203 — per-topic reporting
                logger.warning("bootstrap.kafka — topic '%s' not created: %s", name, exc)
    except Exception as exc:
        logger.warning("bootstrap.kafka skipped — %s", exc)


# ─── 4. optional demo data ────────────────────────────────────────────────────

async def seed_demo_data() -> None:
    """Insert a small, stable demo series so a fresh install isn't empty."""
    dsn = _asyncpg_dsn()
    if not dsn:
        logger.warning("bootstrap.demo skipped — DATABASE_URL is not set")
        return
    try:
        import asyncpg

        conn = await asyncpg.connect(dsn)
    except Exception as exc:
        logger.warning("bootstrap.demo skipped — cannot connect to database: %s", exc)
        return

    part_number = os.getenv("DEMO_PART_NUMBER", "DEMO-PART-001")
    characteristic = os.getenv("DEMO_CHARACTERISTIC", "bore_diameter")
    try:
        existing = await conn.fetchval(
            "SELECT count(*) FROM measurements WHERE part_number = $1 AND characteristic_name = $2",
            part_number,
            characteristic,
        )
        if existing and int(existing) > 0:
            logger.info("bootstrap.demo — demo series already present (%s rows)", existing)
            return

        base = datetime.now(timezone.utc) - timedelta(minutes=60)
        rows = []
        nominal = 12.000
        for i in range(60):
            # Stable process around nominal with a single deliberate out-of-control spike.
            value = nominal + (0.0009 * ((i % 7) - 3))
            if i == 50:
                value = nominal + 0.02  # special-cause point for the monitor to catch
            rows.append(
                (
                    base + timedelta(minutes=i),
                    part_number,
                    characteristic,
                    nominal,
                    round(value, 5),
                    "mm",
                    f"OP{i % 3}",
                    "CMM-DEMO-01",
                    "A",
                    uuid.uuid4().hex,
                    "bootstrap-demo",
                )
            )
        await conn.executemany(
            """
            INSERT INTO measurements (
                timestamp, part_number, characteristic_name, nominal_value,
                measured_value, unit, operator_id, equipment_id, shift,
                source_event_id, created_by
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (source_event_id, timestamp) DO NOTHING
            """,
            rows,
        )
        logger.info("bootstrap.demo — seeded %d demo measurements for %s/%s", len(rows), part_number, characteristic)
    except Exception as exc:
        logger.warning("bootstrap.demo skipped — %s", exc)
    finally:
        await conn.close()


# ─── orchestration ────────────────────────────────────────────────────────────

async def run() -> None:
    logger.info("bootstrap starting (environment=%s)", os.getenv("ENVIRONMENT", "development"))
    await ensure_users()
    ensure_mlflow_experiments()
    ensure_kafka_topics()
    if _truthy("SEED_DEMO_DATA"):
        await seed_demo_data()
    logger.info("bootstrap complete")


def main() -> int:
    try:
        asyncio.run(run())
    except Exception:  # never let bootstrap crash container start
        logger.exception("bootstrap encountered an unexpected error (continuing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
