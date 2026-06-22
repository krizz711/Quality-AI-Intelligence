# Arad Quality Agent — Deployment Guide

This guide takes you from a fresh machine to a running, production-grade deployment
of the Quality Control & GR&R Analysis Agent. It covers the full Docker Compose
stack (recommended), a single-VPS production setup, managed-cloud options, and the
secret-rotation / hardening checklist you must complete before go-live.

The platform delivers:

- **Automated GR&R analysis** — Gage R&R studies with AIAG acceptance verdicts
- **Real-time SPC monitoring** — control limits, Nelson rules, baseline freeze
- **Proactive alerting** — Slack / email / SMS / Jira on threshold breaches
- **AI copilot** — Gemini-backed quality engineering Q&A (optional)
- **Full audit trail** — immutable, exportable (JSON/CSV) for compliance

---

## 0. Architecture at a glance

```
                         ┌────────────────────────────────────────────┐
  Browser ──HTTPS──▶ Dashboard (Next.js :3000)                         │
                         │   └─ /api/backend proxy ──▶ API (FastAPI :8000)
                         │                                  │           │
  MES / line sensors ──▶ Kafka (:9092) ──▶ Consumer ───────┤           │
                         │                                  ▼           │
                         │                     TimescaleDB (Postgres 15)│
                         │                     Redis (realtime pub/sub) │
                         │                     MLflow · Prometheus · Grafana
                         └────────────────────────────────────────────┘
```

| Service | Port (host) | Purpose |
| --- | --- | --- |
| Dashboard | 3000 | Operator UI |
| API | 8000 | REST + WebSocket |
| TimescaleDB | 5433 | Time-series quality data |
| Redis | 6379 | Realtime event bus |
| Kafka | 9092 | Measurement ingestion |
| MLflow | 5000 | Prediction tracking |
| Prometheus | 9090 | Metrics scrape |
| Grafana | 3002 | Dashboards |
| Kafka UI | 8080 | Topic inspection |
| pgAdmin | 5050 | DB admin |

---

## 1. Prerequisites

- **Docker Desktop** (Windows/macOS) or **Docker Engine + Compose v2** (Linux)
- 6 GB RAM free (full stack), 2 vCPU minimum
- A domain name + TLS certificate for any internet-facing deployment
- (Optional) A Gemini API key for AI features — the agent runs fully without it,
  falling back to deterministic statistical narratives

Verify Docker:

```bash
docker --version          # 24+
docker compose version    # v2.x
```

---

## 2. Quick start (local, full stack)

```bash
# 1. Clone and enter the repo root (the ONLY canonical root)
cd Quality_Control_&_GR&R_Analysis_Agent

# 2. Create your env file from the template
cp .env.example .env
#   Edit .env — at minimum set strong API_AUTH_KEY, JWT_SECRET, POSTGRES_PASSWORD.

# 3. Bring up the whole stack
docker compose up --build -d

# 4. Wait for health, then open the dashboard
#    (first build pulls images + compiles the dashboard — a few minutes)
curl http://localhost:8000/health/ready    # {"status":"ready",...}
```

Open **http://localhost:3000**.

Stop / reset:

```bash
docker compose down              # stop, keep data volumes
docker compose down -v           # stop + wipe DB and Grafana volumes (DESTRUCTIVE)
```

---

## 3. Local development (no full stack)

Run only the infra you need in Docker, and the app on the host for fast reloads.

```bash
# Infra: database, cache, message bus
docker compose up -d timescaledb redis kafka

# Backend (host) — uses .venv; reads .env
#   For host runs, uncomment REDIS_URL=redis://localhost:6379/0 in .env
.venv/Scripts/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000   # Windows
# .venv/bin/uvicorn api.main:app --reload --port 8000                       # macOS/Linux

# Dashboard (host)
cd dashboard
cp .env.example .env.local         # set API_URL + API_AUTH_KEY to match the API
npm install
npm run dev
```

The dashboard talks to the API through its own same-origin proxy
(`/api/backend/*`), so the browser never needs CORS and the API key stays
server-side. For the **live WebSocket** in `npm run dev`, set in `.env.local`:

