"""Abstract base class for ML tool adapters.

All adapters implement three methods so that orchestrator code never
couples to a specific ML platform:

    log_experiment()   — persist study params, metrics, and artifacts
    register_model()   — push a model to the registry (optional)
    get_prediction()   — run inference from a registered model (optional)

Adding a new ML tool = create ``adapters/my_tool_adapter.py``, subclass
``MLToolAdapter``, and add to the config registry.  Done.
"""

from __future__ import annotations

import abc
from typing import Any


class MLToolAdapter(abc.ABC):
    """Common interface every ML tool adapter must implement."""

    @abc.abstractmethod
    async def log_experiment(
        self,
        experiment_name: str,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        artifacts: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> str:
        """Log an experiment run.  Returns a run ID / reference string."""
        ...

    @abc.abstractmethod
    async def register_model(
        self,
        model_name: str,
        model_artifact: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Register a model in the platform's registry.  Returns version ID."""
        ...

    @abc.abstractmethod
    async def get_prediction(
        self,
        model_name: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run inference using a registered model.  Returns prediction dict."""
        ...
