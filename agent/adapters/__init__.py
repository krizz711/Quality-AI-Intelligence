"""ML Tool Adapters — pluggable integration layer.

Each ML integration (MLflow, Gemini, future models) is an adapter class
behind a common ``MLToolAdapter`` interface.  Config selects which adapter
loads; new tools just add a new adapter file — no core changes needed.
"""

from agent.adapters.base import MLToolAdapter
from agent.adapters.registry import get_adapter, register_adapter

__all__ = ["MLToolAdapter", "get_adapter", "register_adapter"]