```
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000
NEXT_PUBLIC_API_KEY=<same as API_AUTH_KEY>
```

If the WebSocket origin is unavailable, the UI automatically degrades to HTTP
polling — no data is lost, updates just arrive on an interval.

### Simulate a live MES feed

```bash
.venv/Scripts/python scripts/synthetic_publisher.py --count 30 --delay-ms 400 \
  --equipment-id "CNC-LATHE-07"
```

Measurements flow Kafka → consumer → TimescaleDB → dashboard in real time.

---

## 4. Production deployment — single VPS (Docker Compose)

Best for a first production rollout (one host, e.g. a 4 vCPU / 8 GB cloud VM).

### 4.1 Provision

```bash
# On Ubuntu 22.04+
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker
git clone <your-repo-url> arad-quality && cd arad-quality
```

### 4.2 Configure production secrets

```bash
cp .env.example .env
```

Edit `.env` and set:

```ini
ENVIRONMENT=production
LOG_LEVEL=INFO

# Generate each with: openssl rand -base64 48
API_AUTH_KEY=<48+ char random>
JWT_SECRET=<48+ char random>
POSTGRES_PASSWORD=<strong random>

# Exact dashboard origin(s) — never use "*"
CORS_ORIGINS=https://quality.yourcompany.com
FRONTEND_URL=https://quality.yourcompany.com
DASHBOARD_URL=https://quality.yourcompany.com

# Hard-off for production
ALLOW_MOCK_DATA=false
NEXT_PUBLIC_ALLOW_MOCK_DATA=false

# Admin UIs — strong passwords
PGADMIN_DEFAULT_PASSWORD=<strong>
GRAFANA_ADMIN_PASSWORD=<strong>

# Optional integrations
GEMINI_API_KEY=<key or leave blank>
SLACK_WEBHOOK_URL=<webhook or blank>
```

> In production the API **refuses to start** unless `FRONTEND_URL` is set and
> CORS is locked to exact origins. `ALLOW_MOCK_DATA` is forced off.

### 4.3 Launch

```bash
docker compose up --build -d
docker compose ps                 # all services healthy
curl http://localhost:8000/health/ready
```

### 4.4 Put it behind TLS (Caddy example)

Run a reverse proxy on the host so only 443 is exposed. `Caddyfile`:

```caddyfile
quality.yourcompany.com {
    reverse_proxy localhost:3000          # dashboard (proxies /api/backend → API)
}
```

```bash
docker run -d --network host -v $PWD/Caddyfile:/etc/caddy/Caddyfile \
  -v caddy_data:/data caddy:2
```

Caddy auto-provisions Let's Encrypt TLS. Lock the firewall so only 80/443 are
public; keep 8000/5433/9090/3002/8080/5050 bound to localhost or a private network.

---

## 5. Managed-cloud options

| Platform | Best for | Notes |
| --- | --- | --- |
| **Render** | Fastest managed path | Dashboard = Web Service (Node), API = Web Service (Docker). Add managed Postgres + Redis. Kafka via Upstash/Redpanda Cloud. |
| **Railway** | Simple multi-service | Deploy each compose service; use Railway Postgres + Redis plugins. |
| **Fly.io** | Global / edge | `fly launch` per service; Fly Postgres + Upstash Redis. |
| **AWS ECS/Fargate** | Enterprise scale | Push images to ECR; RDS Postgres (or Timescale Cloud), ElastiCache Redis, MSK Kafka. |
| **GCP Cloud Run** | Serverless API/UI | Cloud SQL + Memorystore; Confluent Cloud for Kafka. |

General managed-deploy recipe:

1. **Build & push images**
   ```bash
   docker build -t <registry>/arad-api:0.1.0 -f docker/api/Dockerfile .
   docker build -t <registry>/arad-dashboard:0.1.0 ./dashboard
   docker push <registry>/arad-api:0.1.0
   docker push <registry>/arad-dashboard:0.1.0
   ```
2. **Provision managed data services** — Postgres (TimescaleDB extension or
   Timescale Cloud), Redis, Kafka.
