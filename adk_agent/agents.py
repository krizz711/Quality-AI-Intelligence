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

# Empty GEMINI_MODEL in the shared .env must fall back to a real default.
MODEL = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"


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


# `output_key` writes each specialist's final answer into session.state, so its
# findings persist (via the TimescaleDB session store — see adk_agent.state) and the
# coordinator can recall them on later turns instead of recomputing. This is the
# "context engineering / state management" the capstone asks for.
measurement_analyst = Agent(
    name="measurement_analyst",
    model=MODEL,
    description="AIAG Gage R&R / measurement-system analysis specialist.",
    instruction=prompts.MEASUREMENT_ANALYST_INSTRUCTION,
    tools=_tools(skills.run_sample_gage_study, skills.run_grr_study),
    output_key="last_gage_study",
)

process_monitor = Agent(
    name="process_monitor",
    model=MODEL,
    description="SPC control charts, Nelson-rule violation detection, and breach forecasting.",
    instruction=prompts.PROCESS_MONITOR_INSTRUCTION,
    tools=_tools(skills.analyze_spc_series, skills.forecast_breach, skills.generate_sample_series),
    output_key="last_spc_scan",
)

business_analyst = Agent(
    name="business_analyst",
    model=MODEL,
    description="Cost of Poor Quality (COPQ) — converts quality issues into dollars and ROI.",
    instruction=prompts.BUSINESS_ANALYST_INSTRUCTION,
    tools=_tools(skills.calculate_copq),
    output_key="last_copq",
)

action_dispatch = Agent(
    name="action_dispatch",
    model=MODEL,
    description="Dispatches quality alerts to Slack and opens JIRA tickets (human-in-the-loop).",
    instruction=prompts.ACTION_DISPATCH_INSTRUCTION,
    tools=_tools(skills.dispatch_quality_alert),
)

root_agent = Agent(
    name="quality_coordinator",
    model=MODEL,
    description="Coordinates Arad's quality specialists and answers plant-manager questions.",
    instruction=prompts.COORDINATOR_INSTRUCTION,
    sub_agents=[measurement_analyst, process_monitor, business_analyst, action_dispatch],
    before_model_callback=block_unsafe_input,
    before_tool_callback=audit_tool_calls,
)
