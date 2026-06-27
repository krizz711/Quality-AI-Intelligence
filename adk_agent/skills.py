"""Agent skills — the shared capability layer.

Each function is a self-contained skill (JSON in, JSON out, no LLM). They wrap this
project's REAL engine (`grr`, `spc`) plus the new business logic and dispatch, and
are exposed two ways: as ADK function tools (`adk_agent.agents`) and as MCP tools
(`adk_agent.mcp_server`). One implementation → identical numbers everywhere.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# Real, production-validated engine from this project:
from grr.calculator import grr_anova, grr_xbar_r
from grr.acceptance import evaluate as evaluate_acceptance
from spc.control_charts import individuals_mr_chart
from spc.nelson_rules import evaluate_all_rules

from adk_agent import backend_client, business, dispatch, sample_data

NELSON_RULE_DESCRIPTIONS = {
    "rule_1": "1 point beyond 3σ (gross shift or measurement error)",
    "rule_2": "9 consecutive points on one side of the center line (sustained mean shift)",
    "rule_3": "6 consecutive points steadily increasing or decreasing (trend / tool wear)",
    "rule_4": "14 consecutive points alternating up and down (over-adjustment)",
    "rule_5": "2 of 3 consecutive points beyond 2σ on one side (emerging shift)",
    "rule_6": "4 of 5 consecutive points beyond 1σ on one side (small sustained shift)",
    "rule_7": "15 consecutive points within 1σ (stratification / under-dispersion)",
    "rule_8": "8 consecutive points beyond 1σ on both sides (mixture)",
}


def run_grr_study(measurements: list[dict[str, Any]], method: str = "xbar_r",
                  tolerance: float | None = None) -> dict[str, Any]:
    """Run an AIAG Gage R&R study (xbar_r or anova) and classify the gage.

    `measurements` rows need ``part``, ``operator`` and ``measurement`` (``value``
    also accepted). Returns variance components, %GR&R, ndc, and an AIAG verdict.
    """
    if not measurements:
        return {"error": "No measurements provided. Use generate_sample_study first."}
    df = pd.DataFrame(measurements)
    if "value" in df.columns and "measurement" not in df.columns:
        df = df.rename(columns={"value": "measurement"})
    missing = {"part", "operator", "measurement"} - set(df.columns)
    if missing:
        return {"error": f"Missing required columns: {sorted(missing)}"}
    try:
        result = (grr_anova if method == "anova" else grr_xbar_r)(df, tolerance=tolerance)
        verdict = evaluate_acceptance(result)
    except ValueError as exc:
        return {"error": str(exc)}
    return {
        "method": method,
        "grr_percent": result.total_grr,
        "repeatability_ev": result.repeatability,
        "reproducibility_av": result.reproducibility,
        "part_variation_pv": result.part_variation,
        "total_variation_tv": result.total_variation,
        "ndc": result.ndc,
        "verdict": verdict.level.value,
        "ndc_adequate": verdict.ndc_adequate,
        "requires_human_review": verdict.requires_human_review,
        "remarks": verdict.remarks,
    }


def run_sample_gage_study(quality: str = "acceptable", n_parts: int = 10, n_operators: int = 3,
                          n_trials: int = 2, method: str = "xbar_r", seed: int = 42) -> dict[str, Any]:
    """Generate a sample gage dataset AND run the GR&R study in one call (demo)."""
    try:
        df = sample_data.generate_grr_study(n_parts=n_parts, n_operators=n_operators,
                                            n_trials=n_trials, quality=quality, seed=seed)
    except ValueError as exc:
        return {"error": str(exc)}
    out = run_grr_study(df.to_dict(orient="records"), method=method)
    out["generated_from"] = {"quality": quality, "n_parts": n_parts,
                             "n_operators": n_operators, "n_trials": n_trials}
    return out


def analyze_spc_series(values: list[float], *, baseline_cl: float | None = None,
                       baseline_sigma: float | None = None, baseline_ucl: float | None = None,
                       baseline_lcl: float | None = None) -> dict[str, Any]:
    """Run SPC (Individuals/MR chart + all 8 Nelson rules) on a measurement series.

    When frozen baseline limits are supplied (``baseline_*``), the Nelson rules and the
    reported limits use them (Phase II monitoring) instead of limits recomputed from this
    window — so a drifting tail can't inflate its own limits and mislabel the points.
    """
    if not values or len(values) < 2:
        return {"error": "Provide at least 2 measurement values."}
    i_chart, _ = individuals_mr_chart(values)
    arr = np.asarray(values, dtype=float)
    cl = baseline_cl if baseline_cl is not None else i_chart.limits.cl
    sigma = baseline_sigma if baseline_sigma is not None else i_chart.limits.sigma
    ucl = baseline_ucl if baseline_ucl is not None else i_chart.limits.ucl
    lcl = baseline_lcl if baseline_lcl is not None else i_chart.limits.lcl
    rule_hits = evaluate_all_rules(arr, cl, sigma)

    violations: list[dict[str, Any]] = []
    for rule, idxs in rule_hits.items():
        for idx in idxs:
            violations.append({"index": int(idx), "value": float(arr[idx]),
                               "rule": rule, "description": NELSON_RULE_DESCRIPTIONS[rule]})
    violations.sort(key=lambda v: v["index"])
    in_control = not violations
    summary = (f"Process in control across {len(arr)} points (no Nelson-rule violations)."
               if in_control else
               f"{len(violations)} special-cause violation(s) across {len(arr)} points; "
               f"rules: {', '.join(sorted({v['rule'] for v in violations}))}.")
    return {
        "in_control": in_control,
        "control_limits": {"ucl": round(ucl, 6), "center_line": round(cl, 6),
                           "lcl": round(lcl, 6), "sigma": round(sigma, 6)},
        "n_points": len(arr),
        "violation_count": len(violations),
        "violations": violations,
        "summary": summary,
    }


def analyze_process(process_name: str) -> dict[str, Any]:
    """Fetch a NAMED process's live measurements from the platform and run SPC on them,
    judged against that process's frozen baseline when one is set.

    Use this to investigate a real, named process or line (e.g. "Torque Press Line 1").
    You do NOT need the user to paste data — this retrieves it for you. Returns the same
    shape as ``analyze_spc_series`` plus ``process_name`` and ``limits_source``.
    """
    try:
        values = backend_client.get_series(process_name)
    except Exception as exc:  # backend unreachable / unknown process
        return {"error": f"Could not fetch measurements for '{process_name}': {exc}"}
    if not values or len(values) < 2:
        return {"error": f"No measurement data on file for '{process_name}' yet."}

    baseline = backend_client.get_baseline(process_name)
    if baseline:
        result = analyze_spc_series(
            values,
            baseline_cl=baseline.get("cl"), baseline_sigma=baseline.get("sigma"),
            baseline_ucl=baseline.get("ucl"), baseline_lcl=baseline.get("lcl"),
        )
        result["limits_source"] = "frozen baseline"
    else:
        result = analyze_spc_series(values)
        result["limits_source"] = "computed from recent window"
    result["process_name"] = process_name
    return result


def forecast_breach(values: list[float], window: int | None = None) -> dict[str, Any]:
    """Predict whether/when a drifting series will cross a control limit."""
    if not values or len(values) < 3:
        return {"error": "Provide at least 3 measurement values."}
    fc = business.forecast_breach(values, window=window)
    return {"will_breach": fc.will_breach, "direction": fc.direction,
            "limit_approached": fc.limit_approached, "samples_to_breach": fc.samples_to_breach,
            "predicted_breach_value": fc.predicted_breach_value, "slope_per_sample": fc.slope_per_sample,
            "r_squared": fc.r_squared, "summary": fc.summary}


def calculate_copq(units_per_hour: float, hours_out_of_control: float, baseline_defect_rate: float,
                   out_of_control_defect_rate: float, scrap_cost_per_unit: float,
                   rework_cost_per_unit: float = 0.0, rework_fraction: float = 0.0,
                   escape_rate: float = 0.0, escape_cost_per_unit: float = 0.0,
                   manual_inspection_hours: float = 8.0, events_per_year: float = 0.0) -> dict[str, Any]:
    """Quantify the Cost of Poor Quality (USD) and early-detection savings."""
    try:
        r = business.calculate_copq(
            units_per_hour=units_per_hour, hours_out_of_control=hours_out_of_control,
            baseline_defect_rate=baseline_defect_rate, out_of_control_defect_rate=out_of_control_defect_rate,
            scrap_cost_per_unit=scrap_cost_per_unit, rework_cost_per_unit=rework_cost_per_unit,
            rework_fraction=rework_fraction, escape_rate=escape_rate, escape_cost_per_unit=escape_cost_per_unit,
            manual_inspection_hours=manual_inspection_hours, events_per_year=events_per_year)
    except ValueError as exc:
        return {"error": str(exc)}
    return {"units_affected": r.units_affected, "excess_defects": r.defects_added,
            "internal_failure_cost": r.internal_failure_cost, "external_failure_cost": r.external_failure_cost,
            "total_copq": r.total_copq, "cost_if_caught_late": r.cost_if_caught_late,
            "savings_from_early_detection": r.savings_from_early_detection,
            "annualized_copq": r.annualized_copq, "summary": r.summary}


def generate_sample_study(n_parts: int = 10, n_operators: int = 3, n_trials: int = 2,
                          quality: str = "acceptable", seed: int = 42) -> dict[str, Any]:
    """Generate a reproducible sample GR&R dataset for demos/testing."""
    try:
        df = sample_data.generate_grr_study(n_parts=n_parts, n_operators=n_operators,
                                            n_trials=n_trials, quality=quality, seed=seed)
    except ValueError as exc:
        return {"error": str(exc)}
    return {"measurements": df.to_dict(orient="records"), "quality": quality}


def generate_sample_series(n: int = 40, scenario: str = "shift", seed: int = 7) -> dict[str, Any]:
    """Generate a reproducible sample SPC series for demos/testing."""
    try:
        values = sample_data.generate_spc_series(n=n, scenario=scenario, seed=seed)
    except ValueError as exc:
        return {"error": str(exc)}
    return {"values": values, "scenario": scenario, "n": n}


# Map the agent's severity vocabulary to the platform's alert severities.
_SEVERITY_MAP = {"info": "low", "warning": "high", "critical": "critical"}


def dispatch_quality_alert(title: str, message: str, severity: str = "warning",
                           process_name: str | None = None,
                           channels: list[str] | None = None, confirm: bool = False) -> dict[str, Any]:
    """Dispatch a quality alert — preferring the platform's configured channels.

    HUMAN-IN-THE-LOOP: with ``confirm=False`` (default) returns a PREVIEW and sends
    nothing. With ``confirm=True`` it routes the alert through the PLATFORM's alert
    pipeline (``/api/v1/alerts/trigger``) so it uses the Slack/email/SMS/JIRA channels
    the operator configured on the **Connections page**. If the platform isn't
    reachable, it falls back to direct Slack/JIRA from the environment (standalone mode).
    """
    channels = channels or ["slack", "jira"]
    plan = {"title": title, "message": message, "severity": severity, "channels": channels,
            "slack_configured": dispatch.slack_configured(), "jira_configured": dispatch.jira_configured()}
    if not confirm:
        return {"status": "preview", "would_send": plan,
                "note": "Nothing sent. Re-call with confirm=true ONLY after a human approves."}

    # Preferred path: route through the platform (Connections-page credentials).
    platform = backend_client.trigger_platform_alert(
        message=f"{title}\n\n{message}",
        severity=_SEVERITY_MAP.get(severity, "high"),
        process_name=process_name or title,
    )
    if platform.get("ok"):
        return {"status": "dispatched", "via": "platform (Connections page)",
                "alert_id": platform.get("alert_id"), "sent_to": ["platform"]}

    # Fallback: direct dispatch from the agent's own env (standalone mode).
    results: dict[str, Any] = {}
    if "slack" in channels:
        results["slack"] = dispatch.send_slack(f"*{title}*\n{message}", severity=severity)
    if "jira" in channels:
        results["jira"] = dispatch.create_jira_issue(summary=title, description=message)
    return {"status": "dispatched", "via": "direct (.env fallback)",
            "sent_to": [k for k, v in results.items() if v.get("ok")], "results": results}


ALL_SKILLS = [run_grr_study, run_sample_gage_study, analyze_process, analyze_spc_series,
              forecast_breach, calculate_copq, generate_sample_study, generate_sample_series,
              dispatch_quality_alert]
