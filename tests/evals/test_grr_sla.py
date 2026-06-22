"""
Eval: GR&R SLA — validates that the Xbar-R and ANOVA calculators complete
in well under the 2-hour (7200s) target for automated computation.

These are CPU-only benchmarks. The real SLA includes DB + API latency,
but the statistical engine should be negligibly fast (<5s) by itself.
"""

import time

import pandas as pd
import pytest

from grr.calculator import grr_anova, grr_xbar_r

_SLA_SECONDS = 7200  # 2 hours — job requirement
_FAST_THRESHOLD_SECONDS = 5.0  # calculator alone must be <5s


def _build_df(n_operators: int, n_parts: int, n_trials: int, seed: int = 42) -> pd.DataFrame:
    import numpy as np

    rng = np.random.default_rng(seed)
    rows = []
    for op in range(n_operators):
        for part in range(n_parts):
            for _ in range(n_trials):
                rows.append({
                    "operator": f"op_{op}",
                    "part": part,
                    "measurement": 10.0 + rng.normal(0, 0.05) + part * 0.1,
                })
    return pd.DataFrame(rows)


@pytest.mark.parametrize("n_operators,n_parts,n_trials,label", [
    (2, 5, 2, "minimum_aiag"),
    (3, 10, 2, "standard_aiag"),
    (3, 10, 3, "standard_aiag_3trials"),
    (5, 10, 3, "large_study"),
])
def test_xbar_r_completes_within_sla(n_operators, n_parts, n_trials, label):
    df = _build_df(n_operators, n_parts, n_trials)
    start = time.perf_counter()
    result = grr_xbar_r(df)
    elapsed = time.perf_counter() - start

    assert elapsed < _FAST_THRESHOLD_SECONDS, (
        f"[{label}] Xbar-R took {elapsed:.3f}s — exceeds {_FAST_THRESHOLD_SECONDS}s fast threshold"
    )
    assert elapsed < _SLA_SECONDS, (
        f"[{label}] Xbar-R took {elapsed:.3f}s — exceeds 2-hour SLA"
    )
    assert 0.0 <= result.total_grr <= 100.0


@pytest.mark.parametrize("n_operators,n_parts,n_trials,label", [
    (2, 5, 2, "minimum_aiag"),
    (3, 10, 2, "standard_aiag"),
    (3, 10, 3, "standard_aiag_3trials"),
])
def test_anova_completes_within_sla(n_operators, n_parts, n_trials, label):
    df = _build_df(n_operators, n_parts, n_trials)
    start = time.perf_counter()
    result = grr_anova(df)
    elapsed = time.perf_counter() - start

    assert elapsed < _FAST_THRESHOLD_SECONDS, (
        f"[{label}] ANOVA took {elapsed:.3f}s — exceeds {_FAST_THRESHOLD_SECONDS}s fast threshold"
    )
    assert 0.0 <= result.total_grr <= 100.0


def test_xbar_r_bulk_100_studies_under_sla():
    """100 sequential studies must all complete within the total SLA."""
    df = _build_df(3, 10, 2)
    start = time.perf_counter()
    for _ in range(100):
        grr_xbar_r(df)
    elapsed = time.perf_counter() - start

    assert elapsed < _SLA_SECONDS, (
        f"100 Xbar-R studies took {elapsed:.1f}s — exceeds 2-hour SLA"
    )
    # Also assert a practical ceiling so CI fails fast
    assert elapsed < 30.0, f"100 Xbar-R studies took {elapsed:.1f}s — suspiciously slow"
