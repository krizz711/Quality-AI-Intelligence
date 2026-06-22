"""Deployable FastAPI app (ADK web UI + REST API) for the ADK agent layer.

    uvicorn adk_agent.web:app --port 8080      # open http://localhost:8080

Importing this module triggers `adk_agent/__init__.py`, which loads the .env and
bridges the Gemini key. $PORT is honoured for Cloud Run.
"""

from __future__ import annotations

import os
from pathlib import Path

import adk_agent  # noqa: F401  (ensures .env / key bridge runs)
from google.adk.cli.fast_api import get_fast_api_app

from adk_agent import state

AGENTS_DIR = os.environ.get(
    "ARAD_AGENTS_DIR",
    str(Path(__file__).resolve().parent.parent / "deploy" / "adk_agents"),
)

# Persist ADK web/REST sessions in TimescaleDB (falls back to the SQLite file, then
# in-memory) so conversation + state survive restarts. See adk_agent.state.
SESSION_URI = state.resolve_session_db_uri_sync()

app = get_fast_api_app(
    agents_dir=AGENTS_DIR, web=True, allow_origins=["*"],
    session_service_uri=SESSION_URI,
)

# Custom /agent/* endpoints that power the dashboard's live "AI Agent" page.
from adk_agent.dashboard_api import register as _register_dashboard_api  # noqa: E402

_register_dashboard_api(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
