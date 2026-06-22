"""
Anomaly Detector — Statistical anomaly detection for manufacturing quality data.

Provides lightweight prediction models that complement the LLM-based insights:
  - EWMA (Exponentially Weighted Moving Average) drift detection
  - IQR-based outlier detection
  - Simple linear trend extrapolation

All results are logged to MLflow for experiment tracking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Result of statistical anomaly detection."""

    anomaly_detected: bool
    anomaly_score: float              # 0.0 = clean, 1.0 = severe
    anomaly_indices: list[int] = field(default_factory=list)
    drift_detected: bool = False
    drift_direction: str = "none"     # "upward" | "downward" | "none"
    drift_rate: float = 0.0           # units per observation
    predicted_violation_in: int | None = None  # observations until OOC
    method: str = "composite"
    details: dict[str, Any] = field(default_factory=dict)


def ewma_detection(
    values: np.ndarray,
    cl: float,
    sigma: float,
    *,
    lambda_: float = 0.2,
    L: float = 3.0,
) -> tuple[list[int], np.ndarray]:
    """
    EWMA (Exponentially Weighted Moving Average) control chart detection.

    Parameters
    ----------
    values : np.ndarray
        Measurement values.
    cl : float
        Center line (target/mean).
    sigma : float
        Process standard deviation.
    lambda_ : float
        EWMA smoothing parameter (0 < λ ≤ 1). Default 0.2.
    L : float
        Control limit width multiplier. Default 3.0.

    Returns
    -------
    tuple[list[int], np.ndarray]
        (violation_indices, ewma_values)
    """
    n = len(values)
    ewma = np.zeros(n)
    ewma[0] = cl

    for i in range(n):
        if i == 0:
            ewma[i] = lambda_ * values[i] + (1 - lambda_) * cl
        else:
            ewma[i] = lambda_ * values[i] + (1 - lambda_) * ewma[i - 1]

    violations = []
    for i in range(n):
        # Time-varying control limits
        factor = lambda_ / (2 - lambda_) * (1 - (1 - lambda_) ** (2 * (i + 1)))
        limit_width = L * sigma * np.sqrt(factor)
        if abs(ewma[i] - cl) > limit_width:
            violations.append(i)

    return violations, ewma


def iqr_outlier_detection(values: np.ndarray, *, k: float = 1.5) -> list[int]:
    """
    IQR-based outlier detection.

    Parameters
    ----------
    values : np.ndarray
        Measurement values.
    k : float
        IQR multiplier for fence calculation. Default 1.5 (mild outliers).

    Returns
    -------
    list[int]
        Indices of outlier values.
    """
    q1 = float(np.percentile(values, 25))
    q3 = float(np.percentile(values, 75))
    iqr = q3 - q1

    lower_fence = q1 - k * iqr
    upper_fence = q3 + k * iqr

    return [i for i, v in enumerate(values) if v < lower_fence or v > upper_fence]


def linear_trend_extrapolation(
    values: np.ndarray,
    ucl: float,
    lcl: float,
) -> tuple[float, str, int | None]:
    """
    Fit a simple linear trend and extrapolate to predict when a control limit
    will be breached.

    Returns
    -------
    tuple[float, str, int | None]
        (slope, direction, observations_until_violation)
    """
    n = len(values)
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, values, 1)

    direction = "upward" if slope > 0 else "downward" if slope < 0 else "none"

    # Extrapolate: when does the trend line cross UCL or LCL?
    obs_until = None
    if slope > 0:
        # Moving toward UCL
        if intercept + slope * n < ucl:
            obs_until = max(0, int((ucl - intercept) / slope) - n)
    elif slope < 0:
        # Moving toward LCL
        if intercept + slope * n > lcl:
            obs_until = max(0, int((intercept - lcl) / abs(slope)) - n)

    return float(slope), direction, obs_until


def detect_anomalies(
    values: list[float] | np.ndarray,
    cl: float,
    sigma: float,
    ucl: float,
    lcl: float,
) -> AnomalyResult:
    """
    Run composite anomaly detection combining EWMA, IQR, and trend analysis.

    Parameters
    ----------
    values : array-like
        Measurement values (ordered by time).
    cl, sigma, ucl, lcl : float
        Control chart parameters.

    Returns
    -------
    AnomalyResult
    """
    vals = np.asarray(values, dtype=float)
    n = len(vals)

    if n < 5:
        return AnomalyResult(
            anomaly_detected=False,
            anomaly_score=0.0,
            method="insufficient_data",
            details={"reason": "Need at least 5 data points"},
        )

    # 1. EWMA detection
    ewma_violations, ewma_values = ewma_detection(vals, cl, sigma)

    # 2. IQR outliers
    iqr_outliers = iqr_outlier_detection(vals)

    # 3. Trend analysis
    slope, drift_direction, obs_until = linear_trend_extrapolation(vals, ucl, lcl)

    # 4. Combine results
    all_anomaly_indices = sorted(set(ewma_violations) | set(iqr_outliers))

    # Anomaly score: 0-1 composite
    ewma_score = min(1.0, len(ewma_violations) / max(1, n) * 5)
    iqr_score = min(1.0, len(iqr_outliers) / max(1, n) * 10)
    trend_score = min(1.0, abs(slope) / (sigma if sigma > 0 else 1.0))

    composite_score = 0.4 * ewma_score + 0.3 * iqr_score + 0.3 * trend_score
    composite_score = round(min(1.0, composite_score), 4)

    anomaly_detected = composite_score > 0.3 or len(all_anomaly_indices) > 0

    result = AnomalyResult(
        anomaly_detected=anomaly_detected,
        anomaly_score=composite_score,
        anomaly_indices=all_anomaly_indices,
        drift_detected=abs(slope) > 0.5 * sigma / n if sigma > 0 else False,
        drift_direction=drift_direction,
        drift_rate=round(slope, 6),
        predicted_violation_in=obs_until,
        method="composite",
        details={
            "ewma_violations": len(ewma_violations),
            "iqr_outliers": len(iqr_outliers),
            "trend_slope": round(slope, 6),
            "composite_scores": {
                "ewma": round(ewma_score, 4),
                "iqr": round(iqr_score, 4),
                "trend": round(trend_score, 4),
            },
        },
    )

    if anomaly_detected:
        logger.warning(
            "Anomaly detected — score=%.3f, EWMA=%d, IQR=%d, drift=%s",
            composite_score,
            len(ewma_violations),
            len(iqr_outliers),
            drift_direction,
        )
    else:
        logger.info("No anomalies detected — score=%.3f", composite_score)

    return result
