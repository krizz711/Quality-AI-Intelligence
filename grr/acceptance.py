"""
Acceptance criteria evaluator for GR&R studies.

Industry-standard thresholds (AIAG MSA 4th Ed.):
  - %GR&R < 10%   → Acceptable
  - 10% ≤ %GR&R ≤ 30% → Conditionally acceptable (may require improvement)
  - %GR&R > 30%   → Not acceptable
  - ndc ≥ 5        → Adequate measurement discrimination
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from grr.calculator import GRRResult

logger = logging.getLogger(__name__)


class AcceptanceLevel(Enum):
    """AIAG-based acceptance classification."""

    ACCEPTABLE = "acceptable"
    CONDITIONAL = "conditional"
    NOT_ACCEPTABLE = "not_acceptable"


@dataclass
class AcceptanceVerdict:
    """Result of evaluating a GR&R study against acceptance criteria."""

    level: AcceptanceLevel
    grr_percent: float
    ndc: int
    ndc_adequate: bool
    remarks: list[str]
    requires_human_review: bool = False


def evaluate(
    result: GRRResult,
    *,
    grr_threshold_accept: float = 10.0,
    grr_threshold_conditional: float = 30.0,
    min_ndc: int = 5,
) -> AcceptanceVerdict:
    """
    Evaluate a GR&R result against configurable acceptance thresholds.

    Parameters
    ----------
    result : GRRResult
        Output from `grr.calculator.grr_xbar_r` or `grr.calculator.grr_anova`.
    grr_threshold_accept : float
        %GR&R below this is fully acceptable (default 10%).
    grr_threshold_conditional : float
        %GR&R between accept and this threshold is conditionally acceptable.
    min_ndc : int
        Minimum number of distinct categories (default 5).

    Returns
    -------
    AcceptanceVerdict
    """
    # 1. CLASSIFY BY %GRR:
    if result.total_grr < grr_threshold_accept:
        level = AcceptanceLevel.ACCEPTABLE
    elif result.total_grr <= grr_threshold_conditional:
        level = AcceptanceLevel.CONDITIONAL
    else:
        level = AcceptanceLevel.NOT_ACCEPTABLE

    # 2. CHECK NDC:
    ndc_adequate = result.ndc >= min_ndc

    # 3. BUILD REMARKS LIST:
    remarks = []
    remarks.append(f"%GR&R = {result.total_grr:.1f}% — {level.value}")
    
    if level == AcceptanceLevel.ACCEPTABLE:
        remarks.append("Measurement system is suitable for production use.")
    elif level == AcceptanceLevel.CONDITIONAL:
        remarks.append("Engineering review required before production use.")
        dominant = 'repeatability' if result.repeatability > result.reproducibility else 'reproducibility'
        remarks.append(f"Consider investigating {dominant} as the dominant source.")
    else:
        remarks.append("Measurement system must be improved before use.")
        remarks.append("Investigate equipment calibration and operator technique.")
        
    if not ndc_adequate:
        remarks.append(f"NDC = {result.ndc} — below minimum of {min_ndc}. Cannot distinguish part variation.")
    else:
        remarks.append(f"NDC = {result.ndc} — adequate discrimination confirmed.")
        
    remarks.append(f"EV (Repeatability) = {result.repeatability:.4f}")
    remarks.append(f"AV (Reproducibility) = {result.reproducibility:.4f}")

    # 4 & 5. RETURN AcceptanceVerdict
    verdict = AcceptanceVerdict(
        level=level,
        grr_percent=result.total_grr,
        ndc=result.ndc,
        ndc_adequate=ndc_adequate,
        remarks=remarks,
        requires_human_review=(level == AcceptanceLevel.CONDITIONAL)
    )
    
    logger.info("evaluate complete, verdict: %s", level.value)
    return verdict
