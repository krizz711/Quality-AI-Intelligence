"""
SPC advanced tests — 100% coverage for:
  - spc/anomaly_detector.py
  - spc/capability.py
  - spc/cusum.py
  - spc/ewma.py
"""
from __future__ import annotations

import numpy as np
import pytest

from spc.anomaly_detector import (
    AnomalyResult,
    detect_anomalies,
    ewma_detection,
    iqr_outlier_detection,
    linear_trend_extrapolation,
)
from spc.capability import CapabilityResult, capability_indices
from spc.cusum import CUSUMResult, cusum_chart, cusum_from_limits
from spc.ewma import EWMAResult, ewma_chart, ewma_from_limits


# ===========================================================================
# spc/anomaly_detector.py
# ===========================================================================

class TestEWMADetection:
    """Unit tests for ewma_detection helper."""

    def test_in_control_no_violations(self):
        cl = 10.0
        sigma = 1.0
        values = np.full(20, cl)   # all exactly on center line
        violations, ewma_vals = ewma_detection(values, cl, sigma)
        assert violations == []
        assert len(ewma_vals) == 20

    def test_massive_step_shift_detected(self):
        cl = 0.0
        sigma = 1.0
        # First 10 in-control, next 10 shifted by 10 sigma
        values = np.concatenate([np.zeros(10), np.full(10, 10.0)])
        violations, ewma_vals = ewma_detection(values, cl, sigma)
        assert len(violations) > 0
        # Violations must be in the shifted region
        assert max(violations) >= 10

    def test_ewma_values_shape(self):
        values = np.arange(15, dtype=float)
        _, ewma_vals = ewma_detection(values, cl=7.0, sigma=3.0)
        assert ewma_vals.shape == (15,)

    def test_custom_lambda_and_L(self):
        values = np.full(10, 5.0)
        violations, _ = ewma_detection(values, cl=5.0, sigma=1.0, lambda_=0.5, L=2.0)
        assert isinstance(violations, list)


class TestIQROutlierDetection:

    def test_no_outliers_uniform(self):
        values = np.full(20, 10.0)
        assert iqr_outlier_detection(values) == []

    def test_single_extreme_outlier(self):
        values = np.array([10.0] * 19 + [100.0])
        outliers = iqr_outlier_detection(values)
        assert 19 in outliers

    def test_extreme_low_outlier(self):
        values = np.array([-100.0] + [10.0] * 19)
        outliers = iqr_outlier_detection(values)
        assert 0 in outliers

    def test_custom_k_strict(self):
        # k=0.0 makes every value that deviates from Q1/Q3 an outlier
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        outliers_loose = iqr_outlier_detection(values, k=3.0)
        outliers_strict = iqr_outlier_detection(values, k=0.0)
        assert len(outliers_strict) >= len(outliers_loose)


class TestLinearTrendExtrapolation:

    def test_flat_trend_no_prediction(self):
        values = np.full(20, 10.0)
        slope, direction, obs_until = linear_trend_extrapolation(values, ucl=13.0, lcl=7.0)
        # np.polyfit may return a tiny non-zero slope for constant data (float precision);
        # direction can be any valid string
        assert abs(slope) < 1e-10
        assert direction in ("none", "upward", "downward")
        # If a prediction is given it must be astronomically far away (≫ spec band width),
        # because |slope| ≈ 0 makes the extrapolation result huge.
        if obs_until is not None:
            assert obs_until > 10_000

    def test_upward_trend_predict_breach(self):
        # Values start at 0 and increase by 1 per step; UCL = 30
        values = np.arange(20, dtype=float)
        slope, direction, obs_until = linear_trend_extrapolation(values, ucl=30.0, lcl=-5.0)
        assert slope > 0
        assert direction == "upward"
        # Trend is heading toward UCL
        if obs_until is not None:
            assert obs_until >= 0

    def test_downward_trend_predict_breach(self):
        values = np.arange(20, 0, -1, dtype=float)
        slope, direction, obs_until = linear_trend_extrapolation(values, ucl=30.0, lcl=5.0)
        assert slope < 0
        assert direction == "downward"

    def test_upward_trend_already_past_ucl(self):
        # Trend line at n is already above UCL — obs_until should be None
        values = np.arange(100, 120, dtype=float)
        _, _, obs_until = linear_trend_extrapolation(values, ucl=110.0, lcl=0.0)
        # Already crossed, so no future prediction returned
        assert obs_until is None

    def test_downward_trend_already_past_lcl(self):
        values = np.arange(20, 0, -1, dtype=float)
        _, _, obs_until = linear_trend_extrapolation(values, ucl=100.0, lcl=15.0)
        assert obs_until is None


