"""
Control Charts — Xbar-R, Xbar-S, Individual-MR, and p/np/c/u charts.

Provides functions to compute control limits and plot data for
real-time SPC monitoring on the manufacturing floor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ControlLimits:
    """Computed control limits for a chart."""

    ucl: float  # Upper Control Limit
    cl: float   # Center Line
    lcl: float  # Lower Control Limit
    sigma: float = 0.0


@dataclass
class ChartData:
    """Full chart output including limits and plotted points."""

    chart_type: str
    limits: ControlLimits
    points: list[float] = field(default_factory=list)
    out_of_control: list[int] = field(default_factory=list)  # indices
    metadata: dict[str, Any] = field(default_factory=dict)


def xbar_r_chart(
    data: pd.DataFrame,
    *,
    subgroup_col: str = "subgroup",
    value_col: str = "value",
) -> tuple[ChartData, ChartData]:
    """
    Compute Xbar and R charts for subgrouped data.

    Returns
    -------
    tuple[ChartData, ChartData]
        (xbar_chart, r_chart)
    """
    # SPC constants keyed by subgroup size n
    A2 = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577,
          6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}
    D3 = {2: 0, 3: 0, 4: 0, 5: 0,
          6: 0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223}
    D4 = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114,
          6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}

    grouped = data.groupby(subgroup_col)[value_col]
    subgroup_counts = grouped.count()
    if subgroup_counts.empty:
        raise ValueError("No subgroups found in data")
    if subgroup_counts.nunique() != 1:
        sizes = subgroup_counts.value_counts().to_dict()
        raise ValueError(
            f"Inconsistent subgroup sizes: {sizes}. "
            "All subgroups must have the same number of values."
        )

    n = int(subgroup_counts.iloc[0])
    if n not in A2:
        raise ValueError(
            f"Subgroup size {n} is not supported (must be between 2 and 10)"
        )

    subgroup_means = grouped.mean()
    subgroup_ranges = grouped.max() - grouped.min()

    x_double_bar = float(subgroup_means.mean())
    r_bar = float(subgroup_ranges.mean())

    a2 = A2[n]
    d3 = D3[n]
    d4 = D4[n]

    # Xbar chart limits
    xbar_ucl = x_double_bar + a2 * r_bar
    xbar_lcl = x_double_bar - a2 * r_bar
    xbar_sigma = (xbar_ucl - x_double_bar) / 3.0

    xbar_points = subgroup_means.tolist()
    xbar_ooc = [i for i, p in enumerate(xbar_points)
                if p > xbar_ucl or p < xbar_lcl]

    xbar_chart = ChartData(
        chart_type="xbar",
        limits=ControlLimits(
            ucl=xbar_ucl, cl=x_double_bar, lcl=xbar_lcl, sigma=xbar_sigma,
        ),
        points=xbar_points,
        out_of_control=xbar_ooc,
    )

    # R chart limits
    r_ucl = d4 * r_bar
    r_lcl = d3 * r_bar
    r_points = subgroup_ranges.tolist()
    r_ooc = [i for i, p in enumerate(r_points)
             if p > r_ucl or p < r_lcl]

    r_chart = ChartData(
        chart_type="range",
        limits=ControlLimits(ucl=r_ucl, cl=r_bar, lcl=r_lcl),
        points=r_points,
        out_of_control=r_ooc,
    )

    logger.info(
        "xbar_r_chart computed — n=%d, X̄̄=%.4f, R̄=%.4f, "
        "xbar OOC=%d, range OOC=%d",
        n, x_double_bar, r_bar, len(xbar_ooc), len(r_ooc),
    )
    return xbar_chart, r_chart


def individuals_mr_chart(
    values: list[float] | np.ndarray,
) -> tuple[ChartData, ChartData]:
    """
    Compute Individual (I) and Moving Range (MR) charts.

    Returns
    -------
    tuple[ChartData, ChartData]
        (i_chart, mr_chart)
    """
    vals = np.asarray(values, dtype=float)

    # Moving ranges: MR_i = |x_i - x_{i-1}| for i = 1..n-1
    mr = np.abs(np.diff(vals))
    mr_bar = float(mr.mean())
    x_bar = float(vals.mean())

    d2 = 1.128  # constant for n=2

    # I chart limits
    i_ucl = x_bar + 2.66 * mr_bar
    i_lcl = x_bar - 2.66 * mr_bar
    i_sigma = mr_bar / d2

    i_points = vals.tolist()
    i_ooc = [i for i, p in enumerate(i_points)
             if p > i_ucl or p < i_lcl]

    i_chart = ChartData(
        chart_type="individuals",
        limits=ControlLimits(ucl=i_ucl, cl=x_bar, lcl=i_lcl, sigma=i_sigma),
        points=i_points,
        out_of_control=i_ooc,
    )

    # MR chart limits (D4=3.267, D3=0 for n=2)
    mr_ucl = 3.267 * mr_bar
    mr_lcl = 0.0
    mr_points = mr.tolist()
    mr_ooc = [i for i, p in enumerate(mr_points)
              if p > mr_ucl or p < mr_lcl]

    mr_chart = ChartData(
        chart_type="moving_range",
        limits=ControlLimits(ucl=mr_ucl, cl=mr_bar, lcl=mr_lcl),
        points=mr_points,
        out_of_control=mr_ooc,
    )

    logger.info(
        "individuals_mr_chart computed — X̄=%.4f, MR̄=%.4f, "
        "I OOC=%d, MR OOC=%d",
        x_bar, mr_bar, len(i_ooc), len(mr_ooc),
    )
    return i_chart, mr_chart


def p_chart(
    defective_counts: list[int],
    sample_sizes: list[int],
) -> ChartData:
    """
    Compute a p-chart (proportion nonconforming) with variable control limits.
    """
    defects = np.asarray(defective_counts, dtype=float)
    sizes = np.asarray(sample_sizes, dtype=float)

    p_bar = float(defects.sum() / sizes.sum())

    # Variable limits per subgroup
    sigma_i = np.sqrt(p_bar * (1.0 - p_bar) / sizes)
    ucl_i = p_bar + 3.0 * sigma_i
    lcl_i = np.maximum(0.0, p_bar - 3.0 * sigma_i)
    p_i = defects / sizes

    ooc = [i for i in range(len(p_i))
           if p_i[i] > ucl_i[i] or p_i[i] < lcl_i[i]]

    # Use average UCL / LCL across all subgroups for the ChartData limits
    avg_ucl = float(ucl_i.mean())
    avg_lcl = float(lcl_i.mean())
    avg_sigma = float(sigma_i.mean())

    chart = ChartData(
        chart_type="p",
        limits=ControlLimits(ucl=avg_ucl, cl=p_bar, lcl=avg_lcl, sigma=avg_sigma),
        points=p_i.tolist(),
        out_of_control=ooc,
    )

    logger.info(
        "p_chart computed — p̄=%.4f, avg UCL=%.4f, avg LCL=%.4f, OOC=%d",
        p_bar, avg_ucl, avg_lcl, len(ooc),
    )
    return chart
