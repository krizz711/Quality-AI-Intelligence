"""The Arad Quality multi-agent system (Google ADK), wired to the real engine.

    quality_coordinator (root)
    ├── measurement_analyst   — GR&R / MSA          (grr.*)
    ├── process_monitor       — SPC + forecasting    (spc.* + business.forecast)
    ├── business_analyst      — Cost of Poor Quality  (business.copq)
    └── action_dispatch       — Slack + JIRA (HITL)   (dispatch.*)

`root_agent` is the ADK entry point. Set ARAD_USE_MCP=1 to route tools through the
MCP server (adk_agent.mcp_server) instead of in-process functions.
"""

from __future__ import annotations

import os
import sys

from google.adk.agents import Agent

from adk_agent import prompts, skills
from adk_agent.guardrails import audit_tool_calls, block_unsafe_input

# Default model for the module-level ``root_agent`` (the ADK web UI, the deploy/
# agent dir, and tests). The dashboard's AI Agent page builds its agent per request
# via ``build_root_agent`` so it can follow the provider chosen on the Connections
# page (Gemini / Claude / OpenAI) — see adk_agent.llm and adk_agent.run.
MODEL = os.environ.get("ADK_GEMINI_MODEL") or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"


def _tools(*funcs):
    """In-process function tools, or MCP toolset when ARAD_USE_MCP=1."""
    if os.environ.get("ARAD_USE_MCP", "").lower() in {"1", "true", "yes"}:
        from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
        from mcp import StdioServerParameters

        return [MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=sys.executable, args=["-m", "adk_agent.mcp_server"]
                ),
                timeout=30.0,
            ),
            tool_filter=[f.__name__ for f in funcs],
        )]
    return list(funcs)


def build_root_agent(model=None) -> Agent:
    """Construct the coordinator + specialists for the given ADK ``model``.

    ``model`` is any value ADK accepts for ``Agent(model=...)`` — a Gemini model-name
    string, or a ``LiteLlm`` instance for Claude / OpenAI (see ``adk_agent.llm``).
    Defaults to :data:`MODEL` (Gemini) so import stays cheap and offline; the AI Agent
    page passes the provider resolved from the Connections page instead.

    Every agent shares the same model so the whole crew runs on the chosen provider.

    ``output_key`` writes each specialist's final answer into ``session.state``, so its
    findings persist (via the TimescaleDB session store — see ``adk_agent.state``) and
    the coordinator can recall them on later turns instead of recomputing. This is the
    "context engineering / state management" the capstone asks for.
    """
    model = model if model is not None else MODEL

    measurement_analyst = Agent(
        name="measurement_analyst",
        model=model,
        description="AIAG Gage R&R / measurement-system analysis specialist.",
        instruction=prompts.MEASUREMENT_ANALYST_INSTRUCTION,
        tools=_tools(skills.run_sample_gage_study, skills.run_grr_study),
        output_key="last_gage_study",
    )

    process_monitor = Agent(
        name="process_monitor",
        model=model,
        description="SPC control charts, Nelson-rule violation detection, and breach forecasting.",
        instruction=prompts.PROCESS_MONITOR_INSTRUCTION,
        tools=_tools(skills.analyze_spc_series, skills.forecast_breach, skills.generate_sample_series),
        output_key="last_spc_scan",
    )

    business_analyst = Agent(
        name="business_analyst",
        model=model,
        description="Cost of Poor Quality (COPQ) — converts quality issues into dollars and ROI.",
        instruction=prompts.BUSINESS_ANALYST_INSTRUCTION,
        tools=_tools(skills.calculate_copq),
        output_key="last_copq",
    )

    action_dispatch = Agent(
        name="action_dispatch",
        model=model,
        description="Dispatches quality alerts to Slack and opens JIRA tickets (human-in-the-loop).",
        instruction=prompts.ACTION_DISPATCH_INSTRUCTION,
        tools=_tools(skills.dispatch_quality_alert),
    )

    return Agent(
        name="quality_coordinator",
        model=model,
        description="Coordinates Arad's quality specialists and answers plant-manager questions.",
        instruction=prompts.COORDINATOR_INSTRUCTION,
        sub_agents=[measurement_analyst, process_monitor, business_analyst, action_dispatch],
        before_model_callback=block_unsafe_input,
        before_tool_callback=audit_tool_calls,
    )


# Module-level default (Gemini) for the ADK web UI, the deploy/ agent dir, and tests.
root_agent = build_root_agent()
