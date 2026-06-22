"""Adapter registry — selects the active ML tool adapter based on config.

``ML_TOOL_NAME`` env var selects which adapter loads.  To add a new tool:

    1. Create ``adapters/my_tool_adapter.py`` with a class implementing
       ``MLToolAdapter``.
    2. Register it below in ``_BUILTIN_ADAPTERS``.
    3. Set ``ML_TOOL_NAME=my_tool`` in your ``.env``.

That's it — no core changes needed.
"""

from __future__ import annotations

import logging
import os
from typing import Callable

from agent.adapters.base import MLToolAdapter

logger = logging.getLogger(__name__)

# Registry: name -> factory callable
_registry: dict[str, Callable[[], MLToolAdapter]] = {}

# Singleton cache
_active_adapter: MLToolAdapter | None = None


def register_adapter(name: str, factory: Callable[[], MLToolAdapter]) -> None:
    """Register a new adapter factory under *name*."""
    _registry[name.lower()] = factory
    logger.debug("Registered ML adapter: %s", name)


def _register_builtins() -> None:
    """Lazy-register built-in adapters (avoids import cost at module load)."""
    if "mlflow" not in _registry:
        def _mlflow_factory() -> MLToolAdapter:
            from agent.adapters.mlflow_adapter import MLflowAdapter
            tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
            return MLflowAdapter(tracking_uri=tracking_uri)

        register_adapter("mlflow", _mlflow_factory)

    if "gemini" not in _registry:
        def _gemini_factory() -> MLToolAdapter:
            from agent.adapters.gemini_adapter import GeminiAdapter
            return GeminiAdapter()

        register_adapter("gemini", _gemini_factory)


def get_adapter(name: str | None = None) -> MLToolAdapter:
    """Return the configured adapter (singleton).

    Parameters
    ----------
    name : str | None
        Adapter name.  Falls back to ``ML_TOOL_NAME`` env var, then
        defaults to ``"mlflow"``.
    """
    global _active_adapter

    resolved = (name or os.environ.get("ML_TOOL_NAME", "mlflow")).lower()
    if _active_adapter is not None:
        return _active_adapter

    _register_builtins()

    factory = _registry.get(resolved)
    if factory is None:
        raise ValueError(
            f"Unknown ML adapter '{resolved}'.  "
            f"Available: {sorted(_registry.keys())}"
        )

    _active_adapter = factory()
    logger.info("Active ML adapter: %s (%s)", resolved, type(_active_adapter).__name__)
    return _active_adapter


def reset_adapter() -> None:
    """Reset the cached singleton (useful in tests)."""
    global _active_adapter
    _active_adapter = None
