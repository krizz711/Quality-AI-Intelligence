import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
import uuid
from datetime import datetime, timezone

import os

from fastapi.testclient import TestClient

from api.main import app
from agent.llm_analyst import (
    _parse_json_response,
    generate_grr_narrative,
    interpret_spc_violations,
    generate_predictive_insight,
    answer_quality_question,
)
from db.models import GrrStudy


client = TestClient(app)
HEADERS = {"x-api-key": os.environ["API_AUTH_KEY"]}


# ── LLM Analyst Unit Tests (Mocking HTTPX) ──────────────────────────────────

@pytest.mark.asyncio
async def test_parse_json_response():
    # 1
    assert _parse_json_response('{"key": "value"}') == {"key": "value"}
    # 2
    assert _parse_json_response('Some prefix {"a": 1}') == {"a": 1}
    # 3
    assert _parse_json_response("No json here") == {"content": "No json here"}


@pytest.mark.asyncio
@patch("agent.llm_analyst.httpx.AsyncClient.post")
async def test_call_gemini_success(mock_post):
    # 4
    from agent.llm_analyst import _call_gemini
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "Hello!"}]}}]}
    mock_post.return_value = mock_resp

    result = await _call_gemini("Hi", "fake_key")
    assert result == "Hello!"


@pytest.mark.asyncio
@patch("agent.llm_analyst.httpx.AsyncClient.post")
async def test_generate_grr_narrative(mock_post):
    # 5
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": '{"summary": "Bad", "confidence": "high"}'}]}}]}
    mock_post.return_value = mock_resp

    res = await generate_grr_narrative(
        grr_result={"total_grr": 35.0, "details": {}},
        verdict={},
        equipment_id="EQ1",
        characteristic_name="Len",
        api_key="fake"
    )
    assert res.summary == "Bad"
    assert res.confidence == "high"


@pytest.mark.asyncio
@patch("agent.llm_analyst.httpx.AsyncClient.post")
async def test_interpret_spc_violations_active(mock_post):
    # 6
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": '{"urgency": "immediate"}'}]}}]}
    mock_post.return_value = mock_resp

    res = await interpret_spc_violations(
        chart_type="xbar_r",
        part_number="P1",
        characteristic_name="C1",
        violated_rules={"rule_1": [1, 2]},
        control_limits={"cl": 0, "ucl": 1, "lcl": -1},
        recent_values=[0.1, 0.2],
        api_key="fake"
    )
    assert res.urgency == "immediate"


@pytest.mark.asyncio
async def test_interpret_spc_violations_clean():
    # 7
    res = await interpret_spc_violations(
        chart_type="xbar_r",
        part_number="P1",
        characteristic_name="C1",
        violated_rules={"rule_1": []},  # Empty
        control_limits={"cl": 0, "ucl": 1, "lcl": -1},
        recent_values=[0.1, 0.2],
        api_key="fake"
    )
    assert res.urgency == "monitor"


@pytest.mark.asyncio
@patch("agent.llm_analyst.httpx.AsyncClient.post")
async def test_generate_predictive_insight_enough_data(mock_post):
    # 8
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": '{"predicted_violation_risk": "high"}'}]}}]}
    mock_post.return_value = mock_resp

    res = await generate_predictive_insight(
        part_number="P1",
        characteristic_name="C1",
        values_history=[1, 2, 3, 4, 5],
        control_limits={"cl": 0, "ucl": 1, "lcl": -1},
        recent_grr_pct=10.0,
        api_key="fake"
    )
    assert res.predicted_violation_risk == "high"


@pytest.mark.asyncio
async def test_generate_predictive_insight_insufficient_data():
    # 9
    res = await generate_predictive_insight(
        part_number="P1",
        characteristic_name="C1",
        values_history=[1, 2],  # < 5 points
        control_limits={"cl": 0, "ucl": 1, "lcl": -1},
        recent_grr_pct=10.0,
        api_key="fake"
    )
    assert res.predicted_violation_risk == "unknown"


