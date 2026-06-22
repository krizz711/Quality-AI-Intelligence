"""
GR&R Calculator — ANOVA and Xbar-R methods for measurement system analysis.

References:
  - AIAG MSA Manual, 4th Edition
  - Montgomery, "Introduction to Statistical Quality Control", Ch. 8
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def _d2_star(sample_size: int) -> float:
    d2_star = {
        2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326,
        6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.179
    }
    if sample_size in d2_star:
        return d2_star[sample_size]
    raise ValueError(
        f"Sample size {sample_size} is outside the supported d2* table range (2-10)."
    )


@dataclass
class GRRResult:
    """Container for GR&R study outputs."""

    total_grr: float  # %GR&R of total variation
    repeatability: float  # Equipment Variation (EV)
    reproducibility: float  # Appraiser Variation (AV)
    part_variation: float  # Part-to-part Variation (PV)
    total_variation: float  # Total Variation (TV)
    ndc: int  # Number of Distinct Categories
    details: dict[str, Any] | None = None


def grr_xbar_r(
    data: pd.DataFrame,
    *,
    part_col: str = "part",
    operator_col: str = "operator",
    measurement_col: str = "measurement",
    tolerance: float | None = None,
) -> GRRResult:
    """
    Perform a GR&R study using the Xbar-R (Average & Range) method.

    Parameters
    ----------
    data : pd.DataFrame
        Long-format dataframe with columns for part, operator, and measurement.
    part_col, operator_col, measurement_col : str
        Column name overrides.
    tolerance : float | None
        If provided, %GR&R is calculated relative to the tolerance band
        instead of total variation.

    Returns
    -------
    GRRResult
    """
    # 1. VALIDATE INPUT
    n_operators = data[operator_col].nunique()
    n_parts = data[part_col].nunique()

    if n_operators < 2 or n_parts < 2:
        raise ValueError("Data must have at least 2 unique operators and 2 unique parts.")

    trials_per_cell = data.groupby([operator_col, part_col]).size()
    k = int(trials_per_cell.iloc[0])
    if not (trials_per_cell == k).all():
        raise ValueError("Each operator-part combination must have the same number of trials.")

    # 2. COMPUTE RANGES PER OPERATOR-PART CELL
    ranges_series = (
        data.groupby([operator_col, part_col])[measurement_col].max()
        - data.groupby([operator_col, part_col])[measurement_col].min()
    )
    ranges = ranges_series.reset_index(name="range")

    # 3. COMPUTE R-BAR (average range)
    R_bar = ranges["range"].mean()

    # 4. COMPUTE X-BAR PER OPERATOR (average measurement per operator)
    x_bar_operator = data.groupby(operator_col)[measurement_col].mean()
    X_diff = x_bar_operator.max() - x_bar_operator.min()

    # 5. COMPUTE PART AVERAGES
    x_bar_part = data.groupby(part_col)[measurement_col].mean()
    R_p = x_bar_part.max() - x_bar_part.min()

    # 6. LOOK UP d2* CONSTANTS
    d2_EV = _d2_star(k)
    d2_AV = _d2_star(n_operators)
    d2_PV = _d2_star(n_parts)

    # 7. COMPUTE VARIANCE COMPONENTS
    EV = R_bar / d2_EV
    AV_squared = (X_diff / d2_AV)**2 - (EV**2 / (n_parts * k))
    AV = np.sqrt(max(0, AV_squared))
    PV = R_p / d2_PV
    GRR = np.sqrt(EV**2 + AV**2)
    TV = np.sqrt(GRR**2 + PV**2)

    # 8. COMPUTE %GRR
    if tolerance is not None:
        grr_percent = (GRR / (tolerance / 6)) * 100
    else:
        grr_percent = (GRR / TV) * 100 if TV > 0 else 0.0

    # 9. COMPUTE NDC
    ndc = int(1.41 * (PV / GRR)) if GRR > 0 else 0

    # 10. RETURN GRRResult
    result = GRRResult(
        total_grr=round(grr_percent, 4),
        repeatability=round(EV, 6),
        reproducibility=round(AV, 6),
        part_variation=round(PV, 6),
        total_variation=round(TV, 6),
        ndc=ndc,
        details={
            "r_bar": R_bar,
            "x_diff": X_diff,
            "r_p": R_p,
            "n_operators": n_operators,
            "n_parts": n_parts,
            "n_trials": k,
            "method": "xbar_r"
        }
    )

    logger.info("Calculated GR&R Xbar-R successfully: %s", result)
    return result


def grr_anova(
    data: pd.DataFrame,
    *,
    part_col: str = "part",
    operator_col: str = "operator",
    measurement_col: str = "measurement",
    tolerance: float | None = None,
) -> GRRResult:
    """
    Perform a GR&R study using the ANOVA method.

    This method can also capture the operator × part interaction effect.

    Parameters
    ----------
    data : pd.DataFrame
        Long-format dataframe with columns for part, operator, and measurement.
    tolerance : float | None
        Optional tolerance band for %GR&R calculation.

    Returns
    -------
    GRRResult
    """
    # 1. VALIDATE INPUT
    n_operators = data[operator_col].nunique()
    n_parts = data[part_col].nunique()

    if n_operators < 2 or n_parts < 2:
        raise ValueError("Data must have at least 2 unique operators and 2 unique parts.")

    trials_per_cell = data.groupby([operator_col, part_col]).size()
    k = int(trials_per_cell.iloc[0])
    if not (trials_per_cell == k).all():
        raise ValueError("Each operator-part combination must have the same number of trials.")

    grand_mean = data[measurement_col].mean()

    # 2. COMPUTE CELL MEANS AND MARGINAL MEANS
    cell_means = data.groupby([operator_col, part_col])[measurement_col].mean()
    operator_means = data.groupby(operator_col)[measurement_col].mean()
    part_means = data.groupby(part_col)[measurement_col].mean()

    # 3. COMPUTE SUMS OF SQUARES
    SS_total = ((data[measurement_col] - grand_mean)**2).sum()
    SS_part = n_operators * k * ((part_means - grand_mean)**2).sum()
    SS_operator = n_parts * k * ((operator_means - grand_mean)**2).sum()
    
    SS_interaction = 0
    for op in data[operator_col].unique():
        for pt in data[part_col].unique():
            val = cell_means.loc[(op, pt)] - part_means.loc[pt] - operator_means.loc[op] + grand_mean
            SS_interaction += k * (val**2)

    SS_error = SS_total - SS_part - SS_operator - SS_interaction

    # 4. COMPUTE DEGREES OF FREEDOM
    df_part = n_parts - 1
    df_operator = n_operators - 1
    df_interaction = df_part * df_operator
    df_error = n_parts * n_operators * (k - 1)

    # 5. COMPUTE MEAN SQUARES
    MS_part = SS_part / df_part
    MS_operator = SS_operator / df_operator
    MS_interaction = SS_interaction / df_interaction
    MS_error = SS_error / df_error if df_error > 0 else 0

    # 6. F-TEST FOR INTERACTION
    F_interaction = MS_interaction / MS_error if MS_error > 0 else 0
    p_interaction = 1 - stats.f.cdf(F_interaction, df_interaction, df_error)

    if p_interaction > 0.05:
        # Interaction NOT significant — pool into error
        MS_error_pooled = (SS_interaction + SS_error) / (df_interaction + df_error)
        interaction_significant = False
    else:
        MS_error_pooled = MS_error
        interaction_significant = True

    # 7. EXTRACT VARIANCE COMPONENTS
    var_error = MS_error_pooled

    if interaction_significant:
        var_operator = max(0, (MS_operator - MS_interaction) / (n_parts * k))
        var_interaction = max(0, (MS_interaction - MS_error) / k)
        var_part = max(0, (MS_part - MS_interaction) / (n_operators * k))
    else:
        var_operator = max(0, (MS_operator - MS_error_pooled) / (n_parts * k))
        var_interaction = 0
        var_part = max(0, (MS_part - MS_error_pooled) / (n_operators * k))

    # 8. COMPUTE FINAL METRICS
    EV = np.sqrt(var_error)
    AV = np.sqrt(var_operator)
    IV = np.sqrt(var_interaction)
    GRR = np.sqrt(var_error + var_operator + var_interaction)
    PV = np.sqrt(var_part)
    TV = np.sqrt(GRR**2 + var_part)

    if tolerance is not None:
        grr_percent = (GRR / (tolerance / 6)) * 100
    else:
        grr_percent = (GRR / TV) * 100 if TV > 0 else 0

    ndc = int(1.41 * PV / GRR) if GRR > 0 else 0

    # 9. RETURN GRRResult
    result = GRRResult(
        total_grr=round(grr_percent, 4),
        repeatability=round(EV, 6),
        reproducibility=round(AV, 6),
        part_variation=round(PV, 6),
        total_variation=round(TV, 6),
        ndc=ndc,
        details={
            "method": "anova",
            "interaction_significant": interaction_significant,
            "p_interaction": round(float(p_interaction), 4),
            "ms_error": MS_error,
            "ms_operator": MS_operator,
            "ms_part": MS_part,
            "ms_interaction": MS_interaction,
            "var_interaction": var_interaction,
            "iv": round(float(IV), 6),
            "n_operators": n_operators,
            "n_parts": n_parts,
            "n_trials": k
        }
    )
    
    logger.info("Calculated GR&R ANOVA successfully: %s", result)
    return result
