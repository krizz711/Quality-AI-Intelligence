"""
ml_tools.registry — adapter registry re-export.

Delegates to agent/adapters/registry so all registration state lives
in one place.  Import from here in application code; import from
agent/adapters/registry only in adapter implementations.

Environment
-----------
ML_TOOL_NAME (or the legacy ML_TOOL alias)
    Selects which adapter is loaded.  Defaults to ``mlflow``.
    Supported built-ins: ``mlflow``, ``gemini``.
"""

import os as _os

# Support both ML_TOOL_NAME and the legacy ML_TOOL env var
if not _os.environ.get("ML_TOOL_NAME") and _os.environ.get("ML_TOOL"):
    _os.environ["ML_TOOL_NAME"] = _os.environ["ML_TOOL"]

from agent.adapters.registry import (
    get_adapter,
    register_adapter,
    reset_adapter,
)

__all__ = ["get_adapter", "register_adapter", "reset_adapter"]
