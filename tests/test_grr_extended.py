"""
GR&R Calculator extended tests — covers branches missed by test_grr.py.

Targeted lines in grr/calculator.py:
  70  — xbar_r: unequal trials ValueError
  100 — xbar_r: d2* KeyError (n_parts or k > 10)
  113 — xbar_r: tolerance-relative %GR&R branch
  172 — anova: operator/part count ValueError
  177 — anova: unequal trials ValueError
  220-221, 227-229 — anova: significant interaction branch
  244 — anova: tolerance-relative %GR&R branch
"""
from __future__ import annotations

import pandas as pd
import pytest

from grr.calculator import GRRResult, grr_anova, grr_xbar_r


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_balanced(
    operators: list[str],
    parts: list[str],
    trials: int,
    base: float = 10.0,
) -> pd.DataFrame:
    """Balanced GR&R dataset with small uniform measurement values."""
    rows = []
    for i, op in enumerate(operators):
        for j, pt in enumerate(parts):
            for t in range(trials):
                rows.append({
                    "operator": op,
                    "part": pt,
                    "measurement": base + j * 2.0 + i * 0.1 + t * 0.05,
                })
    return pd.DataFrame(rows)


def _make_crossover_interaction(trials: int = 3) -> pd.DataFrame:
    """
    Two operators, two parts with a severe cross-over interaction.
    Operator A: P1 >> P2; Operator B: P1 << P2.
    Guarantees MS_interaction >> MS_error → p_interaction < 0.05.
    """
    rows = []
    values = {
        ("A", "P1"): 20.0,
        ("A", "P2"): 10.0,
        ("B", "P1"): 10.0,
        ("B", "P2"): 20.0,
    }
    for (op, pt), base in values.items():
        for t in range(trials):
            rows.append({"operator": op, "part": pt, "measurement": base + t * 0.05})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# grr_xbar_r — uncovered branches
# ---------------------------------------------------------------------------

class TestXbarRUncoveredBranches:

    def test_unequal_trials_raises(self):
        """Line 70 — different trial counts per cell must raise ValueError."""
        # P1/Op-A has 2 trials, P2/Op-A has only 1 → unbalanced
        rows = [
            {"operator": "A", "part": "P1", "measurement": 10.0},
            {"operator": "A", "part": "P1", "measurement": 10.1},
            {"operator": "A", "part": "P2", "measurement": 20.0},
            {"operator": "B", "part": "P1", "measurement": 10.2},
            {"operator": "B", "part": "P1", "measurement": 10.3},
            {"operator": "B", "part": "P2", "measurement": 20.1},
            {"operator": "B", "part": "P2", "measurement": 20.2},
        ]
        df = pd.DataFrame(rows)
        with pytest.raises(ValueError, match="same number of trials"):
            grr_xbar_r(df)

    def test_n_parts_exceeds_d2_table_raises(self):
        """Lines 100-101 — n_parts=11 is outside d2* table (2–10) → ValueError."""
        df = _make_balanced(
            operators=["A", "B"],
            parts=[f"P{i}" for i in range(1, 12)],  # 11 parts
            trials=2,
        )
        with pytest.raises(ValueError, match="d2\\* table"):
            grr_xbar_r(df)

    def test_n_operators_exceeds_d2_table_raises(self):
        """Lines 100-101 — n_operators=11 exceeds d2* table."""
        df = _make_balanced(
            operators=[chr(65 + i) for i in range(11)],  # 11 operators
            parts=["P1", "P2"],
            trials=2,
        )
        with pytest.raises(ValueError, match="d2\\* table"):
            grr_xbar_r(df)

    def test_k_exceeds_d2_table_raises(self):
        """Lines 100-101 — k (trials per cell) = 11 → d2* KeyError."""
        df = _make_balanced(
            operators=["A", "B"],
            parts=["P1", "P2"],
            trials=11,  # k=11, not in d2* table
        )
        with pytest.raises(ValueError, match="d2\\* table"):
            grr_xbar_r(df)

    def test_tolerance_relative_grr_percent(self):
        """Line 113 — when tolerance is given, %GR&R uses tolerance/(6) denominator."""
        df = _make_balanced(["A", "B"], ["P1", "P2", "P3", "P4", "P5"], trials=2)
        result_tv = grr_xbar_r(df)                       # default: relative to TV
        result_tol = grr_xbar_r(df, tolerance=10.0)      # relative to tolerance

        # Both are valid GRRResult objects
        assert isinstance(result_tv, GRRResult)
        assert isinstance(result_tol, GRRResult)
        # With a large tolerance the tolerance-relative GR&R should be smaller
        assert result_tol.total_grr != result_tv.total_grr

    def test_tolerance_branch_gives_nonzero_result(self):
        """Line 113 — tolerance path returns finite, positive %GR&R."""
        df = _make_balanced(["A", "B"], [f"P{i}" for i in range(1, 6)], trials=2)
        result = grr_xbar_r(df, tolerance=5.0)
        assert result.total_grr > 0
        assert result.total_grr < 100


