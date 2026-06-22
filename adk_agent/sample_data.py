"""Reproducible synthetic data so the agent can run end to end with zero setup."""

from __future__ import annotations

import numpy as np
import pandas as pd

_GRR_QUALITY = {"acceptable": 0.04, "marginal": 0.12, "unacceptable": 0.30}


def generate_grr_study(
    *,
    n_parts: int = 10,
    n_operators: int = 3,
    n_trials: int = 2,
    quality: str = "acceptable",
    nominal: float = 12.0,
    part_spread: float = 2.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a long-format GR&R dataset (columns: part, operator, measurement)."""
    if quality not in _GRR_QUALITY:
        raise ValueError(f"quality must be one of {list(_GRR_QUALITY)}")
    rng = np.random.default_rng(seed)
    gage_sigma = part_spread * _GRR_QUALITY[quality]
    true_part_values = nominal + rng.normal(0, part_spread, n_parts)
    operator_bias = rng.normal(0, gage_sigma * 0.5, n_operators)

    rows = []
    for p in range(n_parts):
        for o in range(n_operators):
            for _ in range(n_trials):
                noise = rng.normal(0, gage_sigma)
                rows.append({
                    "part": f"P{p + 1:02d}",
                    "operator": f"Op{o + 1}",
                    "measurement": round(float(true_part_values[p] + operator_bias[o] + noise), 4),
                })
    return pd.DataFrame(rows)


def generate_spc_series(
    *, n: int = 40, scenario: str = "shift", nominal: float = 100.0, sigma: float = 1.0, seed: int = 7
) -> list[float]:
    """Generate an individuals series for a scenario.

    Scenarios: in_control, shift, trend, outlier, drift_to_breach.
    """
    rng = np.random.default_rng(seed)
    base = rng.normal(nominal, sigma, n)
    if scenario == "in_control":
        series = base
    elif scenario == "shift":
        base[n // 2:] += 3 * sigma
        series = base
    elif scenario == "trend":
        series = base + np.linspace(0, 4 * sigma, n)
    elif scenario == "outlier":
        base[n // 2] += 6 * sigma
        series = base
    elif scenario == "drift_to_breach":
        series = base + np.linspace(0, 5 * sigma, n)
    else:
        raise ValueError("scenario must be: in_control, shift, trend, outlier, drift_to_breach")
    return [round(float(v), 4) for v in series]
