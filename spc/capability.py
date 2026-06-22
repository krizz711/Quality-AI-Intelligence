"""
Process Capability Indices — Cpk, Ppk, Cp, Pp calculations.

References:
  - AIAG SPC Manual, 2nd Edition
  - Montgomery, "Introduction to Statistical Quality Control", Ch. 7
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CapabilityResult:
    """Container for process capability study outputs."""

    cp: float       # Process Capability (uses within-subgroup σ)
    cpk: float      # Process Capability Index (accounts for centering)
    pp: float       # Process Performance (uses overall σ)
    ppk: float      # Process Performance Index (accounts for centering)
    cpu: float      # Upper capability index
    cpl: float      # Lower capability index
    mean: float
    sigma_within: float   # Within-subgroup standard deviation
    sigma_overall: float  # Overall standard deviation
    usl: float
    lsl: float
    ppm_above: float     # Estimated PPM above USL
    ppm_below: float     # Estimated PPM below LSL
    ppm_total: float


def _estimate_sigma_within(values: np.ndarray, subgroup_size: int = 1) -> float:
    """
    Estimate within-subgroup sigma.

    For individuals (subgroup_size=1): use moving range / d2.
    For subgroups: use R-bar / d2.
    """
    d2_table = {
        1: 1.128,  # moving range of 2
        2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326,
        6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.179,
    }

    if subgroup_size <= 1:
        # Individuals — use moving range
        mr = np.abs(np.diff(values))
        mr_bar = float(mr.mean())
        return mr_bar / d2_table[1]
    else:
        # Subgrouped data — use range within subgroups
        n_subgroups = len(values) // subgroup_size
        if n_subgroups < 2:
            return float(np.std(values, ddof=1))
        subgroups = values[: n_subgroups * subgroup_size].reshape(n_subgroups, subgroup_size)
        ranges = subgroups.max(axis=1) - subgroups.min(axis=1)
        r_bar = float(ranges.mean())
        d2 = d2_table.get(subgroup_size, 2.326)
        return r_bar / d2


def capability_indices(
    values: list[float] | np.ndarray,
    usl: float,
    lsl: float,
    *,
    subgroup_size: int = 1,
) -> CapabilityResult:
    """
    Calculate Cp, Cpk, Pp, Ppk for a dataset.

    Parameters
    ----------
    values : array-like
        Measurement values (at least 25 recommended per AIAG).
    usl : float
        Upper Specification Limit.
    lsl : float
        Lower Specification Limit.
    subgroup_size : int
        Subgroup size for within-subgroup sigma estimation.

    Returns
    -------
    CapabilityResult
    """
    vals = np.asarray(values, dtype=float)
    if len(vals) < 2:
        raise ValueError("Need at least 2 values for capability study")
    if usl <= lsl:
        raise ValueError("USL must be greater than LSL")

    mean = float(vals.mean())
    sigma_overall = float(vals.std(ddof=1))
    sigma_within = _estimate_sigma_within(vals, subgroup_size)

    # Guard against zero sigma
    if sigma_within <= 0:
        sigma_within = sigma_overall if sigma_overall > 0 else 1e-10
    if sigma_overall <= 0:
        sigma_overall = 1e-10

    tolerance = usl - lsl

    # Cp/Cpk (short-term, within-subgroup)
    cp = tolerance / (6 * sigma_within)
    cpu = (usl - mean) / (3 * sigma_within)
    cpl = (mean - lsl) / (3 * sigma_within)
    cpk = min(cpu, cpl)

    # Pp/Ppk (long-term, overall)
    pp = tolerance / (6 * sigma_overall)
    ppu = (usl - mean) / (3 * sigma_overall)
    ppl = (mean - lsl) / (3 * sigma_overall)
    ppk = min(ppu, ppl)

    # Estimated PPM
    from scipy.stats import norm
    z_upper = (usl - mean) / sigma_overall
    z_lower = (mean - lsl) / sigma_overall
    ppm_above = float(norm.sf(z_upper) * 1_000_000)
    ppm_below = float(norm.sf(z_lower) * 1_000_000)
    ppm_total = ppm_above + ppm_below

    result = CapabilityResult(
        cp=round(cp, 4),
        cpk=round(cpk, 4),
        pp=round(pp, 4),
        ppk=round(ppk, 4),
        cpu=round(cpu, 4),
        cpl=round(cpl, 4),
        mean=round(mean, 6),
        sigma_within=round(sigma_within, 6),
        sigma_overall=round(sigma_overall, 6),
        usl=usl,
        lsl=lsl,
        ppm_above=round(ppm_above, 1),
        ppm_below=round(ppm_below, 1),
        ppm_total=round(ppm_total, 1),
    )

    logger.info(
        "capability_indices computed — Cp=%.3f Cpk=%.3f Pp=%.3f Ppk=%.3f",
        cp, cpk, pp, ppk,
    )
    return result