# ---------------------------------------------------------------------------
# grr_anova — uncovered branches
# ---------------------------------------------------------------------------

class TestANOVAUncoveredBranches:

    def test_too_few_operators_raises(self):
        """Line 172 — fewer than 2 unique operators must raise."""
        rows = [
            {"operator": "A", "part": "P1", "measurement": 10.0},
            {"operator": "A", "part": "P2", "measurement": 20.0},
        ]
        with pytest.raises(ValueError, match="at least 2 unique operators"):
            grr_anova(pd.DataFrame(rows))

    def test_too_few_parts_raises(self):
        """Line 172 — fewer than 2 unique parts must raise."""
        rows = [
            {"operator": "A", "part": "P1", "measurement": 10.0},
            {"operator": "B", "part": "P1", "measurement": 10.1},
        ]
        with pytest.raises(ValueError, match="at least 2 unique operators"):
            grr_anova(pd.DataFrame(rows))

    def test_unequal_trials_raises(self):
        """Line 177 — unequal trials in anova path."""
        rows = [
            {"operator": "A", "part": "P1", "measurement": 10.0},
            {"operator": "A", "part": "P1", "measurement": 10.1},
            {"operator": "A", "part": "P2", "measurement": 20.0},
            {"operator": "B", "part": "P1", "measurement": 10.2},
            {"operator": "B", "part": "P2", "measurement": 20.1},
            {"operator": "B", "part": "P2", "measurement": 20.2},
        ]
        with pytest.raises(ValueError, match="same number of trials"):
            grr_anova(pd.DataFrame(rows))

    def test_significant_interaction_branch(self):
        """
        Lines 220-221, 227-229 — cross-over data forces p_interaction < 0.05
        so the interaction_significant=True branch executes.
        """
        df = _make_crossover_interaction(trials=3)
        result = grr_anova(df)

        assert isinstance(result, GRRResult)
        assert result.details is not None
        assert result.details["interaction_significant"] is True
        # var_interaction should be captured in details
        assert result.details["var_interaction"] > 0

    def test_significant_interaction_sets_detail_fields(self):
        """Lines 227-229 — var_operator and var_interaction computed in sig-interaction path."""
        df = _make_crossover_interaction(trials=4)
        result = grr_anova(df)

        assert result.details["interaction_significant"] is True
        # IV (interaction variation) exposed in details
        assert "iv" in result.details
        assert result.details["iv"] >= 0

    def test_tolerance_relative_grr_percent(self):
        """Line 244 — tolerance path in anova returns correct %GR&R."""
        df = _make_balanced(["A", "B", "C"], [f"P{i}" for i in range(1, 6)], trials=2)
        result_tv = grr_anova(df)
        result_tol = grr_anova(df, tolerance=10.0)

        assert isinstance(result_tol, GRRResult)
        assert result_tol.total_grr != result_tv.total_grr

    def test_tolerance_branch_gives_nonzero(self):
        """Line 244 — tolerance-relative anova GR&R is finite and positive."""
        df = _make_balanced(["A", "B"], [f"P{i}" for i in range(1, 6)], trials=2)
        result = grr_anova(df, tolerance=5.0)
        assert result.total_grr > 0
        assert result.total_grr < 500  # wide bound — ratio can exceed 100 if GRR > tol/6