@pytest.mark.asyncio
@patch("agent.llm_analyst.httpx.AsyncClient.post")
async def test_answer_quality_question(mock_post):
    # 10
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "It is broken."}]}}]}
    mock_post.return_value = mock_resp

    res = await answer_quality_question(
        question="Why?",
        context={"info": "stuff"},
        conversation_history=[{"role": "user", "content": "hi"}],
        api_key="fake"
    )
    assert res == "It is broken."


# ── API Route Tests (Mocking internal functions) ────────────────────────────

def test_api_predict():
    # 11
    with patch("api.ai_routes.generate_predictive_insight") as mock_predict:
        mock_predict.return_value = MagicMock(
            trend_summary="Summary",
            predicted_violation_risk="low",
            time_to_action="None",
            leading_indicators=[],
            preventive_actions=[]
        )
        
        payload = {
            "part_number": "P1",
            "characteristic_name": "C1",
            "values_history": [1, 2, 3, 4, 5],
            "ucl": 1, "cl": 0, "lcl": -1
        }
        res = client.post("/spc/predict", json=payload, headers=HEADERS)
        assert res.status_code == 200
        assert res.json()["predicted_violation_risk"] == "low"


def test_api_interpret():
    # 12
    with patch("api.ai_routes.interpret_spc_violations") as mock_interpret:
        mock_interpret.return_value = MagicMock(
            pattern_description="Pattern",
            manufacturing_significance="Bad",
            likely_causes=[],
            urgency="high",
            recommended_actions=[]
        )
        
        payload = {
            "violated_rules": {"rule_1": [1]},
            "ucl": 1, "cl": 0, "lcl": -1,
            "recent_values": [1, 2]
        }
        res = client.post("/spc/interpret", json=payload, headers=HEADERS)
        assert res.status_code == 200
        assert res.json()["urgency"] == "high"


def test_api_chat():
    # 13
    with patch("api.ai_routes.answer_quality_question") as mock_ans:
        mock_ans.return_value = "It's fine."
        
        payload = {
            "question": "How is it?",
            "context_override": {"a": 1}
        }
        res = client.post("/chat", json=payload, headers=HEADERS)
        assert res.status_code == 200
        assert res.json()["answer"] == "It's fine."
        assert "context_override" in res.json()["context_used"]


def test_api_narrative():
    # 14
    with patch("api.ai_routes._load_study") as mock_load, \
         patch("api.ai_routes.generate_grr_narrative") as mock_gen:
         
        mock_study = MagicMock(
            equipment_id="EQ1",
            characteristic_name="C1",
            grr_pct=10.0,
            acceptance_decision="approved",
            ev=1.0, av=1.0, pv=1.0, ndc=5
        )
        mock_load.return_value = mock_study
        
        mock_gen.return_value = MagicMock(
            summary="Good", root_cause_analysis="None", recommendations=[],
            risk_assessment="Low", confidence="high"
        )
        
        res = client.post(f"/studies/{uuid.uuid4()}/narrative", headers=HEADERS)
        assert res.status_code == 200
        assert res.json()["narrative"]["summary"] == "Good"


def test_api_report():
    # 15
    with patch("api.ai_routes._load_study") as mock_load, \
         patch("api.ai_routes.create_pdf") as mock_pdf:
         
        mock_study = MagicMock(
            equipment_id="EQ1",
            characteristic_name="C1",
            grr_pct=10.0,
            acceptance_decision="approved",
            ev=1.0, av=1.0, pv=1.0, ndc=5,
            created_at=datetime.now(timezone.utc)
        )
        mock_load.return_value = mock_study
        
        mock_pdf.return_value = b"%PDF-1.4 mock pdf"
        
        res = client.get(f"/studies/{uuid.uuid4()}/report", headers=HEADERS)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content == b"%PDF-1.4 mock pdf"


def test_api_auth_failure():
    # 16
    payload = {
        "question": "How is it?",
        "context_override": {"a": 1}
    }
    # No headers provided
    res = client.post("/chat", json=payload)
    assert res.status_code == 403

    # Wrong header
    res = client.post("/chat", json=payload, headers={"x-api-key": "wrong-key"})
    assert res.status_code == 403  # Forbidden
