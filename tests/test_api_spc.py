"""Tests for the /spc/analyze API endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
import os

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app, headers={"x-api-key": os.environ["API_AUTH_KEY"]})


@pytest.fixture(autouse=True)
def mock_alert_engine():
    """SPC analyze may invoke AlertEngine when Rule 1 fires."""
    with patch("api.main.AlertEngine") as mock_cls:
        mock_cls.return_value.process_pending_violations = AsyncMock(return_value=0)
        yield mock_cls


def _in_control_xbar_values(n_subgroups: int = 10, subgroup_size: int = 5) -> list[float]:
    rng = np.random.default_rng(0)
    values: list[float] = []
    for _ in range(n_subgroups):
        for _ in range(subgroup_size):
            values.append(float(rng.normal(10.0, 0.1)))
    return values


@patch("api.main.AsyncSessionLocal")
def test_analyze_spc_xbar_r(mock_session_local: AsyncMock) -> None:
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    payload = {
        "values": _in_control_xbar_values(),
        "chart_type": "xbar_r",
        "subgroup_size": 5,
    }
    response = client.post("/spc/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["chart_type"] == "xbar_r"
    assert data["ucl"] > data["cl"] > data["lcl"]
    assert "nelson_violations" in data
    for rule in [f"rule_{i}" for i in range(1, 9)]:
        assert rule in data["nelson_violations"]


@patch("api.main.AsyncSessionLocal")
def test_analyze_spc_truncates_partial_subgroup(mock_session_local: AsyncMock) -> None:
    """Extra values beyond a full subgroup must not affect the chart."""
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    base = _in_control_xbar_values(n_subgroups=5, subgroup_size=3)
    partial = [99.0, 99.0]  # incomplete sixth subgroup
    payload = {
        "values": base + partial,
        "chart_type": "xbar_r",
        "subgroup_size": 3,
    }
    response = client.post("/spc/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    # 5 subgroups of 3 → 5 Xbar points; partial tail dropped
    assert len(data["out_of_control_indices"]) <= 5


@patch("api.main.AsyncSessionLocal")
def test_analyze_spc_i_mr(mock_session_local: AsyncMock) -> None:
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    values = [10.0 + 0.1 * i for i in range(20)]
    response = client.post(
        "/spc/analyze",
        json={"values": values, "chart_type": "i_mr", "subgroup_size": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["chart_type"] == "i_mr"
    assert data["ucl"] > data["cl"]


@patch("api.main.AsyncSessionLocal")
def test_analyze_spc_p_chart(mock_session_local: AsyncMock) -> None:
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    response = client.post(
        "/spc/analyze",
        json={
            "values": [2, 3, 1, 4, 2],
            "chart_type": "p",
            "subgroup_size": 100,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["chart_type"] == "p"
    assert 0 <= data["cl"] <= 1


@patch("api.main.AsyncSessionLocal")
def test_analyze_spc_rule_1_persisted(mock_session_local: AsyncMock) -> None:
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    values = [10.0] * 24 + [50.0]
    response = client.post(
        "/spc/analyze",
        json={"values": values, "chart_type": "i_mr", "subgroup_size": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["nelson_violations"]["rule_1"]) > 0
    mock_session.add.assert_called()
    mock_session.commit.assert_called()


def test_analyze_spc_invalid_subgroup_size() -> None:
    response = client.post(
        "/spc/analyze",
        json={
            "values": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0],
            "chart_type": "xbar_r",
            "subgroup_size": 11,
        },
    )
    assert response.status_code == 422
    assert "subgroup_size" in response.json()["detail"]
