# Arad Quality Agent — Operational Runbook

> **Purpose**: Step-by-step procedures for operating, troubleshooting, and recovering the Arad Quality Agent production system. Every section should be tested by a team member who did not write it before go-live.

---

## Table of Contents

1. [Service Overview](#service-overview)
2. [Startup Procedure](#startup-procedure)
3. [Shutdown Procedure](#shutdown-procedure)
4. [Kafka Consumer Restart](#kafka-consumer-restart)
5. [Database Migration Rollback](#database-migration-rollback)
6. [Alert Escalation Procedure](#alert-escalation-procedure)
7. [Secrets Rotation](#secrets-rotation)
8. [Monitoring & Alerting](#monitoring--alerting)
9. [Common Failure Scenarios](#common-failure-scenarios)
10. [Emergency Contacts](#emergency-contacts)

---

## Service Overview

| Service | Port | Purpose |
|---------|------|---------|
| `api` | 8000 | FastAPI backend — GR&R, SPC, alerts, auth |
| `dashboard` | 3000 | Next.js quality engineer UI |
| `timescaledb` | 5432 | TimescaleDB — measurements + audit trail |
| `kafka` | 9092 | Measurement stream ingestion |
| `zookeeper` | 2181 | Kafka coordination |
| `redis` | 6379 | Rate limiting + alert deduplication |
| `mlflow` | 5000 | Experiment tracking |
| `prometheus` | 9090 | Metrics scraping |
| `grafana` | 3002 | Operational dashboard |
| `kafka-ui` | 8080 | Kafka topic browser |
| `pgadmin` | 5050 | Database browser |

**Health probes:**
- Liveness: `GET http://localhost:8000/health/live` — process alive
- Readiness: `GET http://localhost:8000/health/ready` — DB + Kafka + Redis all reachable

---

## Startup Procedure

### Prerequisites
1. `.env` file present with all required secrets (see `.env.example`).
2. Docker Engine ≥ 25, Docker Compose ≥ 2.20 installed.
3. Ports 3000, 5432, 8000, 9092 not in use on host.

### Steps

```bash
# 1. Copy and fill environment variables
cp .env.example .env
$EDITOR .env   # set API_AUTH_KEY, POSTGRES_PASSWORD, GRAFANA_ADMIN_PASSWORD

# 2. Build images (skip --build on subsequent starts if code unchanged)
docker compose up --build -d

# 3. Wait for readiness (up to 120s)
until curl -sf http://localhost:8000/health/ready | grep -q '"status":"ready"'; do
  sleep 5; echo "waiting..."
done
echo "Stack is ready."

# 4. Run database migrations (idempotent — safe to re-run)
docker compose exec api alembic upgrade head

# 5. Verify all services healthy
docker compose ps

# 6. Check Grafana dashboard
open http://localhost:3002   # login: admin / <GRAFANA_ADMIN_PASSWORD from .env>
```

**Expected output from `docker compose ps`:**

```
NAME            STATUS          PORTS
api             running (healthy)   0.0.0.0:8000->8000/tcp
timescaledb     running (healthy)   0.0.0.0:5432->5432/tcp
kafka           running (healthy)   0.0.0.0:9092->9092/tcp
redis           running (healthy)   0.0.0.0:6379->6379/tcp
...
```

---

## Shutdown Procedure

### Graceful shutdown (maintenance / upgrade)

```bash
# 1. Stop accepting new requests — scale API to 0
docker compose stop api dashboard

# 2. Wait for in-flight Kafka consumer to drain (max 60s)
sleep 60

# 3. Stop remaining services
docker compose down

# 4. Verify no dangling processes
docker ps -a | grep arad
```

### Emergency stop (all services immediately)

```bash
docker compose down --timeout 5
```

> **Warning**: Hard-stopping Kafka before the consumer drains may cause duplicate processing on restart. Review consumer group offsets afterward (see [Kafka Consumer Restart](#kafka-consumer-restart)).

---

## Kafka Consumer Restart

Use when: consumer is stuck, offset lag is growing (Grafana `kafka_consumer_lag_messages > 1000`), or after a crash.

```bash
# 1. Check current lag
docker compose exec kafka \
  kafka-consumer-groups.sh \
  --bootstrap-server localhost:29092 \
  --describe --group arad-quality-agent-test-consumer

# 2. Restart the consumer (built into the API service)
docker compose restart api

# 3. Watch lag recover in Grafana (should drop within 60s for typical load)
# Panel: "Kafka Consumer Lag" — target: 0 within 2 minutes

# 4. If consumer is permanently stuck at an error offset, reset to latest
# (WARNING: messages between old and new offset will be skipped)
docker compose exec kafka \
  kafka-consumer-groups.sh \
  --bootstrap-server localhost:29092 \
  --group arad-quality-agent-test-consumer \
  --topic measurements.test \
  --reset-offsets --to-latest --execute
```

### Verify consumer resumed

```bash
# Should see recent measurement timestamps in DB
docker compose exec timescaledb \
  psql -U arad -d arad_quality -c \
  "SELECT MAX(measured_at) FROM measurements;"
```

---

## Database Migration Rollback

Use when: a migration introduces a regression and must be reverted.

### Check current migration state

```bash
docker compose exec api alembic current
docker compose exec api alembic history --verbose
```

### Roll back one revision

```bash
# Identify the previous revision from alembic history output, e.g. "abc123"
docker compose exec api alembic downgrade -1
```

### Roll back to a specific revision

```bash
docker compose exec api alembic downgrade <revision_id>
```

### Roll back all migrations (nuclear — destroys schema)

```bash
docker compose exec api alembic downgrade base
```

> **After rollback**: if rolling back removes a column that the running API expects, the API will crash. Either redeploy the previous API version first, or apply the fix-forward migration immediately after rollback.

### Point-in-time restore from TimescaleDB backup

TimescaleDB supports continuous aggregation and WAL-based backups. For a full PITR:

```bash
# Stop API to prevent writes during restore
docker compose stop api

# Restore from backup (example: pg_restore from S3)
pg_restore -h localhost -U arad -d arad_quality backup.dump

# Reapply any migrations that post-date the backup
docker compose exec api alembic upgrade head

# Restart API
docker compose start api
```

---

## Alert Escalation Procedure

The system generates three alert severities from Nelson rule violations:

| Severity | Source | Auto-action | Human escalation |
|----------|--------|-------------|-----------------|
| `critical` | nelson_rule_1 (3σ breach) | Slack + SMS (if configured) | Page on-call within 15 min |
| `warning` | nelson_rule_2/3 (shift/trend) | Slack | Review within 4 hours |
| `info` | all other rules | Slack only | Review at next daily standup |

### Alert stuck in queue (alert_queue_depth > 0 for > 10 min)

```bash
# Check unsent violations
docker compose exec timescaledb \
  psql -U arad -d arad_quality -c \
  "SELECT id, part_number, violation_type, created_at
   FROM quality_violations WHERE alert_sent = FALSE
   ORDER BY created_at LIMIT 20;"

# Manually trigger alert engine
docker compose exec api \
  python -c "
import asyncio
from agent.alert_engine import AlertEngine
asyncio.run(AlertEngine().process_pending_violations())
"
```

### False positive suppression

If a sensor is malfunctioning and generating thousands of violations:

```bash
# Mark all unsent violations for the faulty sensor as sent (suppresses alerts)
docker compose exec timescaledb \
  psql -U arad -d arad_quality -c \
  "UPDATE quality_violations
   SET alert_sent = TRUE
   WHERE part_number = '<PART_NUMBER>'
     AND alert_sent = FALSE;"
```

> **Always create an audit log entry when manually suppressing alerts.**

### Acknowledge all active alerts via API

```bash
# Requires a valid JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<password>"}' \
  | jq -r .access_token)

# List active alerts
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/alerts?status=active | jq .
```

---

## Secrets Rotation

### API Auth Key

```bash
# 1. Generate a new strong key (min 32 chars)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Update .env (local) and GitHub Secrets (CI)
# In GitHub: Settings → Secrets → API_AUTH_KEY

# 3. Restart API to pick up the new key
docker compose restart api

# 4. Verify health
curl http://localhost:8000/health/live
```

### JWT Secret

Same procedure as API Auth Key. Rotating JWT_SECRET invalidates all existing tokens — users must log in again.

### Database Password

```bash
# 1. Update POSTGRES_PASSWORD in .env
# 2. Change password in database
docker compose exec timescaledb \
  psql -U arad -c "ALTER USER arad WITH PASSWORD '<new_password>';"

# 3. Restart API and consumer to pick up new DATABASE_URL
docker compose restart api
```

---

## Monitoring & Alerting

### Key Grafana panels to watch

| Panel | Green | Yellow | Red |
|-------|-------|--------|-----|
| API p99 latency | < 500ms | 500ms–1s | > 1s |
| Kafka consumer lag | 0 | 100–1000 | > 1000 |
| Alert queue depth | 0 | 10–50 | > 50 |
| Pending GR&R reviews | 0–5 | 5–20 | > 20 |

### Prometheus alert rules (add to `monitoring/prometheus.yml`)

```yaml
groups:
  - name: arad-quality
    rules:
      - alert: KafkaConsumerLagHigh
        expr: kafka_consumer_lag_messages > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Kafka consumer lag {{ $value }} messages"

      - alert: APILatencyHigh
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API p99 latency {{ $value }}s"

      - alert: AlertQueueDepthHigh
        expr: alert_queue_depth > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "{{ $value }} unsent quality violation alerts"
```

---

## Common Failure Scenarios

### API exits immediately at startup

**Symptoms**: `docker compose ps` shows api as `exited (1)`.

```bash
docker compose logs api --tail 50
```

**Common causes:**
- `DATABASE_URL` not set or wrong format → check `.env`
- `API_AUTH_KEY` missing → set in `.env`
- TimescaleDB not ready yet → `docker compose up -d timescaledb && sleep 20 && docker compose up -d api`

---

### Kafka consumer not ingesting

**Symptoms**: Grafana shows Kafka lag growing, no new rows in `measurements`.

```bash
docker compose logs api | grep -i "kafka\|consumer\|error"
```

**Fix**: Restart API to re-initialize the consumer connection.

```bash
docker compose restart api
```

---

### TimescaleDB out of disk

**Symptoms**: API logs `FATAL: could not write to file`.

```bash
docker system df          # check disk usage
docker volume ls          # find timescale_data volume
```

**Fix**: Expand disk or run TimescaleDB chunk compression:

```bash
docker compose exec timescaledb \
  psql -U arad -d arad_quality -c \
  "SELECT compress_chunk(c) FROM show_chunks('measurements') c;"
```

---

### Grafana shows no data

**Symptoms**: All panels show "No data".

1. Verify Prometheus is scraping: `http://localhost:9090/targets`
2. Verify API `/metrics` endpoint: `curl http://localhost:8000/metrics | head -20`
3. Check Grafana datasource: Settings → Data Sources → Prometheus → Test

---

## Emergency Contacts

> Fill in before go-live.

| Role | Name | Contact |
|------|------|---------|
| On-call engineer | _TBD_ | _TBD_ |
| DB admin | _TBD_ | _TBD_ |
| Platform lead | _TBD_ | _TBD_ |
| Escalation (P1) | _TBD_ | _TBD_ |
