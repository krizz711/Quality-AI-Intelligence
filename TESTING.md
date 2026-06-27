# Quality AI Agent — Testing Strategy

## Overview

This document describes the test pyramid, how to run each layer, CI/CD gates, and go-live acceptance criteria.

---

## Test Pyramid

```
       /\
      /E2E\          tests/e2e/          (Playwright — requires live stack)
     /------\
    /Contract\       tests/contract/     (schemathesis — no DB required)
   /----------\
  /Performance \     tests/performance/  (p99 latency + GRR runtime)
 /--------------\
/  Integration   \   tests/integration/  (Kafka + TimescaleDB — Docker required)
/------------------\
      Unit           tests/unit/ + tests/test_*.py  (pure Python — no Docker)
```

---

## Running Tests

### Quick start — run the suite against your running stack (Docker only)

The runtime image is intentionally lean (it ships **without** `tests/` or `pytest`), so
copy the tests in, add the test tools, and point pytest at the database. **Inside the
container the DB host is `timescaledb:5432`, not `localhost`**, and a fresh `pytest`
shell does not inherit the app's `DATABASE_URL` — so it is passed explicitly below,
built from the container's own credentials (no password needed):

```bash
docker compose cp ./tests api:/app/tests
docker compose exec api pip install -q pytest pytest-asyncio pytest-cov confluent-kafka
docker compose exec api sh -c 'DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@timescaledb:5432/${POSTGRES_DB}" pytest tests/test_monitor.py -v'
```

> ⚠️ Omitting that `DATABASE_URL` produces `OSError: ... Connect call failed ('127.0.0.1', 5432)` —
> there is no database at `localhost` *inside* the container. The whole sequence is wrapped
> in **`make test-docker`** for convenience.

To run on the **host** instead (Python 3.12 + Poetry; infra up; `.env` configured —
its `DATABASE_URL` already points at `localhost:5433`):

```bash
poetry install
make test            # or: poetry run pytest -m "not integration"
```

### Unit Tests (no Docker required)

```bash
# Install dev dependencies
pip install ".[dev]"   # or: pip install pytest pytest-asyncio pytest-cov httpx fakeredis jinja2

# Run all unit tests with coverage
pytest tests/ \
  --ignore=tests/integration \
  --ignore=tests/contract \
  --ignore=tests/e2e \
  --ignore=tests/performance \
  -v --tb=short \
  --cov=grr --cov=spc --cov=agent --cov=api --cov=core \
  --cov-report=term-missing

# Run only the statistical core (grr/ + spc/) — must be 100% covered
pytest tests/test_grr.py tests/test_spc.py \
  --cov=grr --cov=spc \
  --cov-fail-under=100
```

### Integration Tests (Docker required)

```bash
# Start dependencies
docker compose up -d timescaledb kafka redis

# Wait for health
until docker compose ps | grep timescaledb | grep -q healthy; do sleep 3; done

# Set the test DB URL
set TEST_DATABASE_URL=postgresql://arad:arad_pass@localhost:5432/arad_quality  # Windows
export TEST_DATABASE_URL=postgresql://arad:arad_pass@localhost:5432/arad_quality  # Linux/Mac

# Run migrations
alembic upgrade head

# Run integration tests
pytest tests/integration/ -v -s --timeout=60
```

### Contract Tests

```bash
pip install schemathesis

pytest tests/contract/ -v --timeout=60
```

### Performance Tests

```bash
pytest tests/performance/ -v -s
# Expected output: timing numbers for GRR runtime and API latency
```

### E2E Tests (requires full stack)

```bash
# Install Playwright
npm install --prefix tests/e2e @playwright/test
npx --prefix tests/e2e playwright install chromium

# Start the full stack
docker compose up --build -d
until curl -sf http://localhost:8000/health/ready | grep -q ready; do sleep 5; done

# Run API-level E2E tests (fast, no browser)
cd tests/e2e
npx playwright test fixture_workflow.spec.ts

# Run UI E2E tests (requires browser)
RUN_UI_TESTS=1 npx playwright test fixture_workflow.spec.ts
```

---

## Test IDs and Coverage

