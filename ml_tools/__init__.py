"""
ml_tools — Clean adapter layer for ML/experiment-tracking platforms.

Thin re-export package that surfaces the adapters in agent/adapters/ under
the canonical ``ml_tools`` namespace.  External callers (routes, scripts,
notebooks) import from here; the implementation lives in ``agent/adapters/``.

Quick usage::

    from ml_tools.registry import get_adapter

    adapter = get_adapter()          # uses ML_TOOL_NAME env var (default: mlflow)
    run_id = await adapter.log_experiment(
        "grr_studies", "study-abc",
        params={"method": "xbar_r"},
        metrics={"grr_pct": 12.3, "ndc": 7},
    )

Adding a new ML tool
--------------------
1. Create ``agent/adapters/my_tool_adapter.py`` (implement ``MLToolAdapter``).
2. Register it in ``agent/adapters/registry.py``  ``_register_builtins()``.
3. Set ``ML_TOOL_NAME=my_tool`` in ``.env``.
4. Zero changes needed here or in any route.
"""

from ml_tools.base_adapter import MLToolAdapter
from ml_tools.registry import get_adapter, register_adapter, reset_adapter

__all__ = [
    "MLToolAdapter",
    "get_adapter",
    "register_adapter",
    "reset_adapter",
]
