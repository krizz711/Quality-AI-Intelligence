"""Establish and validate frozen SPC baselines (Phase I → Phase II).

A *baseline* locks the control limits computed from a window of stable measurements
so later points are judged against fixed limits (**Phase II**) instead of limits that
drift with the data and hide the very problem you're watching for.

This module is the single, framework-free place that:
  * computes limits with the correct **Individuals / Moving-Range** method,
  * **validates** the baseline window is itself in statistical control before locking
    (Phase I requires a stable period — freezing on an unstable window bakes the
    problem into the limits), and
  * **guards** against degenerate, near-zero variation that would collapse the limits
    onto the mean and make every later point look out of control.

It has no DB or web dependencies, so it is cheap to unit-test. Persistence lives in
``core.spc_baseline_store``; both the API and the autonomous monitor read the stored
baseline so they judge points against the *same* limits.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from spc.control_charts import individuals_mr_chart
from spc.nelson_rules import evaluate_all_rules

# Individual measurements need a reasonable window before limits mean anything.
MIN_BASELINE_POINTS = 15

# Nelson rules whose violation means the baseline window was NOT a stable Phase-I
# period (an outlier, a sustained shift, or a trend = assignable cause). If any of
# these fire we refuse to freeze unless the caller explicitly forces it.
_DISQUALIFYING_RULES = ("rule_1", "rule_2", "rule_3")


@dataclass(frozen=True)
class Baseline:
    """Frozen control limits for a process."""

    ucl: float
    cl: float
    lcl: float
    sigma: float
    n_points: int


@dataclass(frozen=True)
class BaselineResult:
    ok: bool
    reason: str                       # "" when ok; human-readable why-not otherwise
    baseline: Baseline | None         # computed limits (present even when not ok, for preview)
    violations: dict[str, list[int]]  # Nelson rules tripped in the window (for the UI)


def _sigma_floor(center: float) -> float:
    """Variation below this (relative to the reading magnitude) is treated as "no real
    variation" — a stuck sensor, constant values, or gauge resolution far too coarse."""
    return max(abs(center) * 1e-9, 1e-12)


def compute_baseline(
    values: list[float] | np.ndarray,
    *,
    min_points: int = MIN_BASELINE_POINTS,
    force: bool = False,
) -> BaselineResult:
    """Compute and validate a frozen baseline from ``values``.

    Returns a :class:`BaselineResult`. ``ok`` is True only when the window has enough
    points, real variation, and is in statistical control (or ``force=True``). When
    ``ok`` is False the ``baseline`` field still carries the computed limits and
    ``violations`` lists the offending points so the UI can show what to investigate.
    """
    vals = [float(v) for v in values]
    n = len(vals)
    if n < min_points:
        return BaselineResult(
            False,
            f"Need at least {min_points} points to set a baseline (have {n}).",
            None,
            {},
        )

    arr = np.asarray(vals, dtype=float)
    i_chart, _ = individuals_mr_chart(arr)
    lim = i_chart.limits

    # Degenerate-variation guard: MR-based sigma ~ 0 → UCL ≈ LCL ≈ mean, so every
    # later wobble trips Rule 1. Refuse rather than freeze unusable limits.
    if lim.sigma <= _sigma_floor(lim.cl):
        return BaselineResult(
            False,
            "Variation is too small to set reliable limits — the readings are nearly "
            "identical. Check the gauge resolution, or that the values aren't constant.",
            None,
            {},
        )

    violations = evaluate_all_rules(arr, lim.cl, lim.sigma)
    baseline = Baseline(ucl=lim.ucl, cl=lim.cl, lcl=lim.lcl, sigma=lim.sigma, n_points=n)

    disqualifying = {r: violations[r] for r in _DISQUALIFYING_RULES if violations.get(r)}
    if disqualifying and not force:
        offending = sorted({i for idxs in disqualifying.values() for i in idxs})
        return BaselineResult(
            False,
            f"The baseline window isn't in control yet — {len(offending)} point(s) "
            f"violate stability rules ({', '.join(sorted(disqualifying))}). Investigate "
            "or remove those points, then re-baseline a stable window (or force it).",
            baseline,
            violations,
        )

    return BaselineResult(True, "", baseline, violations)
