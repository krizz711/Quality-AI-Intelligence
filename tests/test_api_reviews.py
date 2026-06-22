"""Tests for GET /reviews and PATCH /reviews/{review_id}."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import os

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app, headers={"x-api-key": os.environ["API_AUTH_KEY"]})


def _session_with_execute(mock_session_local: MagicMock, execute_result: MagicMock) -> AsyncMock:
    """Wire AsyncSessionLocal to return a mock session whose execute() yields execute_result."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=execute_result)
    mock_session.commit = AsyncMock()
    mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_session


@patch("api.main.AsyncSessionLocal")
def test_get_reviews_returns_list(mock_session_local: MagicMock) -> None:
    mock_mappings = MagicMock()
    mock_mappings.all.return_value = []
    execute_result = MagicMock()
    execute_result.mappings.return_value = mock_mappings
    _session_with_execute(mock_session_local, execute_result)

    response = client.get("/reviews")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json() == []


def test_patch_review_invalid_decision_returns_400() -> None:
    response = client.patch(
        "/reviews/fake-id",
        json={"decision": "maybe", "decided_by": "john"},
    )
    assert response.status_code == 400


@patch("api.main.AsyncSessionLocal")
def test_patch_review_not_found_returns_404(mock_session_local: MagicMock) -> None:
    mock_mappings = MagicMock()
    mock_mappings.first.return_value = None
    execute_result = MagicMock()
    execute_result.mappings.return_value = mock_mappings
    _session_with_execute(mock_session_local, execute_result)

    response = client.patch(
        "/reviews/nonexistent-id",
        json={"decision": "approved", "decided_by": "john"},
    )

    assert response.status_code == 404


@patch("api.main.AsyncSessionLocal")
def test_patch_already_decided_returns_400(mock_session_local: MagicMock) -> None:
    mock_mappings = MagicMock()
    mock_mappings.first.return_value = {
        "id": "r",
        "study_id": "s",
        "status": "approved",
    }
    execute_result = MagicMock()
    execute_result.mappings.return_value = mock_mappings
    _session_with_execute(mock_session_local, execute_result)

    response = client.patch(
        "/reviews/r",
        json={"decision": "approved", "decided_by": "john"},
    )

    assert response.status_code == 400


@patch("api.main.AsyncSessionLocal")
def test_approve_review_returns_decision_in_response(
    mock_session_local: MagicMock,
) -> None:
    mock_mappings = MagicMock()
    mock_mappings.first.return_value = {
        "id": "rev-1",
        "study_id": "study-1",
        "status": "pending",
    }
    execute_result = MagicMock()
    execute_result.mappings.return_value = mock_mappings
    mock_session = _session_with_execute(mock_session_local, execute_result)

    response = client.patch(
        "/reviews/rev-1",
        json={"decision": "approved", "notes": "looks good", "decided_by": "john"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "approved"
    assert data["decided_by"] == "john"
    assert mock_session.execute.await_count == 3
    mock_session.commit.assert_awaited_once()