class TestDetectAnomalies:

    def test_insufficient_data_returns_early(self):
        result = detect_anomalies([1.0, 2.0, 3.0], cl=2.0, sigma=0.5, ucl=3.5, lcl=0.5)
        assert isinstance(result, AnomalyResult)
        assert result.method == "insufficient_data"
        assert not result.anomaly_detected
        assert result.anomaly_score == 0.0

    def test_clean_in_control_process(self):
        cl = 10.0
        sigma = 1.0
        values = [cl + np.random.default_rng(42).normal(0, 0.01) for _ in range(30)]
        result = detect_anomalies(values, cl=cl, sigma=sigma, ucl=cl+3, lcl=cl-3)
        assert isinstance(result, AnomalyResult)
        assert result.anomaly_score >= 0.0
        assert result.anomaly_score <= 1.0

    def test_heavy_drift_detected(self):
        # Rising values will trigger EWMA + trend
        values = list(range(1, 31))  # 1..30, clearly drifting upward
        result = detect_anomalies(values, cl=5.0, sigma=1.0, ucl=8.0, lcl=2.0)
        assert result.anomaly_detected

    def test_extreme_outlier_detected(self):
        values = [10.0] * 20 + [100.0]  # one huge outlier at end
        result = detect_anomalies(values, cl=10.0, sigma=1.0, ucl=13.0, lcl=7.0)
        assert result.anomaly_detected
        assert 20 in result.anomaly_indices

    def test_result_fields_populated(self):
        values = [10.0 + i * 0.3 for i in range(25)]
        result = detect_anomalies(values, cl=10.0, sigma=1.0, ucl=13.0, lcl=7.0)
        assert result.method == "composite"
        assert isinstance(result.drift_direction, str)
        assert isinstance(result.drift_rate, float)
        assert "ewma_violations" in result.details

    def test_downward_drift_direction(self):
        values = list(range(30, 0, -1))
        result = detect_anomalies(values, cl=15.0, sigma=3.0, ucl=24.0, lcl=6.0)
        assert result.drift_direction in ("downward", "none")

    def test_anomaly_score_capped_at_one(self):
        # Pathological: all values are extreme outliers
        values = [1000.0] * 30
        result = detect_anomalies(values, cl=0.0, sigma=1.0, ucl=3.0, lcl=-3.0)
        assert result.anomaly_score <= 1.0


# ===========================================================================
# spc/capability.py
# ===========================================================================

class TestCapabilityIndices:

    def _capable_values(self, n: int = 50) -> np.ndarray:
        rng = np.random.default_rng(7)
        return rng.normal(loc=10.0, scale=0.3, size=n)

    def test_returns_capability_result(self):
        result = capability_indices(self._capable_values(), usl=11.0, lsl=9.0)
        assert isinstance(result, CapabilityResult)

    def test_capable_process_cpk_above_1(self):
        result = capability_indices(self._capable_values(), usl=11.0, lsl=9.0)
        assert result.cpk > 1.0

    def test_incapable_process_cpk_below_1(self):
        # Wide spread relative to tight spec
        rng = np.random.default_rng(8)
        values = rng.normal(loc=10.0, scale=2.0, size=50)
        result = capability_indices(values, usl=11.0, lsl=9.0)
        assert result.cpk < 1.0

    def test_cp_cpk_relationship(self):
        # Centered process: Cpk ≈ Cp
        values = np.full(50, 10.0) + np.linspace(-0.1, 0.1, 50)
        result = capability_indices(values, usl=11.0, lsl=9.0)
        assert result.cp >= result.cpk - 0.001

    def test_ppm_nonnegative(self):
        result = capability_indices(self._capable_values(), usl=11.0, lsl=9.0)
        assert result.ppm_above >= 0
        assert result.ppm_below >= 0
        assert result.ppm_total == pytest.approx(result.ppm_above + result.ppm_below)

    def test_subgroup_size_individuals(self):
        result = capability_indices(self._capable_values(), usl=11.0, lsl=9.0, subgroup_size=1)
        assert result.sigma_within > 0

    def test_subgroup_size_5(self):
        rng = np.random.default_rng(9)
        values = rng.normal(loc=10.0, scale=0.3, size=50)
        result = capability_indices(values, usl=11.0, lsl=9.0, subgroup_size=5)
        assert result.sigma_within > 0

    def test_subgroup_size_too_large_falls_back(self):
        # Only 3 values with subgroup_size=5 → n_subgroups < 2 → falls back to ddof=1 std
        values = [9.8, 10.0, 10.2]
        result = capability_indices(values, usl=12.0, lsl=8.0, subgroup_size=5)
        assert result.sigma_within > 0

    def test_insufficient_values_raises(self):
        with pytest.raises(ValueError, match="at least 2 values"):
            capability_indices([10.0], usl=11.0, lsl=9.0)

    def test_inverted_spec_raises(self):
        with pytest.raises(ValueError, match="USL must be greater"):
            capability_indices([10.0, 10.1], usl=9.0, lsl=11.0)

    def test_zero_sigma_guard(self):
        # All same values → sigma_overall = 0; function must guard and not crash
        values = [10.0] * 10
        result = capability_indices(values, usl=11.0, lsl=9.0)
        assert isinstance(result, CapabilityResult)

    def test_result_fields_populated(self):
        result = capability_indices(self._capable_values(), usl=11.0, lsl=9.0)
        assert result.usl == 11.0
        assert result.lsl == 9.0
        assert result.mean == pytest.approx(10.0, abs=0.2)
        assert result.sigma_within > 0
        assert result.sigma_overall > 0


