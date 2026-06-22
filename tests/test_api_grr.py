import pytest
import os

from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from api.main import app

client = TestClient(app, headers={"x-api-key": os.environ["API_AUTH_KEY"]})

@patch("api.main.get_adapter")
@patch("api.main.AsyncSessionLocal")
def test_create_grr_study_xbar_r(mock_session_local, mock_get_adapter):
    mock_adapter = AsyncMock()
    mock_get_adapter.return_value = mock_adapter
    # AIAG MSA requires >= 5 parts; 5 parts × 2 operators × 2 trials = 20 measurements
    payload = {
        "part_ids": ["P1", "P2", "P3", "P4", "P5"],
        "operator_ids": ["A", "B"],
        "measurements": [
            {"part": "P1", "operator": "A", "value": 1.00},
            {"part": "P1", "operator": "A", "value": 1.01},
            {"part": "P2", "operator": "A", "value": 2.00},
            {"part": "P2", "operator": "A", "value": 2.02},
            {"part": "P3", "operator": "A", "value": 3.00},
            {"part": "P3", "operator": "A", "value": 3.01},
            {"part": "P4", "operator": "A", "value": 4.00},
            {"part": "P4", "operator": "A", "value": 4.02},
            {"part": "P5", "operator": "A", "value": 5.00},
            {"part": "P5", "operator": "A", "value": 5.01},
            {"part": "P1", "operator": "B", "value": 1.02},
            {"part": "P1", "operator": "B", "value": 1.01},
            {"part": "P2", "operator": "B", "value": 2.01},
            {"part": "P2", "operator": "B", "value": 2.03},
            {"part": "P3", "operator": "B", "value": 3.02},
            {"part": "P3", "operator": "B", "value": 3.00},
            {"part": "P4", "operator": "B", "value": 4.01},
            {"part": "P4", "operator": "B", "value": 4.03},
            {"part": "P5", "operator": "B", "value": 5.02},
            {"part": "P5", "operator": "B", "value": 5.00},
        ],
        "method": "xbar_r"
    }

    # Mock the async session context manager
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    response = client.post("/studies/grr", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert "study_id" in data
    assert "grr_percent" in data
    assert "acceptance" in data
    assert "ndc" in data

    # Verify database session was used
    mock_session.add.assert_called()
    mock_session.commit.assert_called()

    # Verify adapter was called
    mock_adapter.log_experiment.assert_called_once()

@patch("api.main.get_adapter")
@patch("api.main.AsyncSessionLocal")
def test_create_grr_study_invalid_method(mock_session_local, mock_get_adapter):
    payload = {
        "part_ids": ["P1", "P2"],
        "operator_ids": ["A", "B"],
        "measurements": [
            {"part": "P1", "operator": "A", "value": 1.0},
            {"part": "P1", "operator": "A", "value": 1.1},
            {"part": "P2", "operator": "A", "value": 2.0},
            {"part": "P2", "operator": "A", "value": 2.1},
            {"part": "P1", "operator": "B", "value": 1.2},
            {"part": "P1", "operator": "B", "value": 1.1},
            {"part": "P2", "operator": "B", "value": 2.2},
            {"part": "P2", "operator": "B", "value": 2.1},
        ],
        "method": "invalid_method"
    }

    response = client.post("/studies/grr", json=payload)
    
    # Should be rejected by Pydantic validation before reaching our function
    assert response.status_code == 422
