"""Quality AI MCP server — exposes the quality skills over the Model Context Protocol.

Run standalone (stdio):  python -m adk_agent.mcp_server
Lets any MCP client (the Arad ADK agents, Claude Desktop, another team's agent) reuse
the exact same engine and numbers.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from adk_agent import skills

logging.basicConfig(level=logging.INFO)
mcp = FastMCP("arad-quality")


@mcp.tool()
def run_grr_study(measurements: list[dict[str, Any]], method: str = "xbar_r",
                  tolerance: float | None = None) -> dict[str, Any]:
    """Run an AIAG Gage R&R study (xbar_r or anova) and return the AIAG verdict."""
    return skills.run_grr_study(measurements, method=method, tolerance=tolerance)


@mcp.tool()
def run_sample_gage_study(quality: str = "acceptable", n_parts: int = 10, n_operators: int = 3,
                          n_trials: int = 2, method: str = "xbar_r", seed: int = 42) -> dict[str, Any]:
    """Generate a sample gage dataset and run the GR&R study in one call."""
    return skills.run_sample_gage_study(quality=quality, n_parts=n_parts, n_operators=n_operators,
                                        n_trials=n_trials, method=method, seed=seed)


@mcp.tool()
def analyze_spc_series(values: list[float]) -> dict[str, Any]:
    """Run SPC (Individuals/MR chart + 8 Nelson rules) on a measurement series."""
    return skills.analyze_spc_series(values)


@mcp.tool()
def forecast_breach(values: list[float], window: int | None = None) -> dict[str, Any]:
    """Predict whether/when a drifting series will cross a control limit."""
    return skills.forecast_breach(values, window=window)


@mcp.tool()
def calculate_copq(units_per_hour: float, hours_out_of_control: float, baseline_defect_rate: float,
                   out_of_control_defect_rate: float, scrap_cost_per_unit: float,
                   rework_cost_per_unit: float = 0.0, rework_fraction: float = 0.0,
                   escape_rate: float = 0.0, escape_cost_per_unit: float = 0.0,
                   manual_inspection_hours: float = 8.0, events_per_year: float = 0.0) -> dict[str, Any]:
    """Quantify the Cost of Poor Quality (USD) and early-detection savings."""
    return skills.calculate_copq(
        units_per_hour=units_per_hour, hours_out_of_control=hours_out_of_control,
        baseline_defect_rate=baseline_defect_rate, out_of_control_defect_rate=out_of_control_defect_rate,
        scrap_cost_per_unit=scrap_cost_per_unit, rework_cost_per_unit=rework_cost_per_unit,
        rework_fraction=rework_fraction, escape_rate=escape_rate, escape_cost_per_unit=escape_cost_per_unit,
        manual_inspection_hours=manual_inspection_hours, events_per_year=events_per_year)


@mcp.tool()
def generate_sample_study(n_parts: int = 10, n_operators: int = 3, n_trials: int = 2,
                          quality: str = "acceptable", seed: int = 42) -> dict[str, Any]:
    """Generate a reproducible sample GR&R dataset for demos/testing."""
    return skills.generate_sample_study(n_parts=n_parts, n_operators=n_operators,
                                        n_trials=n_trials, quality=quality, seed=seed)


@mcp.tool()
def generate_sample_series(n: int = 40, scenario: str = "shift", seed: int = 7) -> dict[str, Any]:
    """Generate a reproducible sample SPC series for demos/testing."""
    return skills.generate_sample_series(n=n, scenario=scenario, seed=seed)


@mcp.tool()
def dispatch_quality_alert(title: str, message: str, severity: str = "warning",
                           process_name: str | None = None,
                           channels: list[str] | None = None, confirm: bool = False) -> dict[str, Any]:
    """Dispatch a quality alert via the platform's configured channels (preview unless confirm=true)."""
    return skills.dispatch_quality_alert(title=title, message=message, severity=severity,
                                         process_name=process_name, channels=channels, confirm=confirm)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
