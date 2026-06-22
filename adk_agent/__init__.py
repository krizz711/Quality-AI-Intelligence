"""Arad Quality — Google ADK agent layer.

A multi-agent system built with Google's Agent Development Kit that sits on top of
this project's existing, production-validated quality engine (`grr`, `spc`) and its
alerting integrations. It adds the things the Kaggle capstone scores — ADK
multi-agent orchestration, an MCP server, agent skills, security guardrails — while
reusing the real GR&R/SPC math and Slack/JIRA dispatch.

The layer runs standalone (just numpy/pandas/scipy + google-adk + mcp); it does not
require the full Kafka/Postgres/MLflow stack.
"""

from __future__ import annotations

import os
from pathlib import Path

# Load the project's .env, then a local override (adk_agent/.env, gitignored) for
# standalone runs where the main .env holds placeholders filled by Docker at runtime.
try:
    from dotenv import load_dotenv

    load_dotenv()
    _local = Path(__file__).with_name(".env")
    if _local.exists():
        load_dotenv(_local, override=True)
except Exception:  # pragma: no cover
    pass

# Bridge GEMINI_API_KEY -> GOOGLE_API_KEY so the ADK layer reuses the same key the
# rest of the app already uses.
if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

__version__ = "1.0.0"
