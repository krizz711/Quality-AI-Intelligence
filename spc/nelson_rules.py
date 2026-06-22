"""
Nelson Rules — Eight tests for special-cause variation detection.

Each rule returns a list of indices where the rule is violated.
Reference: Lloyd S. Nelson, "The Shewhart Control Chart—Tests for Special Causes",
           Journal of Quality Technology, 1984.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def rule_1_beyond_3sigma(values: np.ndarray, cl: float, sigma: float) -> list[int]:
    """Rule 1: One point beyond 3σ from the center line."""
    return np.where(np.abs(values - cl) > 3 * sigma)[0].tolist()


def rule_2_nine_same_side(values: np.ndarray, cl: float) -> list[int]:
    """Rule 2: Nine consecutive points on the same side of the center line."""
    above = values > cl
    below = values < cl
    violations: list[int] = []
    for i in range(8, len(values)):
        window = slice(i - 8, i + 1)  # 9 points
        if all(above[window]) or all(below[window]):
            violations.append(i)
    return violations


def rule_3_six_trending(values: np.ndarray) -> list[int]:
    """Rule 3: Six consecutive points steadily increasing or decreasing."""
    violations: list[int] = []
    for i in range(5, len(values)):
        window = values[i - 5 : i + 1]  # 6 points
        diffs = np.diff(window)
        if all(diffs > 0) or all(diffs < 0):
            violations.append(i)
    return violations


def rule_4_fourteen_alternating(values: np.ndarray) -> list[int]:
    """Rule 4: Fourteen consecutive points alternating up and down."""
    violations: list[int] = []
    for i in range(13, len(values)):
        window = values[i - 13 : i + 1]
        diffs = np.diff(window)
        # Flat segments are not alternating; compare raw diffs, not np.sign.
        if np.any(diffs == 0):
            continue
        if np.all(diffs[:-1] * diffs[1:] < 0):
            violations.append(i)
    return violations


def rule_5_two_of_three_beyond_2sigma(
    values: np.ndarray, cl: float, sigma: float
) -> list[int]:
    """Rule 5: Two of three consecutive points beyond 2σ (same side)."""
    violations: list[int] = []
    for i in range(2, len(values)):
        window = values[i - 2 : i + 1]
        above = int(np.sum(window > cl + 2 * sigma))
        below = int(np.sum(window < cl - 2 * sigma))
        if above >= 2 or below >= 2:
            violations.append(i)
    return violations


def rule_6_four_of_five_beyond_1sigma(
    values: np.ndarray, cl: float, sigma: float
) -> list[int]:
    """Rule 6: Four of five consecutive points beyond 1σ (same side)."""
    violations: list[int] = []
    for i in range(4, len(values)):
        window = values[i - 4 : i + 1]
        above = int(np.sum(window > cl + sigma))
        below = int(np.sum(window < cl - sigma))
        if above >= 4 or below >= 4:
            violations.append(i)
    return violations


def rule_7_fifteen_within_1sigma(
    values: np.ndarray, cl: float, sigma: float
) -> list[int]:
    """Rule 7: Fifteen consecutive points within 1σ of center line (stratification)."""
    violations: list[int] = []
    for i in range(14, len(values)):
        window = values[i - 14 : i + 1]  # 15 points
        if all(np.abs(window - cl) < sigma):
            violations.append(i)
    return violations


def rule_8_eight_beyond_1sigma(
    values: np.ndarray, cl: float, sigma: float
) -> list[int]:
    """Rule 8: Eight consecutive points beyond 1σ (on either side — mixture)."""
    violations: list[int] = []
    for i in range(7, len(values)):
        window = values[i - 7 : i + 1]  # 8 points
        if all(np.abs(window - cl) > sigma):
            violations.append(i)
    return violations


def evaluate_all_rules(
    values: np.ndarray, cl: float, sigma: float
) -> dict[str, list[int]]:
    """
    Run all eight Nelson rules and return a dict mapping rule names
    to lists of violating indices.
    """
    results = {
        "rule_1": rule_1_beyond_3sigma(values, cl, sigma),
        "rule_2": rule_2_nine_same_side(values, cl),
        "rule_3": rule_3_six_trending(values),
        "rule_4": rule_4_fourteen_alternating(values),
        "rule_5": rule_5_two_of_three_beyond_2sigma(values, cl, sigma),
        "rule_6": rule_6_four_of_five_beyond_1sigma(values, cl, sigma),
        "rule_7": rule_7_fifteen_within_1sigma(values, cl, sigma),
        "rule_8": rule_8_eight_beyond_1sigma(values, cl, sigma),
    }
    total = sum(len(v) for v in results.values())
    logger.info(
        "evaluate_all_rules — %d total violations across 8 rules", total,
    )
    return results