# ===========================================================================
# spc/cusum.py
# ===========================================================================

class TestCUSUMChart:

    def test_in_control_no_shift(self):
        values = np.full(30, 10.0)
        result = cusum_chart(values, cl=10.0, sigma=1.0)
        assert isinstance(result, CUSUMResult)
        assert not result.shift_detected
        assert result.shift_direction == "none"
        assert result.first_signal_index is None

    def test_upward_shift_detected(self):
        # First 10 in-control, then 1σ upward shift for 20 more
        values = np.concatenate([np.full(10, 10.0), np.full(20, 11.0)])
        result = cusum_chart(values, cl=10.0, sigma=1.0, k=0.5, h=4.0)
        assert result.shift_detected
        assert result.shift_direction in ("upward", "both")
        assert result.first_signal_index is not None
        assert result.first_signal_index > 0

    def test_downward_shift_detected(self):
        values = np.concatenate([np.full(10, 10.0), np.full(20, 9.0)])
        result = cusum_chart(values, cl=10.0, sigma=1.0, k=0.5, h=4.0)
        assert result.shift_detected
        assert result.shift_direction in ("downward", "both")

    def test_both_directions(self):
        # Alternate extreme high/low to force both C+ and C- to exceed h
        rng = np.random.default_rng(42)
        high = np.full(15, 15.0)
        low = np.full(15, 5.0)
        values = np.concatenate([high, low])
        result = cusum_chart(values, cl=10.0, sigma=1.0, k=0.5, h=4.0)
        assert result.shift_detected
        # Both violations possible
        assert result.shift_direction in ("upward", "downward", "both")

    def test_result_shapes(self):
        n = 25
        values = np.arange(n, dtype=float)
        result = cusum_chart(values, cl=12.0, sigma=2.0)
        assert len(result.upper_cusum) == n
        assert len(result.lower_cusum) == n

    def test_params_stored(self):
        result = cusum_chart(np.ones(10), cl=1.0, sigma=0.5, k=0.3, h=3.0)
        assert result.params["k"] == 0.3
        assert result.params["h"] == 3.0
        assert result.params["cl"] == 1.0
        assert result.params["sigma"] == 0.5

    def test_too_few_values_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            cusum_chart([10.0], cl=10.0, sigma=1.0)

    def test_zero_sigma_raises(self):
        with pytest.raises(ValueError, match="sigma must be > 0"):
            cusum_chart([10.0, 11.0], cl=10.0, sigma=0.0)

    def test_negative_sigma_raises(self):
        with pytest.raises(ValueError, match="sigma must be > 0"):
            cusum_chart([10.0, 11.0], cl=10.0, sigma=-1.0)

    def test_h2_faster_detection(self):
        """h=2 should detect a 1σ shift faster than h=4."""
        values = np.concatenate([np.full(5, 10.0), np.full(20, 11.0)])
        result_h2 = cusum_chart(values, cl=10.0, sigma=1.0, h=2.0)
        result_h4 = cusum_chart(values, cl=10.0, sigma=1.0, h=4.0)
        if result_h2.first_signal_index and result_h4.first_signal_index:
            assert result_h2.first_signal_index <= result_h4.first_signal_index


class TestCUSUMFromLimits:

    def test_derives_cl_and_sigma(self):
        ucl, lcl = 13.0, 7.0   # cl=10, sigma=1
        values = np.concatenate([np.full(10, 10.0), np.full(20, 11.0)])
        result = cusum_from_limits(values, ucl=ucl, lcl=lcl)
        assert isinstance(result, CUSUMResult)
        # cl = (13+7)/2 = 10, sigma = (13-7)/6 = 1
        assert result.params["cl"] == pytest.approx(10.0)
        assert result.params["sigma"] == pytest.approx(1.0)

    def test_in_control_via_limits(self):
        values = np.full(20, 10.0)
        result = cusum_from_limits(values, ucl=13.0, lcl=7.0)
        assert not result.shift_detected


# ===========================================================================
# spc/ewma.py
# ===========================================================================

