#!/usr/bin/env bash
set -e

DB_HOST=${DB_HOST:-timescaledb}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_NAME=${DB_NAME:-arad_quality}

echo "Waiting for TimescaleDB at ${DB_HOST}:${DB_PORT} to be ready..."
# Use helper python script to avoid shell quoting issues
while ! python /app/scripts/wait_for_tcp.py >/dev/null 2>&1; do
  echo "  DB not ready yet — sleeping 2s"
  sleep 2
done

echo "TimescaleDB is ready. Running Alembic migrations..."
# Use the repository's alembic.ini by default
alembic -c /app/alembic.ini upgrade heads
echo "Migrations complete."
