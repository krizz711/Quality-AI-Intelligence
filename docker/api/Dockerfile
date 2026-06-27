FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    TMPDIR=/var/tmp/pip-tmp \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl librdkafka1 netcat-openbsd && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/tmp/pip-tmp

COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
COPY agent ./agent
COPY api ./api
COPY backend ./backend
COPY core ./core
COPY db ./db
COPY grr ./grr
COPY schemas ./schemas
COPY spc ./spc

RUN python -m pip install --upgrade pip setuptools wheel && python -m pip install --retries 8 --timeout 120 .

RUN sed -i 's/\r$//' ./scripts/ensure_db_ready.sh ./scripts/docker_api_entrypoint.sh 2>/dev/null || true \
    && chmod +x ./scripts/ensure_db_ready.sh ./scripts/docker_api_entrypoint.sh ./scripts/build_database_url.py

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