3. **Set the same `.env` keys** as platform secrets (never bake them into images).
4. **Point the dashboard** `API_URL` at the API service's internal URL.
5. **Run DB migrations** once (see §6).
6. **Wire health checks** to `/health/ready` (API) and `/` (dashboard).

---

## 6. Database migrations

The Compose API entrypoint applies the checked-in TimescaleDB migration on first
boot. For managed Postgres, run Alembic once against your production DSN:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/arad_quality \
  .venv/Scripts/python -m alembic upgrade head
```

Verify hypertables and indexes exist before accepting traffic.

---

## 7. Pre-go-live hardening checklist

- [ ] `ENVIRONMENT=production` and the API starts without the dev-CORS fallback
- [ ] Every secret in `.env` rotated to a strong random value (no template defaults)
- [ ] `API_AUTH_KEY` and `JWT_SECRET` are 48+ random chars, stored in a secret manager
- [ ] `CORS_ORIGINS` / `FRONTEND_URL` list exact HTTPS origins — never `*`
- [ ] `ALLOW_MOCK_DATA=false` and `NEXT_PUBLIC_ALLOW_MOCK_DATA=false`
- [ ] TLS terminates at the proxy; only 80/443 are internet-facing
- [ ] Admin UIs (pgAdmin :5050, Grafana :3002, Kafka UI :8080) are private/VPN-only
- [ ] Postgres + Grafana volumes are on backed-up storage
- [ ] Prometheus scrape + Grafana dashboards confirmed receiving data
- [ ] Alert channels tested end-to-end (Slack/email/SMS/Jira)
- [ ] `/health/ready` returns `db/kafka/redis: ok`
- [ ] Log aggregation in place (JSON logs ship to your stack)

### Rotating a secret after launch

```bash
# 1. Generate and update the value in your secret store / .env
# 2. Recreate only the affected services
docker compose up -d --force-recreate api consumer dashboard
# 3. Update any external clients holding the old API_AUTH_KEY
```

---

## 8. Operations

**Health & readiness**

```bash
curl http://localhost:8000/health         # liveness + dependency snapshot
curl http://localhost:8000/health/ready   # readiness gate (db, kafka, redis)
```

**Logs**

```bash
docker compose logs -f api          # structured JSON logs
docker compose logs -f consumer     # Kafka ingestion (BATCH_METRICS lines)
```

**Metrics & dashboards** — Prometheus scrapes `api:8000/metrics`; Grafana is on
host port **3002** (so the product dashboard keeps **3000**).

**Backups**

```bash
docker compose exec timescaledb pg_dump -U arad arad_quality > backup_$(date +%F).sql
```

**Scaling** — the API and consumer are stateless; run multiple API replicas behind
the proxy and rely on Redis pub/sub for realtime fan-out. Scale the consumer by
adding partitions to `quality.measurements` and running more consumer instances in
the same group.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Dashboard shows "Dashboard unavailable" | API not reachable | `curl /health/ready`; check `API_URL` and the `/api/backend` proxy |
| `cache: unknown` in `/health` | Cosmetic placeholder | Real Redis status is in `/health/ready` |
| Realtime not updating in dev | No WS origin | Set `NEXT_PUBLIC_WS_URL`; otherwise polling fallback applies |
| AI replies "temporarily unavailable" | Gemini quota/key | Set/replace `GEMINI_API_KEY`; deterministic stats still returned |
| Consumer ingests nothing | Topic mismatch | Ensure `MEASUREMENTS_TOPIC=quality.measurements` everywhere |
| API won't start in prod | Missing `FRONTEND_URL` | Set it; production requires explicit CORS origins |
| Alerts not delivered | Channel not configured | Set `SLACK_WEBHOOK_URL` / SMTP / SMS vars; test from Alert Inbox |

---

## 10. Verification gates

```bash
# Release gate (no live services needed)
make prod-check            # backend unit tests + dashboard production build

# Live pipeline gate (requires the Docker stack)
docker compose up --build -d
python -m pytest -m integration -v
```

You're production-ready when `/health/ready` is green, `make prod-check` passes,
and the §7 checklist is fully ticked.
