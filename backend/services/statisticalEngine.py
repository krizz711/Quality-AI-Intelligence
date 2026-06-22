"""Statistical engine for GR&R and SPC calculations.

This module implements the quality calculations in a form that can be used by
the backend service layer and reused by the rest of the application.
"""

from __future__ import annotations

import math
import warnings
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

try:
    from scipy import stats
except Exception:  # pragma: no cover - scipy is available in normal app installs
    stats = None


warnings.warn(
    "backend.services.statisticalEngine is deprecated — use the canonical 'spc' modules "
    "(spc.control_charts, spc.nelson_rules) instead. This shim will be removed in a future "
    "release.",
    DeprecationWarning,
)


_D2: dict[int, float] = {
    2: 1.128,
    3: 1.693,
    4: 2.059,
    5: 2.326,
    6: 2.534,
    7: 2.704,
    8: 2.847,
    9: 2.970,
    10: 3.078,
}

_A2: dict[int, float] = {
    2: 1.880,
    3: 1.023,
    4: 0.729,
    5: 0.577,
    6: 0.483,
    7: 0.419,
    8: 0.373,
    9: 0.337,
    10: 0.308,
}

_D3: dict[int, float] = {
    2: 0.000,
    3: 0.000,
    4: 0.000,
    5: 0.000,
    6: 0.000,
    7: 0.076,
    8: 0.136,
    9: 0.184,
    10: 0.223,
}

_D4: dict[int, float] = {
    2: 3.267,
    3: 2.574,
    4: 2.282,
    5: 2.114,
    6: 2.004,
    7: 1.924,
    8: 1.864,
    9: 1.816,
    10: 1.777,
}


@dataclass(frozen=True)
class _CellKey:
    operator: str
    part: int


def _safe_float(value: Any) -> float:
    return float(value) if value is not None else float("nan")


def _sample_std(values: np.ndarray) -> float:
    """Sample standard deviation with ddof=1, returning 0 for undersized samples."""

    if values.size < 2:
        return 0.0
    return float(np.std(values, ddof=1))


def _validate_subgroup_size(subgroup_size: int) -> None:
    if subgroup_size not in _A2:
        raise ValueError("subgroupSize must be between 2 and 10")


