from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, headers={"x-api-key": os.environ["API_AUTH_KEY"]})


def _wire_session(mock_session_local: MagicMock, execute_results: list[MagicMock] | None = None) -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=execute_results or [])
    session.commit = AsyncMock()
    session.add = MagicMock()
    session_local_ctx = mock_session_local.return_value
    session_local_ctx.__aenter__ = AsyncMock(return_value=session)
    session_local_ctx.__aexit__ = AsyncMock(return_value=None)
    return session


def _result_with_rows(rows: list[dict[str, object]]) -> MagicMock:
    mappings = MagicMock()
    mappings.all.return_value = rows
    mappings.first.return_value = rows[0] if rows else None
    result = MagicMock()
    result.mappings.return_value = mappings
    return result


@patch("agent.alert_manager.AlertManager.send", new_callable=AsyncMock)
@patch("api.quality_routes.geminiService.analyzeGRR", new_callable=AsyncMock, return_value="GRR AI")
@patch("api.quality_routes.AsyncSessionLocal")
def test_api_grr_analyze_and_history(mock_session_local: MagicMock, mock_gemini: AsyncMock, mock_alert_send: AsyncMock) -> None:
    session = _wire_session(mock_session_local)

    payload = {
        "measurements": [
            {"operator": "A", "part": 1, "trial": 1, "value": 10.0},
            {"operator": "A", "part": 1, "trial": 2, "value": 10.1},
            {"operator": "A", "part": 2, "trial": 1, "value": 10.2},
            {"operator": "A", "part": 2, "trial": 2, "value": 10.3},
            {"operator": "A", "part": 3, "trial": 1, "value": 10.4},
            {"operator": "A", "part": 3, "trial": 2, "value": 10.5},
            {"operator": "A", "part": 4, "trial": 1, "value": 10.6},
            {"operator": "A", "part": 4, "trial": 2, "value": 10.7},
            {"operator": "A", "part": 5, "trial": 1, "value": 10.8},
            {"operator": "A", "part": 5, "trial": 2, "value": 10.9},
            {"operator": "B", "part": 1, "trial": 1, "value": 11.0},
            {"operator": "B", "part": 1, "trial": 2, "value": 11.1},
            {"operator": "B", "part": 2, "trial": 1, "value": 11.2},
            {"operator": "B", "part": 2, "trial": 2, "value": 11.3},
            {"operator": "B", "part": 3, "trial": 1, "value": 11.4},
            {"operator": "B", "part": 3, "trial": 2, "value": 11.5},
            {"operator": "B", "part": 4, "trial": 1, "value": 11.6},
            {"operator": "B", "part": 4, "trial": 2, "value": 11.7},
            {"operator": "B", "part": 5, "trial": 1, "value": 11.8},
            {"operator": "B", "part": 5, "trial": 2, "value": 11.9},
        ],
        "partTolerance": 1.0,
    }

    response = client.post("/api/v1/grr/analyze", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert set(data) == {
        "grr_percent",
        "repeatability",
        "reproducibility",
        "number_of_distinct_categories",
        "ai_analysis",
        "timestamp",
    }
    assert data["ai_analysis"] == "GRR AI"
    mock_gemini.assert_awaited_once()
    assert session.commit.await_count == 1

    history_row = {
        "id": uuid.uuid4(),
        "completed_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "grr_pct": 12.5,
        "acceptance_decision": "acceptable",
        "operator_count": 2,
        "part_count": 5,
    }
    history_result = _result_with_rows([history_row])
    session.execute = AsyncMock(return_value=history_result)

    history = client.get("/api/v1/grr/history")
    assert history.status_code == 200
    history_data = history.json()
    assert history_data[0]["verdict"] == "acceptable"
    assert history_data[0]["operator_count"] == 2
    assert history_data[0]["part_count"] == 5


def test_api_grr_analyze_rejects_small_sample() -> None:
    response = client.post(
        "/api/v1/grr/analyze",
        json={
            "measurements": [
                {"operator": "A", "part": 1, "trial": 1, "value": 10.0},
                {"operator": "A", "part": 2, "trial": 1, "value": 10.1},
                {"operator": "B", "part": 1, "trial": 1, "value": 10.2},
                {"operator": "B", "part": 2, "trial": 1, "value": 10.3},
            ]
        },
    )
    assert response.status_code == 422


@patch("api.quality_routes.geminiService.analyzeSPCAnomaly", new_callable=AsyncMock, return_value="SPC AI")
@patch("api.quality_routes.AsyncSessionLocal")
def test_api_spc_data_and_history(mock_session_local: MagicMock, mock_gemini: AsyncMock) -> None:
    session = _wire_session(mock_session_local)

    response = client.post(
        "/api/v1/spc/data",
        json={
            "process_name": "line-1",
            "measurements": [10.0, 10.1, 10.2, 10.3, 10.4, 11.5, 10.5, 10.6],
        },
    )

    assert response.status_code == 201
    assert response.json()["ai_analysis"] == "SPC AI"
    assert session.add.call_count >= 8
    mock_gemini.assert_awaited_once()

    history_rows = [
        {
            "timestamp": datetime.now(timezone.utc),
            "measured_value": 10.7,
            "part_number": "line-1",
            "characteristic_name": "line-1",
        }
    ]
    history_result = _result_with_rows(history_rows)
    session.execute = AsyncMock(return_value=history_result)

    history = client.get("/api/v1/spc/history/line-1")
    assert history.status_code == 200
    assert history.json()["process_name"] == "line-1"
    assert history.json()["points"][0]["value"] == 10.7


@patch("api.quality_routes.AsyncSessionLocal")
def test_dashboard_summary_and_audit_log(mock_session_local: MagicMock) -> None:
    grr_result = _result_with_rows([
        {"count": 2, "pass_rate": 0.5},
    ])
    alerts_result = _result_with_rows([
        {"count": 1},
    ])
    violations_result = _result_with_rows([
        {
            "id": uuid.uuid4(),
            "timestamp": datetime.now(timezone.utc),
            "part_number": "P1",
            "characteristic_name": "diameter",
            "violation_type": "nelson_rule_1",
            "severity": "critical",
            "measured_value": 12.0,
        }
    ])
    audit_result = _result_with_rows([
        {
            "id": uuid.uuid4(),
            "created_at": datetime.now(timezone.utc),
            "actor": "system",
            "action": "alert_triggered",
            "entity_type": "alert",
            "entity_id": "alert-1",
            "details": {"type": "spc_violation"},
        }
    ])

    session = _wire_session(mock_session_local, [grr_result, alerts_result, violations_result, audit_result])

    summary = client.get("/api/v1/dashboard/summary")
    assert summary.status_code == 200
    assert summary.json()["total_grr_analyses"] == 2
    assert summary.json()["active_alerts_count"] == 1

    audit = client.get("/api/v1/audit-log")
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "alert_triggered"
    assert session.execute.await_count >= 4


@patch("agent.alert_manager.AlertManager.send", new_callable=AsyncMock)
@patch("api.quality_routes.AsyncSessionLocal")
def test_alert_lifecycle(mock_session_local: MagicMock, mock_send: AsyncMock) -> None:
    mock_send.return_value = uuid.uuid4()
    trigger_session = _wire_session(mock_session_local)

    trigger = client.post(
        "/api/v1/alerts/trigger",
        json={
            "type": "spc_violation",
            "severity": "high",
            "message": "Process drift detected",
            "process_name": "line-9",
        },
    )
    assert trigger.status_code == 201
    assert trigger.json()["alert_id"]
    mock_send.assert_called_once()

    list_result = _result_with_rows(
        [
            {
                "id": uuid.uuid4(),
                "type": "spc_violation",
                "severity": "high",
                "message": "Process drift detected",
                "process_name": "line-9",
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "resolved_at": None,
            }
        ]
    )
    count_result = _result_with_rows([{"count": 1}])
    resolve_result = _result_with_rows(
        [
            {
                "id": uuid.uuid4(),
                "type": "spc_violation",
                "severity": "high",
                "message": "Process drift detected",
                "process_name": "line-9",
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "resolved_at": None,
            }
        ]
    )
    update_result = _result_with_rows([])
    session = _wire_session(
        mock_session_local,
        [count_result, list_result, resolve_result, update_result],
    )

    alerts = client.get("/api/v1/alerts?status=active&severity=high&limit=50")
    assert alerts.status_code == 200
    assert alerts.json()["total"] == 1
    assert alerts.json()["items"][0]["severity"] == "high"

    alert_id = alerts.json()["items"][0]["id"]
    resolve = client.put(f"/api/v1/alerts/{alert_id}/resolve")
    assert resolve.status_code == 200
    assert resolve.json()["alert_id"] == alert_id
    assert session.commit.await_count >= 1


@patch("api.quality_routes.AsyncSessionLocal")
def test_alert_feedback_and_accuracy(mock_session_local: MagicMock) -> None:
    alert_id = uuid.uuid4()
    alert_result = _result_with_rows([{"id": alert_id}])
    accuracy_result = _result_with_rows(
        [{"feedback_count": 4, "relevant_count": 3, "false_positive_count": 1}]
    )
    session = _wire_session(mock_session_local, [alert_result, accuracy_result])

    feedback = client.post(
        f"/api/v1/alerts/{alert_id}/feedback",
        json={
            "is_relevant": False,
            "category": "false_positive",
            "notes": "Known maintenance window",
            "submitted_by": "qe-1",
        },
    )
    assert feedback.status_code == 201
    assert feedback.json()["alert_id"] == str(alert_id)
    assert feedback.json()["is_relevant"] is False

    accuracy = client.get("/api/v1/alerts/accuracy")
    assert accuracy.status_code == 200
    assert accuracy.json()["feedback_count"] == 4
    assert accuracy.json()["accuracy_rate"] == 75.0
    assert accuracy.json()["target_met"] is False
    assert session.commit.await_count == 1


@patch("api.quality_routes.geminiService.analyzeSPCAnomaly", new_callable=AsyncMock, return_value="SPC AI")
@patch("api.quality_routes.AsyncSessionLocal")
def test_mes_measurement_integration(mock_session_local: MagicMock, mock_gemini: AsyncMock) -> None:
    session = _wire_session(mock_session_local)

    response = client.post(
        "/api/v1/integrations/mes/measurements",
        json={
            "event_id": "mes-1",
            "process_name": "Torque Press Line 1",
            "measurements": [5.01, 5.0, 4.99, 5.02],
            "source_system": "mes",
        },
    )

    assert response.status_code == 200
    assert response.json()["event_id"] == "mes-1"
    assert response.json()["accepted"] is True
    assert response.json()["analysis"]["ai_analysis"] == "SPC AI"
    assert mock_gemini.await_count == 1
    assert session.commit.await_count >= 2


@patch("api.quality_routes.AsyncSessionLocal")
def test_qms_equipment_event_without_measurements(mock_session_local: MagicMock) -> None:
    session = _wire_session(mock_session_local)

    response = client.post(
        "/api/v1/integrations/qms/inspection-equipment",
        json={
            "event_id": "qms-1",
            "equipment_id": "torque-tool-7",
            "fixture_id": "fixture-2",
            "operator_ids": ["A", "B", "C"],
            "source_system": "qms",
        },
    )

    assert response.status_code == 200
    assert response.json()["event_id"] == "qms-1"
    assert response.json()["accepted"] is True
    assert response.json()["grr_analysis_started"] is False
    assert session.commit.await_count == 1
