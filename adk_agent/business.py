"""Business-impact logic the core app didn't have yet: COPQ + breach forecasting.

`calculate_copq` turns an out-of-control event into dollars (the "Agents for
Business" differentiator). `forecast_breach` projects a drift to a control limit,
reusing this project's real SPC chart math (`spc.control_charts`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from spc.control_charts import individuals_mr_chart

logger = logging.getLogger(__name__)

DEFAULT_MANUAL_INSPECTION_HOURS = 8.0  # once per shift


# ─── Cost of Poor Quality ────────────────────────────────────────────────────


@dataclass
class COPQResult:
    units_affected: int
    defects_added: float
    internal_failure_cost: float
    external_failure_cost: float
    total_copq: float
    cost_if_caught_late: float
    savings_from_early_detection: float
    annualized_copq: float
    summary: str


def calculate_copq(
    *,
    units_per_hour: float,
    hours_out_of_control: float,
    baseline_defect_rate: float,
    out_of_control_defect_rate: float,
    scrap_cost_per_unit: float,
    rework_cost_per_unit: float = 0.0,
    rework_fraction: float = 0.0,
    escape_rate: float = 0.0,
    escape_cost_per_unit: float = 0.0,
    manual_inspection_hours: float = DEFAULT_MANUAL_INSPECTION_HOURS,
    events_per_year: float = 0.0,
) -> COPQResult:
    """Estimate the cost of a process running out of control, in dollars."""
    if not 0 <= baseline_defect_rate <= 1 or not 0 <= out_of_control_defect_rate <= 1:
        raise ValueError("Defect rates must be between 0 and 1.")
    if out_of_control_defect_rate < baseline_defect_rate:
        raise ValueError("Out-of-control defect rate should exceed the baseline rate.")

    def _event_cost(hours: float):
        units = units_per_hour * hours
        defects = units * (out_of_control_defect_rate - baseline_defect_rate)
        internal = (
            defects * (1.0 - rework_fraction) * scrap_cost_per_unit
            + defects * rework_fraction * rework_cost_per_unit
        )
        external = defects * escape_rate * escape_cost_per_unit
        return int(round(units)), defects, internal, external

    units_affected, defects_added, internal, external = _event_cost(hours_out_of_control)
    total = internal + external
    _, _, late_internal, late_external = _event_cost(
        max(manual_inspection_hours, hours_out_of_control)
    )
    cost_if_late = late_internal + late_external
    savings = max(0.0, cost_if_late - total)
    annualized = total * events_per_year

    summary = (
        f"${total:,.0f} lost over {hours_out_of_control:.2f}h out of control "
        f"({defects_added:.0f} excess defects on {units_affected:,} units). "
        f"Early detection saved ${savings:,.0f} vs a {manual_inspection_hours:.0f}h "
        f"manual-inspection cadence."
    )
    if events_per_year:
        summary += f" Annualized exposure: ${annualized:,.0f}/yr."

    return COPQResult(
        units_affected=units_affected,
        defects_added=round(defects_added, 2),
        internal_failure_cost=round(internal, 2),
        external_failure_cost=round(external, 2),
        total_copq=round(total, 2),
        cost_if_caught_late=round(cost_if_late, 2),
        savings_from_early_detection=round(savings, 2),
        annualized_copq=round(annualized, 2),
        summary=summary,
    )


# ─── Breach forecasting ──────────────────────────────────────────────────────


@dataclass
class BreachForecast:
    will_breach: bool
    direction: str
    limit_approached: str | None
    samples_to_breach: int | None
    predicted_breach_value: float | None
    slope_per_sample: float
    r_squared: float
    summary: str


def forecast_breach(
    values: list[float] | np.ndarray,
    *,
    window: int | None = None,
    max_horizon: int = 200,
    min_r_squared: float = 0.30,
) -> BreachForecast:
    """Project the recent trend of an individuals series toward its control limits."""
    arr = np.asarray(values, dtype=float)
    if arr.size < 3:
        raise ValueError("Need at least 3 points to forecast a trend.")

    i_chart, _ = individuals_mr_chart(arr)
    ucl, lcl = i_chart.limits.ucl, i_chart.limits.lcl

    fit_arr = arr[-window:] if window else arr
    x = np.arange(fit_arr.size, dtype=float)
    slope, intercept = np.polyfit(x, fit_arr, 1)
    pred = slope * x + intercept
    ss_res = float(np.sum((fit_arr - pred) ** 2))
    ss_tot = float(np.sum((fit_arr - fit_arr.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    direction = "rising" if slope > 0 else "falling" if slope < 0 else "stable"
    last_x = fit_arr.size - 1
    last_val = float(fit_arr[-1])

    if abs(slope) < 1e-12 or r2 < min_r_squared:
        return BreachForecast(
            False, "stable", None, None, None, round(float(slope), 6), round(r2, 3),
            f"No actionable trend (slope={slope:.4g}, R²={r2:.2f}). Process is stable or noisy.",
        )

    target = ucl if slope > 0 else lcl
    limit_name = "UCL" if slope > 0 else "LCL"
    if (slope > 0 and last_val >= ucl) or (slope < 0 and last_val <= lcl):
        return BreachForecast(
            True, direction, limit_name, 0, last_val, round(float(slope), 6), round(r2, 3),
            f"Series is already at/beyond the {limit_name} ({last_val:.4g}).",
        )

    x_cross = (target - intercept) / slope
    samples_ahead = int(np.ceil(x_cross - last_x))
    if samples_ahead <= 0 or samples_ahead > max_horizon:
        return BreachForecast(
            False, direction, limit_name, None, None, round(float(slope), 6), round(r2, 3),
            f"{direction.capitalize()} trend (R²={r2:.2f}) but no {limit_name} breach "
            f"within {max_horizon} samples.",
        )

    return BreachForecast(
        True, direction, limit_name, samples_ahead, round(float(target), 6),
        round(float(slope), 6), round(r2, 3),
        f"{direction.capitalize()} trend (slope={slope:.4g}/sample, R²={r2:.2f}); projected to "
        f"cross {limit_name} ({target:.4g}) in ~{samples_ahead} samples. Act now to avoid defects.",
    )
