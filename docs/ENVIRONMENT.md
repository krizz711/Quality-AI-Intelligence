# Environment configuration

## Single source of truth

All configuration lives in **one file at the repo root**:

```
Quality_Control_&_GR&R_Analysis_Agent/
├── .env              ← your secrets (gitignored)
├── .env.example      ← template (committed)
└── docker-compose.yml ← reads root .env automatically
```

There must be **no** second `.env` under `arad-quality-agent/`. That folder is a legacy nested clone and is gitignored.

## First-time setup

```bash
cp .env.example .env
# Edit .env — set API_AUTH_KEY, POSTGRES_PASSWORD, optional Slack/Jira/Gemini

docker compose up --build
```

If you still have secrets in `arad-quality-agent/.env`:

```bash
python scripts/bootstrap_env.py
```

That copies integration tokens into root `.env` with Docker-safe defaults.

## Docker vs local development

| Variable | Docker Compose | Local `make run-api` |
|----------|----------------|----------------------|
| `DATABASE_URL` | Overridden in compose (`timescaledb:5432`) | Use root `.env` (`localhost:5433`) |
| `REDIS_URL` | Default `redis://redis:6379` | Set `redis://localhost:6379/0` |
| `API_URL` | Dashboard uses `http://api:8000` | Set `http://localhost:8000` for `npm run dev` |
| `KAFKA_BOOTSTRAP_SERVERS` | Overridden to `kafka:29092` in API container | `localhost:9092` on host |

**Rule:** run `docker compose` only from the **repo root**, never from `arad-quality-agent/`.

## Required secrets

| Variable | Purpose |
|----------|---------|
| `API_AUTH_KEY` | Dashboard + API authentication (min 32 chars in production) |
| `POSTGRES_PASSWORD` | TimescaleDB + MLflow backend |

## Optional integrations

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | AI Copilot, GR&R narratives (core stats work without it) |
| `SLACK_WEBHOOK_URL` | Alert notifications |
| `JIRA_*` | Auto-create tickets on critical alerts |
| `SMTP_*` | Email alerts |

## Dashboard API key

The dashboard container receives `API_AUTH_KEY` from root `.env`. In the UI: **Settings → API key** must match the same value.

## Passwords with special characters (`@`, `!`, etc.)

`POSTGRES_PASSWORD` may contain symbols that break naive URL strings. Docker services build `DATABASE_URL` via `scripts/build_database_url.py` at startup.

If you change `POSTGRES_PASSWORD` after the first `docker compose up`, the existing TimescaleDB volume keeps the **old** password. Either:

```bash
docker compose down
docker volume rm quality_control__grr_analysis_agent_timescale_data
docker compose up -d
```

…or keep the password that matches the volume.

## Removing the legacy folder

After `bootstrap_env.py` and verifying the stack:

```powershell
Remove-Item -Recurse -Force .\arad-quality-agent
```

Rotate any secrets that were stored in the old nested `.env`.