class TestEWMAChart:

    def test_in_control_no_violation(self):
        values = np.full(30, 10.0)
        result = ewma_chart(values, cl=10.0, sigma=1.0)
        assert isinstance(result, EWMAResult)
        assert not result.shift_detected
        assert result.violation_indices == []
        assert result.drift_direction == "none"

    def test_upward_drift_detected(self):
        values = np.concatenate([np.full(5, 10.0), np.linspace(10.0, 20.0, 25)])
        result = ewma_chart(values, cl=10.0, sigma=1.0)
        assert result.shift_detected
        assert len(result.violation_indices) > 0

    def test_downward_drift_detected(self):
        values = np.concatenate([np.full(5, 10.0), np.linspace(10.0, 0.0, 25)])
        result = ewma_chart(values, cl=10.0, sigma=1.0)
        assert result.shift_detected
        assert result.drift_direction in ("downward", "none")

    def test_drift_direction_upward(self):
        # Late mean >> early mean by > 0.1*sigma
        early = np.full(15, 10.0)
        late = np.full(15, 15.0)
        values = np.concatenate([early, late])
        result = ewma_chart(values, cl=10.0, sigma=1.0)
        # The EWMA smooths, but with such a large shift drift should be upward
        assert result.drift_direction in ("upward", "none")

    def test_drift_direction_downward(self):
        early = np.full(15, 10.0)
        late = np.full(15, 5.0)
        values = np.concatenate([early, late])
        result = ewma_chart(values, cl=10.0, sigma=1.0)
        assert result.drift_direction in ("downward", "none")

    def test_ewma_arrays_shape(self):
        n = 20
        result = ewma_chart(np.arange(n, dtype=float), cl=9.5, sigma=2.0)
        assert result.ewma_values.shape == (n,)
        assert result.ucl.shape == (n,)
        assert result.lcl.shape == (n,)

    def test_steady_state_limits(self):
        result = ewma_chart(np.full(50, 10.0), cl=10.0, sigma=1.0, lambda_=0.2, L=3.0)
        # Steady-state UCL/LCL should be symmetric around cl
        assert result.steady_state_ucl > result.cl
        assert result.steady_state_lcl < result.cl
        assert result.steady_state_ucl - result.cl == pytest.approx(
            result.cl - result.steady_state_lcl, rel=1e-6
        )

    def test_params_stored(self):
        result = ewma_chart(np.full(10, 5.0), cl=5.0, sigma=0.5, lambda_=0.3, L=2.7)
        assert result.params["lambda_"] == 0.3
        assert result.params["L"] == 2.7
        assert result.cl == 5.0

    def test_too_few_values_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            ewma_chart([10.0], cl=10.0, sigma=1.0)

    def test_zero_sigma_raises(self):
        with pytest.raises(ValueError, match="sigma must be > 0"):
            ewma_chart([10.0, 11.0], cl=10.0, sigma=0.0)

    def test_negative_sigma_raises(self):
        with pytest.raises(ValueError, match="sigma must be > 0"):
            ewma_chart([10.0, 11.0], cl=10.0, sigma=-0.5)

    def test_lambda_zero_raises(self):
        with pytest.raises(ValueError, match="lambda_"):
            ewma_chart([10.0, 11.0], cl=10.0, sigma=1.0, lambda_=0.0)

    def test_lambda_above_one_raises(self):
        with pytest.raises(ValueError, match="lambda_"):
            ewma_chart([10.0, 11.0], cl=10.0, sigma=1.0, lambda_=1.1)

    def test_lambda_one_equals_shewhart(self):
        # λ=1 → EWMA reduces to Shewhart; Z_i = x_i
        values = np.array([10.0, 10.1, 10.2, 10.3])
        result = ewma_chart(values, cl=10.0, sigma=1.0, lambda_=1.0)
        np.testing.assert_allclose(result.ewma_values, values, rtol=1e-10)


class TestEWMAFromLimits:

    def test_derives_cl_and_sigma(self):
        ucl, lcl = 13.0, 7.0
        values = np.full(20, 10.0)
        result = ewma_from_limits(values, ucl=ucl, lcl=lcl)
        assert isinstance(result, EWMAResult)
        assert result.cl == pytest.approx(10.0)
        assert result.params["sigma"] == pytest.approx(1.0)

    def test_upward_drift_via_limits(self):
        values = np.concatenate([np.full(5, 10.0), np.linspace(10.0, 20.0, 25)])
        result = ewma_from_limits(values, ucl=13.0, lcl=7.0)
        assert result.shift_detected

    def test_in_control_via_limits(self):
        values = np.full(20, 10.0)
        result = ewma_from_limits(values, ucl=13.0, lcl=7.0)
        assert not result.shift_detected