def calculateGRR(
    measurements: list[dict[str, Any]],
    tolerance: float | None = None,
) -> dict[str, Any]:
    """Calculate a full ANOVA GR&R study from long-format measurements.

    Parameters
    ----------
    measurements:
        List of measurement records containing operator, part, trial, and value.
    tolerance:
        Optional engineering tolerance. When provided, %GRR is based on tolerance
        instead of study variation.
    """

    if not measurements:
        raise ValueError("measurements must not be empty")

    normalized: list[dict[str, Any]] = []
    operator_names: list[str] = []
    part_numbers: list[int] = []
    trial_numbers: list[int] = []

    for item in measurements:
        operator = str(item["operator"])
        part = int(item["part"])
        trial = int(item["trial"])
        value = float(item["value"])

        normalized.append(
            {"operator": operator, "part": part, "trial": trial, "value": value}
        )
        if operator not in operator_names:
            operator_names.append(operator)
        if part not in part_numbers:
            part_numbers.append(part)
        if trial not in trial_numbers:
            trial_numbers.append(trial)

    operator_names.sort()
    part_numbers.sort()
    trial_numbers.sort()

    n_operators = len(operator_names)
    n_parts = len(part_numbers)
    n_trials = len(trial_numbers)

    if n_operators < 2 or n_parts < 2 or n_trials < 2:
        raise ValueError("GR&R requires at least 2 operators, 2 parts, and 2 trials")

    matrix: dict[str, dict[int, dict[int, float]]] = {
        operator: {part: {} for part in part_numbers} for operator in operator_names
    }

    seen: set[_CellKey] = set()
    for item in normalized:
        key = _CellKey(item["operator"], item["part"])
        cell = matrix[key.operator][key.part]
        if item["trial"] in cell or key in seen and item["trial"] in cell:
            raise ValueError("Duplicate measurement for the same operator, part, and trial")
        cell[item["trial"]] = item["value"]
        seen.add(key)

    for operator in operator_names:
        for part in part_numbers:
            trials = matrix[operator][part]
            if set(trials) != set(trial_numbers):
                raise ValueError("Each operator-part combination must contain all trial values")

    values = np.array([item["value"] for item in normalized], dtype=float)
    grand_mean = float(np.mean(values))

    cell_means: dict[str, dict[int, float]] = {}
    cell_ranges: dict[str, dict[int, float]] = {}
    for operator in operator_names:
        cell_means[operator] = {}
        cell_ranges[operator] = {}
        for part in part_numbers:
            cell_values = np.array([matrix[operator][part][trial] for trial in trial_numbers], dtype=float)
            cell_means[operator][part] = float(np.mean(cell_values))
            cell_ranges[operator][part] = float(np.max(cell_values) - np.min(cell_values))

    part_means = {
        part: float(
            np.mean(
                [matrix[operator][part][trial] for operator in operator_names for trial in trial_numbers]
            )
        )
        for part in part_numbers
    }
    operator_means = {
        operator: float(
            np.mean(
                [matrix[operator][part][trial] for part in part_numbers for trial in trial_numbers]
            )
        )
        for operator in operator_names
    }

    r_bar = float(np.mean([cell_ranges[operator][part] for operator in operator_names for part in part_numbers]))
    xdiff = float(max(operator_means.values()) - min(operator_means.values()))

    # ANOVA sums of squares using the balanced crossed design.
    ss_total = float(np.sum((values - grand_mean) ** 2))
    ss_parts = float(
        n_operators * n_trials * sum((part_means[part] - grand_mean) ** 2 for part in part_numbers)
    )
    ss_operators = float(
        n_parts * n_trials * sum((operator_means[operator] - grand_mean) ** 2 for operator in operator_names)
    )
    ss_interaction = float(
        n_trials
        * sum(
            (
                cell_means[operator][part]
                - part_means[part]
                - operator_means[operator]
                + grand_mean
            )
            ** 2
            for operator in operator_names
            for part in part_numbers
        )
    )
    ss_error = ss_total - ss_parts - ss_operators - ss_interaction

    df_parts = n_parts - 1
    df_operators = n_operators - 1
    df_interaction = (n_parts - 1) * (n_operators - 1)
    df_error = n_parts * n_operators * (n_trials - 1)

    if df_parts <= 0 or df_operators <= 0 or df_interaction <= 0 or df_error <= 0:
        raise ValueError("Not enough degrees of freedom for ANOVA GR&R")

    ms_parts = ss_parts / df_parts
    ms_operators = ss_operators / df_operators
    ms_interaction = ss_interaction / df_interaction
    ms_error = ss_error / df_error

    # Variance components. Negative estimates can occur from sampling noise; in MSA
    # they are truncated at zero to avoid non-physical variance components.
    variance_repeatability = max(0.0, ms_error)
    variance_reproducibility = max(0.0, (ms_operators - ms_interaction) / (n_parts * n_trials))
    variance_parts = max(0.0, (ms_parts - ms_interaction) / (n_operators * n_trials))
    variance_grr = variance_repeatability + variance_reproducibility
    variance_total = variance_grr + variance_parts

    grr_sigma = math.sqrt(variance_grr)
    total_sigma = math.sqrt(variance_total)
    repeatability_sigma = math.sqrt(variance_repeatability)
    reproducibility_sigma = math.sqrt(variance_reproducibility)
    part_sigma = math.sqrt(variance_parts)

    if tolerance is not None:
        grr_percent = 100.0 * 5.15 * grr_sigma / float(tolerance)
    else:
        grr_percent = 100.0 * grr_sigma / (5.15 * total_sigma) if total_sigma > 0 else 0.0

    repeatability_percent = 100.0 * repeatability_sigma / grr_sigma if grr_sigma > 0 else 0.0
    reproducibility_percent = 100.0 * reproducibility_sigma / grr_sigma if grr_sigma > 0 else 0.0
    ndc = int(math.floor(1.41 * math.sqrt(variance_parts / variance_grr))) if variance_grr > 0 else 0

    if grr_percent < 10.0:
        verdict = "excellent"
    elif grr_percent <= 30.0:
        verdict = "acceptable"
    else:
        verdict = "unacceptable"

    anova_table = {
        "parts": {
            "ss": ss_parts,
            "df": df_parts,
            "ms": ms_parts,
            "f": ms_parts / ms_interaction if ms_interaction > 0 else None,
        },
        "operators": {
            "ss": ss_operators,
            "df": df_operators,
            "ms": ms_operators,
            "f": ms_operators / ms_interaction if ms_interaction > 0 else None,
        },
        "interaction": {
            "ss": ss_interaction,
            "df": df_interaction,
            "ms": ms_interaction,
            "f": ms_interaction / ms_error if ms_error > 0 else None,
        },
        "error": {
            "ss": ss_error,
            "df": df_error,
            "ms": ms_error,
        },
        "total": {
            "ss": ss_total,
            "df": len(values) - 1,
        },
    }

    if stats is not None:
        anova_table["interaction"]["p"] = float(
            stats.f.sf(anova_table["interaction"]["f"], df_interaction, df_error)
        ) if anova_table["interaction"]["f"] is not None else None
    else:
        anova_table["interaction"]["p"] = None

    return {
        "method": "anova",
        "grand_mean": grand_mean,
        "part_means": part_means,
        "operator_means": operator_means,
        "range_within": r_bar,
        "range_between_operators": xdiff,
        "anova_table": anova_table,
        "variance_components": {
            "repeatability": variance_repeatability,
            "reproducibility": variance_reproducibility,
            "grr": variance_grr,
            "parts": variance_parts,
            "total": variance_total,
        },
        "percentages": {
            "grr": grr_percent,
            "repeatability": repeatability_percent,
            "reproducibility": reproducibility_percent,
        },
        "sigma": {
            "repeatability": repeatability_sigma,
            "reproducibility": reproducibility_sigma,
            "grr": grr_sigma,
            "parts": part_sigma,
            "total": total_sigma,
        },
        "ndc": ndc,
        "verdict": verdict,
        "inputs": {
            "n_operators": n_operators,
            "n_parts": n_parts,
            "n_trials": n_trials,
            "tolerance": tolerance,
        },
    }


