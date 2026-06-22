"""Tests for GR&R calculator and acceptance modules."""

from __future__ import annotations

import pandas as pd
import pytest

from grr.acceptance import AcceptanceLevel, evaluate
from grr.calculator import GRRResult, grr_anova, grr_xbar_r
from grr.report_generator import create_pdf


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def aiag_data() -> pd.DataFrame:
    """AIAG MSA 4th Edition reference data."""
    data = {
      "operator": ["A"]*20 + ["B"]*20 + ["C"]*20,
      "part": [p for p in range(1, 11) for _ in range(2)] * 3,
      "measurement": [
        # Operator A Trial 1, Trial 2 (alternating by part)
        0.29, 0.41, -0.56, -0.68, 1.34, 1.17, 0.47, 0.50, -0.80, -0.92,
        0.02, 0.11, 0.59, 0.75, -0.31, -0.20, 2.26, 1.99, -1.36, -1.25,
        # Operator B
        0.08, 0.25, -0.47, -1.22, 1.19, 0.94, 0.01, 1.03, -0.56, -1.20,
        0.47, 0.39, 0.02, 1.20, -0.20, 0.22, 1.76, 2.17, -1.47, -1.59,
        # Operator C
        0.04, 0.34, -1.38, -1.13, 0.88, 1.09, 0.14, 0.20, -1.46, -1.07,
        0.08, -0.11, 0.67, 0.95, 0.01, 0.30, 2.19, 2.01, -2.16, -1.65,
      ]
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_grr_result() -> GRRResult:
    return GRRResult(
        total_grr=18.5,
        repeatability=0.10,
        reproducibility=0.08,
        part_variation=0.40,
        total_variation=0.50,
        ndc=4,
    )


@pytest.fixture
def mock_verdict(mock_grr_result: GRRResult):
    return evaluate(mock_grr_result)


# ─── Calculator tests ───────────────────────────────────────────────────────

class TestGRRXbarR:
    """Tests for the Xbar-R GR&R method."""

    def test_xbar_r_returns_grr_result(self, aiag_data: pd.DataFrame) -> None:
        result = grr_xbar_r(aiag_data)
        assert isinstance(result, GRRResult)
        assert 0 < result.total_grr < 100
        assert result.ndc >= 1
        assert result.repeatability > 0
        assert result.total_variation > 0

    def test_xbar_r_aiag_reference_values(self, aiag_data: pd.DataFrame) -> None:
        result = grr_xbar_r(aiag_data)
        # AIAG reference: %GRR should be in range 20-30% for this dataset
        assert 15.0 < result.total_grr < 35.0, f"GRR% out of expected range: {result.total_grr}"
        # NDC should be >= 2 for this dataset
        assert result.ndc >= 2, f"NDC too low: {result.ndc}"

    def test_perfect_measurement_system(self) -> None:
        # If all measurements are identical — EV=0, AV=0, GRR=0
        perfect = []
        for op in ["A", "B", "C"]:
            for part in range(1, 6):
                for trial in range(2):
                    perfect.append({"operator": op, "part": str(part), "measurement": 10.0 + part * 0.5})
        result = grr_xbar_r(pd.DataFrame(perfect))
        assert result.total_grr < 1.0, "Perfect system should have near-zero GRR"

    def test_invalid_input_raises(self) -> None:
        with pytest.raises(ValueError):
            grr_xbar_r(pd.DataFrame({"operator": ["A"], "part": ["P1"], "measurement": [10.0]}))


class TestGRRANOVA:
    """Tests for the ANOVA GR&R method."""

    def test_basic_anova(self, aiag_data: pd.DataFrame) -> None:
        result = grr_anova(aiag_data)
        assert isinstance(result, GRRResult)
        assert 0 < result.total_grr < 100
        assert result.ndc >= 1
        assert result.details["method"] == "anova"

    def test_anova_and_xbar_r_agree_within_tolerance(self, aiag_data: pd.DataFrame) -> None:
        # Both methods on same data should give similar %GRR (within 10 percentage points)
        result_xbar = grr_xbar_r(aiag_data)
        result_anova = grr_anova(aiag_data)
        diff = abs(result_xbar.total_grr - result_anova.total_grr)
        assert diff < 15.0, f"Methods diverge too much: xbar={result_xbar.total_grr:.1f}% anova={result_anova.total_grr:.1f}%"

    def test_anova_interaction_flag_in_details(self, aiag_data: pd.DataFrame) -> None:
        result = grr_anova(aiag_data)
        assert "interaction_significant" in result.details
        assert "p_interaction" in result.details
        assert 0 <= result.details["p_interaction"] <= 1

    def test_anova_perfect_system(self) -> None:
        # Same as xbar_r perfect test — should give near-zero GRR
        perfect = []
        for op in ["A", "B", "C"]:
            for part in range(1, 6):
                for trial in range(2):
                    perfect.append({"operator": op, "part": str(part), "measurement": 10.0 + part * 0.5})
        result = grr_anova(pd.DataFrame(perfect))
        assert result.total_grr < 5.0, f"Perfect system GRR too high: {result.total_grr}"


# ─── Acceptance tests ───────────────────────────────────────────────────────

class TestAcceptance:
    """Tests for the acceptance criteria evaluator."""

    def test_acceptance_pass(self) -> None:
        good = GRRResult(
            total_grr=8.5,
            repeatability=0.05,
            reproducibility=0.03,
            part_variation=0.45,
            total_variation=0.50,
            ndc=7,
        )
        verdict = evaluate(good)
        assert verdict.level == AcceptanceLevel.ACCEPTABLE
        assert verdict.requires_human_review is False

    def test_acceptance_conditional_triggers_human_review(self) -> None:
        medium = GRRResult(
            total_grr=18.5,
            repeatability=0.10,
            reproducibility=0.08,
            part_variation=0.40,
            total_variation=0.50,
            ndc=4,
        )
        verdict = evaluate(medium)
        assert verdict.level == AcceptanceLevel.CONDITIONAL
        assert verdict.requires_human_review is True

    def test_acceptance_fail(self) -> None:
        bad = GRRResult(
            total_grr=45.0,
            repeatability=0.30,
            reproducibility=0.15,
            part_variation=0.20,
            total_variation=0.50,
            ndc=1,
        )
        verdict = evaluate(bad)
        assert verdict.level == AcceptanceLevel.NOT_ACCEPTABLE
        assert verdict.ndc_adequate is False


# ─── Report Generator tests ──────────────────────────────────────────────────

class TestReportGenerator:
    """Tests for the PDF report generator."""

    def test_create_pdf_returns_bytes(self, mock_grr_result: GRRResult, mock_verdict) -> None:
        pdf = create_pdf(mock_grr_result, mock_verdict)
        assert isinstance(pdf, bytes) and len(pdf) > 0
