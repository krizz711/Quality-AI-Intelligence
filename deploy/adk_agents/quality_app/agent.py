"""ADK app entry point for `adk web` / `adk api_server` / `adk deploy`."""

from adk_agent.agents import root_agent

__all__ = ["root_agent"]
