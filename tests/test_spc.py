"""Tests for SPC control charts and Nelson rules."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spc.control_charts import (
    ChartData,
    ControlLimits,
    individuals_mr_chart,
    p_chart,
    xbar_r_chart,
)
from spc.nelson_rules import (
    evaluate_all_rules,
    rule_1_beyond_3sigma,
    rule_2_nine_same_side,
    rule_3_six_trending,
    rule_4_fourteen_alternating,
    rule_5_two_of_three_beyond_2sigma,
    rule_6_four_of_five_beyond_1sigma,
    rule_7_fifteen_within_1sigma,
    rule_8_eight_beyond_1sigma,
)


# ─── Control chart tests ────────────────────────────────────────────────────


class TestXbarRChart:
    """Tests for Xbar-R control charts."""

    def test_basic_xbar_r(self) -> None:
        data = pd.DataFrame({
            "subgroup": [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5],
            "value": [
                10.1, 10.2, 10.0,
                10.3, 10.1, 10.2,
                9.9, 10.0, 10.1,
                10.2, 10.1, 10.3,
                10.0, 10.1, 9.9,
            ],
        })
        xbar, r = xbar_r_chart(data)
        assert xbar.limits.ucl > xbar.limits.cl > xbar.limits.lcl
        assert r.limits.ucl > 0
        assert r.limits.lcl == 0  # D3 for n=3 is 0
        assert xbar.chart_type == "xbar"
        assert r.chart_type == "range"

    def test_out_of_control_detected(self) -> None:
        # All in-control except last subgroup which is way out
        rows: list[dict] = []
        for sg in range(1, 11):
            for _ in range(3):
                rows.append({"subgroup": sg, "value": 10.0})
        rows[-1]["value"] = 50.0  # last point massively out
        rows[-2]["value"] = 50.0
        rows[-3]["value"] = 50.0
        xbar, _ = xbar_r_chart(pd.DataFrame(rows))
        assert len(xbar.out_of_control) > 0

    def test_inconsistent_subgroup_size_raises(self) -> None:
        data = pd.DataFrame({
            "subgroup": [1, 1, 2, 2, 2],
            "value": [10.0, 10.1, 10.0, 10.1, 10.2],
        })
        with pytest.raises(ValueError, match="Inconsistent subgroup sizes"):
            xbar_r_chart(data)

    def test_unsupported_subgroup_size_raises(self) -> None:
        data = pd.DataFrame({
            "subgroup": [1] * 11,
            "value": [float(i) for i in range(11)],
        })
        with pytest.raises(ValueError, match="not supported"):
            xbar_r_chart(data)


# ─── p-chart tests ──────────────────────────────────────────────────────────


class TestPChart:
    """Tests for p-charts."""

    def test_basic_p_chart(self) -> None:
        counts = [2, 3, 1, 4, 2]
        sizes = [50, 50, 50, 50, 50]
        chart = p_chart(counts, sizes)
        assert chart.chart_type == "p"
        assert chart.limits.ucl > chart.limits.cl >= chart.limits.lcl
        assert len(chart.points) == 5
        assert all(0 <= p <= 1 for p in chart.points)

    def test_p_chart_detects_high_defect_rate(self) -> None:
        counts = [2, 2, 2, 2, 40]
        sizes = [100, 100, 100, 100, 100]
        chart = p_chart(counts, sizes)
        assert len(chart.out_of_control) > 0


# ─── Individual-MR chart tests ──────────────────────────────────────────────


class TestIMRChart:
    """Tests for Individual-Moving Range charts."""

    def test_basic_imr(self) -> None:
        values = [10.1, 10.2, 10.0, 10.3, 10.1, 10.2, 9.9, 10.0, 10.1, 10.2]
        i_chart, mr_chart = individuals_mr_chart(values)
        assert i_chart.limits.ucl > i_chart.limits.cl > i_chart.limits.lcl
        assert mr_chart.limits.lcl == 0
        assert i_chart.chart_type == "individuals"

    def test_outlier_detected(self) -> None:
        values = [10.0] * 25
        values[12] = 99.0  # massive outlier
        i_chart, _ = individuals_mr_chart(values)
        assert 12 in i_chart.out_of_control


# ─── Nelson rules tests ─────────────────────────────────────────────────────


class TestNelsonRules:
    """Tests for Nelson rule violation detection."""

    def test_rule_1_detects_outlier(self) -> None:
        values = np.array([10.0] * 20)
        values[10] = 100.0
        violations = rule_1_beyond_3sigma(values, cl=10.0, sigma=1.0)
        assert 10 in violations

    def test_rule_1_no_false_positive(self) -> None:
        # All points exactly on the centre line — zero violations
        values = np.array([10.0] * 30)
        violations = rule_1_beyond_3sigma(values, cl=10.0, sigma=1.0)
        assert violations == []

    def test_rule_2_detects_shift(self) -> None:
        # 9 points above centre line
        values = np.array([10.0] * 5 + [11.0] * 9 + [10.0] * 5)
        violations = rule_2_nine_same_side(values, cl=10.0)
        assert len(violations) > 0

    def test_rule_3_detects_trend(self) -> None:
        # 6 steadily increasing points
        values = np.array(
            [10.0, 10.1, 10.2, 10.3, 10.4, 10.5] + [10.0] * 10
        )
        violations = rule_3_six_trending(values)
        assert len(violations) > 0

    def test_rule_4_detects_alternating(self) -> None:
        values = np.array(
            [10.0 + (0.5 if i % 2 == 0 else -0.5) for i in range(20)]
        )
        violations = rule_4_fourteen_alternating(values)
        assert len(violations) > 0

    def test_rule_4_ignores_flat_segments(self) -> None:
        values = np.array([10.0, 11.0, 11.0, 10.0] * 5, dtype=float)
        violations = rule_4_fourteen_alternating(values)
        assert violations == []

    def test_rule_5_detects_two_of_three_beyond_2sigma(self) -> None:
        values = np.array([10.0, 10.0, 13.0, 13.0, 10.0])
        violations = rule_5_two_of_three_beyond_2sigma(values, cl=10.0, sigma=1.0)
        assert len(violations) > 0

    def test_rule_6_detects_four_of_five_beyond_1sigma(self) -> None:
        values = np.array([10.0, 11.5, 11.6, 11.4, 11.3, 10.0])
        violations = rule_6_four_of_five_beyond_1sigma(values, cl=10.0, sigma=1.0)
        assert len(violations) > 0

    def test_rule_7_detects_stratification(self) -> None:
        values = np.array([10.0 + 0.1 * (i % 3 - 1) for i in range(20)])
        violations = rule_7_fifteen_within_1sigma(values, cl=10.0, sigma=1.0)
        assert len(violations) > 0

    def test_rule_8_detects_mixture(self) -> None:
        values = np.array(
            [8.0, 12.0, 8.0, 12.0, 8.0, 12.0, 8.0, 12.0, 10.0]
        )
        violations = rule_8_eight_beyond_1sigma(values, cl=10.0, sigma=1.0)
        assert len(violations) > 0

    def test_evaluate_all_returns_all_keys(self) -> None:
        values = np.random.normal(10.0, 1.0, 50)
        result = evaluate_all_rules(values, cl=10.0, sigma=1.0)
        for rule in [
            "rule_1", "rule_2", "rule_3", "rule_4",
            "rule_5", "rule_6", "rule_7", "rule_8",
        ]:
            assert rule in result
            assert isinstance(result[rule], list)

    def test_false_positive_rate(self) -> None:
        # Nelson rules on chart points with chart limits (same as API).
        rng = np.random.default_rng(42)
        trigger_count = 0
        n_trials = 1000
        for _ in range(n_trials):
            rows = []
            for sg in range(15):
                for _ in range(5):
                    rows.append({
                        "subgroup": sg,
                        "value": float(rng.normal(10.0, 0.1)),
                    })
            xbar, _ = xbar_r_chart(pd.DataFrame(rows))
            result = evaluate_all_rules(
                np.array(xbar.points),
                xbar.limits.cl,
                xbar.limits.sigma,
            )
            if any(len(v) > 0 for v in result.values()):
                trigger_count += 1
        false_positive_rate = trigger_count / n_trials
        assert false_positive_rate < 0.10, (
            f"Too many false positives: {false_positive_rate:.1%}"
        )
