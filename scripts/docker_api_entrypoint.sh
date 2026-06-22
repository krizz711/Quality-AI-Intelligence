#!/bin/sh
set -e

export DATABASE_URL="$(python /app/scripts/build_database_url.py)"

echo "Waiting for TimescaleDB..."
while ! python /app/scripts/wait_for_tcp.py >/dev/null 2>&1; do
  sleep 2
done

echo "Running Alembic migrations..."
alembic -c /app/alembic.ini upgrade head

echo "Running first-run bootstrap (idempotent)..."
python /app/scripts/bootstrap.py || echo "bootstrap reported a non-fatal issue; continuing"

echo "Starting API..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