def calculateXbarR(data: list[list[float]], subgroupSize: int) -> dict[str, float]:
    """Calculate X-bar and R chart control limits for subgrouped data."""

    _validate_subgroup_size(subgroupSize)

    if not data:
        raise ValueError("data must not be empty")

    subgroups = [np.asarray(subgroup, dtype=float) for subgroup in data]
    for subgroup in subgroups:
        if subgroup.size != subgroupSize:
            raise ValueError("Each subgroup must match subgroupSize")
        if subgroup.size < 2:
            raise ValueError("Each subgroup must contain at least 2 values")

    subgroup_means = np.array([float(np.mean(subgroup)) for subgroup in subgroups], dtype=float)
    subgroup_ranges = np.array([float(np.max(subgroup) - np.min(subgroup)) for subgroup in subgroups], dtype=float)

    xbar_centerline = float(np.mean(subgroup_means))
    r_centerline = float(np.mean(subgroup_ranges))

    a2 = _A2[subgroupSize]
    d2 = _D2[subgroupSize]
    d3 = _D3[subgroupSize]
    d4 = _D4[subgroupSize]

    # Estimate process sigma from the average range, then derive X-bar limits.
    sigma_within = r_centerline / d2 if d2 > 0 else 0.0
    xbar_ucl = xbar_centerline + a2 * r_centerline
    xbar_lcl = xbar_centerline - a2 * r_centerline

    # R chart limits use the d3/d4 constants directly.
    r_ucl = d4 * r_centerline
    r_lcl = d3 * r_centerline

    return {
        "xbar_ucl": xbar_ucl,
        "xbar_lcl": xbar_lcl,
        "xbar_centerline": xbar_centerline,
        "r_ucl": r_ucl,
        "r_lcl": r_lcl,
        "r_centerline": r_centerline,
        "sigma": sigma_within,
        "constants": {
            "d2": d2,
            "d3": d3,
            "a2": a2,
            "d4": d4,
        },
    }


