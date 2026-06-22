"""
EWMA Control Chart — Exponentially Weighted Moving Average for trend detection.

The EWMA chart weights recent observations more heavily than older ones,
making it sensitive to small sustained shifts that Shewhart charts miss.

References:
  - Montgomery, "Introduction to Statistical Quality Control", Ch. 9
  - Roberts (1959), "Control Chart Tests Based on Geometric Moving Averages"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EWMAResult:
    """Result of an EWMA control chart analysis."""

    ewma_values: np.ndarray     # Z_i smoothed values
    ucl: np.ndarray             # time-varying upper control limits
    lcl: np.ndarray             # time-varying lower control limits
    cl: float                   # center line
    shift_detected: bool
    violation_indices: list[int] = field(default_factory=list)
    drift_direction: str = "none"  # "upward" | "downward" | "none"
    steady_state_ucl: float = 0.0
    steady_state_lcl: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)


def ewma_chart(
    values: np.ndarray | list[float],
    cl: float,
    sigma: float,
    *,
    lambda_: float = 0.2,
    L: float = 3.0,
) -> EWMAResult:
    """
    Compute the EWMA control chart with time-varying control limits.

    Recursion:
      Z_0 = cl
      Z_i = λ*x_i + (1 − λ)*Z_{i−1}

    Time-varying limits (exact):
      UCL_i = cl + L*σ*sqrt( λ/(2−λ) * (1 − (1−λ)^{2i}) )
      LCL_i = cl − L*σ*sqrt( λ/(2−λ) * (1 − (1−λ)^{2i}) )

    Steady-state limits (i → ∞):
      UCL_ss = cl + L*σ*sqrt( λ/(2−λ) )
      LCL_ss = cl − L*σ*sqrt( λ/(2−λ) )

    A signal is raised when Z_i > UCL_i or Z_i < LCL_i.

    Parameters
    ----------
    values : array-like
        Ordered measurement values (oldest → newest).
    cl : float
        Process center line (target / mean).
    sigma : float
        Process standard deviation (estimated from in-control data).
    lambda_ : float
        Smoothing constant (0 < λ ≤ 1). Default 0.2.
        Smaller λ → more smoothing → sensitive to smaller shifts.
        λ = 1 reduces to the Shewhart chart.
    L : float
        Control limit width in sigma units. Default 3.0.
        L = 2.7 is recommended for λ = 0.05–0.25 to maintain ARL ≈ 370.

    Returns
    -------
    EWMAResult

    Raises
    ------
    ValueError
        If fewer than 2 values are provided, sigma ≤ 0, or lambda_ out of range.
    """
    vals = np.asarray(values, dtype=float)
    n = len(vals)
    if n < 2:
        raise ValueError("EWMA chart requires at least 2 data points")
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    if not (0 < lambda_ <= 1):
        raise ValueError("lambda_ must be in (0, 1]")

    z = np.zeros(n)
    ucl_arr = np.zeros(n)
    lcl_arr = np.zeros(n)

    z[0] = lambda_ * vals[0] + (1 - lambda_) * cl

    for i in range(1, n):
        z[i] = lambda_ * vals[i] + (1 - lambda_) * z[i - 1]

    factor_base = lambda_ / (2 - lambda_)
    for i in range(n):
        factor = factor_base * (1 - (1 - lambda_) ** (2 * (i + 1)))
        half_width = L * sigma * np.sqrt(factor)
        ucl_arr[i] = cl + half_width
        lcl_arr[i] = cl - half_width

    # Steady-state limits (used for long-run interpretation)
    ss_half_width = L * sigma * np.sqrt(factor_base)
    ss_ucl = cl + ss_half_width
    ss_lcl = cl - ss_half_width

    violations = [i for i in range(n) if z[i] > ucl_arr[i] or z[i] < lcl_arr[i]]
    shift_detected = len(violations) > 0

    # Determine dominant drift direction from recent half of the series
    mid = n // 2
    early_mean = float(z[:mid].mean()) if mid > 0 else cl
    late_mean = float(z[mid:].mean())
    if late_mean > early_mean + 0.1 * sigma:
        drift_direction = "upward"
    elif late_mean < early_mean - 0.1 * sigma:
        drift_direction = "downward"
    else:
        drift_direction = "none"

    if shift_detected:
        logger.warning(
            "EWMA shift detected — first violation at index %d, direction=%s, λ=%.2f",
            violations[0],
            drift_direction,
            lambda_,
        )
    else:
        logger.debug("EWMA: in-control (λ=%.2f, n=%d)", lambda_, n)

    return EWMAResult(
        ewma_values=z,
        ucl=ucl_arr,
        lcl=lcl_arr,
        cl=cl,
        shift_detected=shift_detected,
        violation_indices=violations,
        drift_direction=drift_direction,
        steady_state_ucl=ss_ucl,
        steady_state_lcl=ss_lcl,
        params={"lambda_": lambda_, "L": L, "n": n, "cl": cl, "sigma": sigma},
    )


def ewma_from_limits(
    values: np.ndarray | list[float],
    ucl: float,
    lcl: float,
    *,
    lambda_: float = 0.2,
    L: float = 3.0,
) -> EWMAResult:
    """
    Convenience wrapper that derives cl and sigma from existing control limits.

    Parameters
    ----------
    ucl, lcl : float
        Upper and lower 3-sigma control limits from an existing I-MR or Xbar chart.

    Returns
    -------
    EWMAResult
    """
    cl = (ucl + lcl) / 2.0
    sigma = (ucl - lcl) / 6.0
    return ewma_chart(values, cl, sigma, lambda_=lambda_, L=L)