| Test ID | Layer | File | Description |
|---------|-------|------|-------------|
| T-U1 | Unit | `tests/test_grr.py` | GRR Xbar-R vs AIAG reference tables |
| T-U2 | Unit | `tests/test_spc.py` | SPC control charts vs AIAG constants |
| T-U3 | Unit | `tests/unit/test_alert_generation.py` | Alert generation with mock violation fixtures |
| T-U4 | Unit | `tests/unit/test_audit_logging.py` | Audit log entry written on trigger action |
| T-U5 | Unit | `tests/unit/test_llm_prompt_template.py` | LLM prompt variable substitution |
| T-I1 | Integration | `tests/integration/test_burst_latency.py` | Kafka consumer → TimescaleDB within 5s |
| T-I2 | Integration | `tests/integration/test_alert_manager.py` | Slack/Email/Jira dispatch via mock servers |
| T-C1 | Contract | `tests/contract/test_openapi_contract.py` | All /api/v1/ routes against OpenAPI spec |
| T-E1 | E2E | `tests/e2e/fixture_workflow.spec.ts` | New fixture workflow via API |
| T-E2 | E2E | `tests/e2e/fixture_workflow.spec.ts` | Dashboard loads and shows charts |
| T-E4 | E2E | `tests/e2e/fixture_workflow.spec.ts` | CSV upload → GR&R results |
| T-P1 | Performance | `tests/performance/test_grr_performance.py` | API p99 latency ≤ 1s |
| T-P2 | Performance | `tests/performance/test_grr_performance.py` | GRR calculation runtime ≤ 5s |
| T-S1 | Unit | `tests/unit/test_security.py` | 401/403 on unauthorized access logged to audit |
| T-S3 | Unit | `tests/unit/test_security.py` | No secrets visible in any container log |

---

## CI/CD Pipeline

The GitHub Actions CI is defined in [.github/workflows/ci.yml](.github/workflows/ci.yml).

```
Push/PR
  │
  ├─► lint         ruff check + mypy type hints
  │
  ├─► unit         pytest --cov (no Docker)  ← blocks integration + docker
  │      └─ coverage gate: grr/ + spc/ must be 100%
  │
  ├─► dashboard    npm ci + npm run build
  │
  ├─► integration  Kafka + TimescaleDB services in GHA  ← main/PR only
  │
  ├─► contract     schemathesis against FastAPI app     ← main/PR only
  │
  └─► docker       build + push to GHCR  ← main branch only, after unit+dashboard pass
```

### Secrets needed in GitHub

| Secret | Purpose |
|--------|---------|
| `API_AUTH_KEY` | Runtime auth key for API container |
| `POSTGRES_PASSWORD` | DB password (not currently used in CI — uses hardcoded test creds) |
| `SLACK_WEBHOOK_URL` | Optional — for alert integration tests |
| `GEMINI_API_KEY` | Optional — AI routes fall back gracefully when absent |

---

## Coverage Requirements

| Module | Required | Rationale |
|--------|----------|-----------|
| `grr/` | **100%** | Statistical calculations — must be exact |
| `spc/` | **100%** | Statistical calculations — must be exact |
| `agent/alert_engine.py` | ≥ 90% | Critical alert dispatch path |
| `api/main.py` | ≥ 80% | Core API handler logic |
| `core/` | ≥ 80% | Config and logging |

---

## Go-Live Acceptance Criteria

All of the following must be green before production deployment:

- [ ] All unit tests pass with 100% coverage on `grr/` and `spc/`
- [ ] All integration tests green in CI
- [ ] T-P2: GR&R runtime ≤ 5s (verified by `tests/performance/`)
- [ ] T-P1: API p99 latency ≤ 1s (verified by `tests/performance/`)
- [ ] T-E1: Fixture GR&R workflow completes successfully
- [ ] T-S3: No secrets visible in container logs (verified by `tests/unit/test_security.py`)
- [ ] RUNBOOK.md reviewed and tested by a team member who did not write it
- [ ] Production deployment completes via CI/CD with zero manual steps
- [ ] Grafana dashboard shows green on all panels after 15 minutes under load
- [ ] `/health/ready` returns `{"status":"ready"}` with all checks passing

---

## Test Isolation Guidelines

1. **Unit tests** must import only from `grr/`, `spc/`, `core/`, `agent/`, or `api/` — never connect to external services.
2. **Integration tests** use a dedicated `TEST_DATABASE_URL` and roll back transactions after each test via `db_conn` fixture.
3. **E2E tests** use unique part numbers / study IDs per run to avoid state collisions.
4. **Performance tests** do not assert exact timing in CI (machines vary) — they document the actual numbers and gate on SLA bounds only.

---

## Adding New Tests

1. Place statistical calculation tests in `tests/test_grr.py` or `tests/test_spc.py`.
2. Place service-level unit tests under `tests/unit/`.
3. Place tests that need a live DB under `tests/integration/` and mark with `@pytest.mark.integration`.
4. New API endpoints require a contract test entry in `tests/contract/test_openapi_contract.py`.
5. New alert channels require a mock-server test in `tests/integration/test_alert_manager.py`.