def detectWesternElectricViolations(
    data: list[float],
    ucl: float,
    lcl: float,
    centerline: float,
    sigma: float,
) -> list[dict[str, Any]]:
    """Detect the five Western Electric rules requested by the user.

    The pointIndexes values use zero-based indexes into the input series.
    """

    values = np.asarray(data, dtype=float)
    if values.size == 0:
        return []

    violations: list[dict[str, Any]] = []

    def add_violation(rule: str, description: str, indexes: list[int]) -> None:
        violations.append({"rule": rule, "description": description, "pointIndexes": indexes})

    # Rule 1: 1 point beyond 3 sigma from the centerline.
    if sigma > 0:
        for index, value in enumerate(values):
            if abs(value - centerline) > 3.0 * sigma or value > ucl or value < lcl:
                add_violation("Rule 1", "Out of control", [index])

    # Rule 2: 2 of 3 consecutive points beyond 2 sigma on the same side.
    if sigma > 0:
        for end in range(2, len(values)):
            window_indexes = list(range(end - 2, end + 1))
            window = values[window_indexes]
            above = [idx for idx, value in zip(window_indexes, window, strict=True) if value > centerline + 2.0 * sigma]
            below = [idx for idx, value in zip(window_indexes, window, strict=True) if value < centerline - 2.0 * sigma]
            if len(above) >= 2 or len(below) >= 2:
                add_violation("Rule 2", "Warning", window_indexes)

    # Rule 3: 4 of 5 consecutive points beyond 1 sigma on the same side.
    if sigma > 0:
        for end in range(4, len(values)):
            window_indexes = list(range(end - 4, end + 1))
            window = values[window_indexes]
            above = [idx for idx, value in zip(window_indexes, window, strict=True) if value > centerline + sigma]
            below = [idx for idx, value in zip(window_indexes, window, strict=True) if value < centerline - sigma]
            if len(above) >= 4 or len(below) >= 4:
                add_violation("Rule 3", "Trend warning", window_indexes)

    # Rule 4: 8 consecutive points on the same side of the centerline.
    for end in range(7, len(values)):
        window_indexes = list(range(end - 7, end + 1))
        window = values[window_indexes]
        if np.all(window > centerline) or np.all(window < centerline):
            add_violation("Rule 4", "Run", window_indexes)

    # Rule 5: 6 consecutive points trending up or down.
    for end in range(5, len(values)):
        window_indexes = list(range(end - 5, end + 1))
        window = values[window_indexes]
        diffs = np.diff(window)
        if np.all(diffs > 0) or np.all(diffs < 0):
            add_violation("Rule 5", "Trend", window_indexes)

    return violations


def calculateProcessCapability(
    data: list[float],
    usl: float,
    lsl: float,
) -> dict[str, float | str]:
    """Calculate Cp and Cpk using the sample standard deviation of the data."""

    values = np.asarray(data, dtype=float)
    if values.size < 2:
        raise ValueError("data must contain at least 2 points")

    mean = float(np.mean(values))
    sigma = _sample_std(values)

    if sigma <= 0:
        cp = float("inf") if usl > lsl else 0.0
        cpk = float("inf") if usl > lsl else 0.0
    else:
        cp = float((usl - lsl) / (6.0 * sigma))
        cpu = float((usl - mean) / (3.0 * sigma))
        cpl = float((mean - lsl) / (3.0 * sigma))
        cpk = min(cpu, cpl)

    # Practical capability verdict: capable at >= 1.33, marginal at >= 1.0.
    if cp >= 1.33 and cpk >= 1.33:
        verdict = "capable"
    elif cp >= 1.0 and cpk >= 1.0:
        verdict = "marginal"
    else:
        verdict = "not capable"

    return {
        "cp": cp,
        "cpk": cpk,
        "sigma": sigma,
        "mean": mean,
        "verdict": verdict,
    }


__all__ = [
    "calculateGRR",
    "calculateProcessCapability",
    "calculateXbarR",
    "detectWesternElectricViolations",
]