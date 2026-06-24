# ADK agent service — backs the dashboard "AI Agent" page.
# Lean image: the real grr/spc/business engine + Google ADK. No Kafka/MLflow stack.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    GOOGLE_GENAI_USE_VERTEXAI=FALSE

WORKDIR /app

# Runtime deps only (the agent layer; not the Kafka/Postgres backend stack).
# litellm backs ADK's Claude/OpenAI providers (the Connections page picks which).
RUN pip install --no-cache-dir \
    "google-adk>=2.0" "litellm>=1.0" "mcp>=1.0" python-dotenv requests \
    numpy pandas scipy \
    "sqlalchemy[asyncio]>=2.0" asyncpg aiosqlite \
    "uvicorn[standard]>=0.30"

# Only the packages the agent actually imports (keeps the image small).
COPY adk_agent/ ./adk_agent/
COPY grr/ ./grr/
COPY spc/ ./spc/
COPY deploy/ ./deploy/

EXPOSE 8090

# Healthy once the agent's REST surface answers.
HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8090/agent/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "adk_agent.web:app", "--host", "0.0.0.0", "--port", "8090"]
