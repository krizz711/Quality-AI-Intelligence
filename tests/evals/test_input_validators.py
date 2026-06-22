"""
Eval: Input validator guardrails in the API layer.

Tests the Pydantic validators added to GRRStudyRequest and SPCRequest:
- GRR minimum operators (≥2)
- GRR minimum parts (≥5)
- Measurement value range (±1e9)
- SPC value range (±1e9)
"""

import pytest
from pydantic import ValidationError

from api.main import GRRStudyRequest, SPCRequest


# ── GRRStudyRequest ───────────────────────────────────────────────────────────

def _valid_grr_measurements(n_parts: int = 5, n_operators: int = 2, n_trials: int = 2) -> list[dict]:
    rows = []
    for op_i in range(n_operators):
        for part_i in range(n_parts):
            for _ in range(n_trials):
                rows.append({"part": f"P{part_i}", "operator": f"OP{op_i}", "value": 10.0 + part_i * 0.1})
    return rows


def test_grr_request_valid_passes():
    req = GRRStudyRequest(
        part_ids=[f"P{i}" for i in range(5)],
        operator_ids=["A", "B"],
        measurements=_valid_grr_measurements(),
    )
    assert req is not None


def test_grr_request_rejects_single_operator():
    with pytest.raises(ValidationError, match="2 operators"):
        GRRStudyRequest(
            part_ids=[f"P{i}" for i in range(5)],
            operator_ids=["A"],
            measurements=_valid_grr_measurements(n_operators=1),
        )


def test_grr_request_rejects_fewer_than_5_parts():
    with pytest.raises(ValidationError, match="5 parts"):
        GRRStudyRequest(
            part_ids=["P1", "P2", "P3", "P4"],
            operator_ids=["A", "B"],
            measurements=_valid_grr_measurements(n_parts=4),
        )


def test_grr_request_rejects_extreme_measurement_value():
    bad_measurements = _valid_grr_measurements()
    bad_measurements[0]["value"] = 2e9  # way outside physical range

    with pytest.raises(ValidationError, match="physical range"):
        GRRStudyRequest(
            part_ids=[f"P{i}" for i in range(5)],
            operator_ids=["A", "B"],
            measurements=bad_measurements,
        )


def test_grr_request_accepts_edge_values():
    """Values right at the boundary (1e9) should be rejected; just under should pass."""
    measurements = _valid_grr_measurements()
    measurements[0]["value"] = 999_999_999.0  # just under 1e9

    req = GRRStudyRequest(
        part_ids=[f"P{i}" for i in range(5)],
        operator_ids=["A", "B"],
        measurements=measurements,
    )
    assert req is not None


def test_grr_request_rejects_exactly_1e9():
    bad_measurements = _valid_grr_measurements()
    bad_measurements[0]["value"] = 1e9

    with pytest.raises(ValidationError, match="physical range"):
        GRRStudyRequest(
            part_ids=[f"P{i}" for i in range(5)],
            operator_ids=["A", "B"],
            measurements=bad_measurements,
        )


# ── SPCRequest ────────────────────────────────────────────────────────────────

def test_spc_request_valid_passes():
    req = SPCRequest(values=[10.0, 10.1, 9.9, 10.2, 10.0, 9.8])
    assert req is not None


def test_spc_request_rejects_extreme_value():
    with pytest.raises(ValidationError, match="physical range"):
        SPCRequest(values=[1.0, 2.0, 3.0, 1e10])


def test_spc_request_rejects_negative_extreme():
    with pytest.raises(ValidationError, match="physical range"):
        SPCRequest(values=[1.0, 2.0, -2e9])


def test_spc_request_accepts_normal_values():
    req = SPCRequest(values=[0.001, -0.002, 0.003, -0.001, 0.002, 0.000])
    assert req is not None
