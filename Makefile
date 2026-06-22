.PHONY: install test test-docker test-integration lint run-api prod-check \
        demo demo-timescale adk-install adk-test

# Use the lean ADK venv's Python if present, else fall back to plain `python`.
ifeq ($(OS),Windows_NT)
ADK_PY ?= $(wildcard .venv-adk/Scripts/python.exe)
else
ADK_PY ?= $(wildcard .venv-adk/bin/python)
endif
ifeq ($(ADK_PY),)
ADK_PY := python
endif

# ─── Install all dependencies via Poetry ─────────────────────────────────────
install:
	poetry install

# ─── Run the test suite ──────────────────────────────────────────────────────
test:
	poetry run pytest -v

# ─── Run the suite inside the running Docker stack (no host Python needed) ────
# DATABASE_URL is built from the container's own credentials and targets the
# in-network DB host (timescaledb), avoiding the localhost connection error.
test-docker:
	docker compose cp ./tests api:/app/tests
	docker compose exec api pip install -q pytest pytest-asyncio pytest-cov confluent-kafka
	docker compose exec api sh -c 'DATABASE_URL="postgresql+asyncpg://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@timescaledb:5432/$${POSTGRES_DB}" pytest -m "not integration"'

test-integration:
	poetry run pytest -m integration -v

# ─── Lint & format with Ruff ─────────────────────────────────────────────────
lint:
	poetry run ruff check .
	poetry run ruff format --check .

# ─── Start the FastAPI dev server ────────────────────────────────────────────
run-api:
	poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

prod-check:
	poetry run pytest -m "not integration"
	cd dashboard && npm run build

# ─── Kaggle ADK capstone: one-command demo + tests (lean venv, no API key) ────
# `make demo` runs the full agent loop offline: live drift -> SPC detection ->
# dollar impact (COPQ) -> drafted action -> human-in-the-loop gate, and persists
# the run to the session store. Add --send by running the module directly.
demo:
	$(ADK_PY) -m adk_agent.demo

# Same demo, but with TimescaleDB up so agent state is persisted there (not SQLite).
# Then prints the persisted session so you can see the state landed in TimescaleDB.
demo-timescale:
	docker compose up -d timescaledb
	$(ADK_PY) -m adk_agent.demo
	$(ADK_PY) -m adk_agent.state

# Lean install for the ADK layer only (no Kafka/Postgres stack needed).
adk-install:
	$(ADK_PY) -m pip install google-adk mcp python-dotenv requests numpy pandas scipy \
		pytest pytest-asyncio matplotlib nbformat "sqlalchemy[asyncio]>=2.0" asyncpg aiosqlite

adk-test:
	$(ADK_PY) -m pytest adk_agent/tests -q
