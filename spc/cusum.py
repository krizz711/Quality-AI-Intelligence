"""
CUSUM Control Chart — Cumulative Sum for detecting sustained process shifts.

References:
  - AIAG SPC Manual, 2nd Edition
  - Montgomery, "Introduction to Statistical Quality Control", Ch. 9
  - Hawkins & Olwell, "Cumulative Sum Charts and Charting for Quality Improvement"

Typical detection performance with default k=0.5, h=4.0:
  - 1σ shift: detects in ~8 measurements on average (ARL ≈ 8.4)
  - 2σ shift: detects in ~4 measurements on average (ARL ≈ 4.0)
  - 3σ shift: detects in ~2 measurements on average

To detect a 1σ shift within ≤5 points, use h=2.0.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CUSUMResult:
    """Result of a CUSUM control chart analysis."""

    upper_cusum: np.ndarray   # C+ cumulative sum values
    lower_cusum: np.ndarray   # C- cumulative sum values
    shift_detected: bool
    shift_indices: list[int] = field(default_factory=list)
    shift_direction: str = "none"  # "upward" | "downward" | "both" | "none"
    first_signal_index: int | None = None
    params: dict[str, Any] = field(default_factory=dict)


def cusum_chart(
    values: np.ndarray | list[float],
    cl: float,
    sigma: float,
    *,
    k: float = 0.5,
    h: float = 4.0,
) -> CUSUMResult:
    """
    Compute the two-sided CUSUM control chart.

    Uses the standardized form:
      z_i = (x_i - cl) / sigma
      C+_i = max(0, C+_{i-1} + z_i - k)    (detects upward shifts)
      C-_i = max(0, C-_{i-1} - z_i - k)    (detects downward shifts)

    A signal is raised when C+_i > h or C-_i > h.

    Parameters
    ----------
    values : array-like
        Ordered measurement values (oldest → newest).
    cl : float
        Process center line (target / mean).
    sigma : float
        Process standard deviation (estimated from in-control data).
    k : float
        Reference value (allowable slack), in sigma units. Default 0.5.
        k = Δ/2 for a shift of size Δ*sigma. k=0.5 targets a 1σ shift.
    h : float
        Decision interval in sigma units. Default 4.0 (industry standard).
        Use h=2.0 for faster detection at the cost of more false alarms.

    Returns
    -------
    CUSUMResult

    Raises
    ------
    ValueError
        If fewer than 2 values are provided or sigma ≤ 0.
    """
    vals = np.asarray(values, dtype=float)
    n = len(vals)
    if n < 2:
        raise ValueError("CUSUM requires at least 2 data points")
    if sigma <= 0:
        raise ValueError("sigma must be > 0")

    z = (vals - cl) / sigma          # standardized observations
    c_plus = np.zeros(n)
    c_minus = np.zeros(n)

    for i in range(n):
        c_plus[i] = max(0.0, (c_plus[i - 1] if i > 0 else 0.0) + z[i] - k)
        c_minus[i] = max(0.0, (c_minus[i - 1] if i > 0 else 0.0) - z[i] - k)

    upper_violations = [i for i in range(n) if c_plus[i] > h]
    lower_violations = [i for i in range(n) if c_minus[i] > h]
    all_violations = sorted(set(upper_violations) | set(lower_violations))

    shift_detected = len(all_violations) > 0
    first_signal = all_violations[0] if all_violations else None

    if upper_violations and lower_violations:
        direction = "both"
    elif upper_violations:
        direction = "upward"
    elif lower_violations:
        direction = "downward"
    else:
        direction = "none"

    if shift_detected:
        logger.warning(
            "CUSUM shift detected at index %d — direction=%s, k=%.2f, h=%.2f",
            first_signal,
            direction,
            k,
            h,
        )
    else:
        logger.debug("CUSUM: no shift detected (k=%.2f, h=%.2f, n=%d)", k, h, n)

    return CUSUMResult(
        upper_cusum=c_plus,
        lower_cusum=c_minus,
        shift_detected=shift_detected,
        shift_indices=all_violations,
        shift_direction=direction,
        first_signal_index=first_signal,
        params={"k": k, "h": h, "n": n, "cl": cl, "sigma": sigma},
    )


def cusum_from_limits(
    values: np.ndarray | list[float],
    ucl: float,
    lcl: float,
    *,
    k: float = 0.5,
    h: float = 4.0,
) -> CUSUMResult:
    """
    Convenience wrapper that derives cl and sigma from existing control limits.

    Parameters
    ----------
    ucl, lcl : float
        Upper and lower 3-sigma control limits from an existing I-MR or Xbar chart.
    k, h : float
        CUSUM parameters (see cusum_chart).

    Returns
    -------
    CUSUMResult
    """
    cl = (ucl + lcl) / 2.0
    sigma = (ucl - lcl) / 6.0
    return cusum_chart(values, cl, sigma, k=k, h=h)
