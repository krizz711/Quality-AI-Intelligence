"""
Phase 6 API additions — AI-powered quality intelligence endpoints.

New endpoints:
    POST /studies/{study_id}/narrative   — Gemini GR&R narrative + root cause
  POST /spc/predict                    — Predictive quality risk before violations
  POST /spc/interpret                  — NL interpretation of SPC violations
  POST /chat                           — Conversational quality engineering agent
  GET  /studies/{study_id}/report      — Download PDF report (fixes NotImplementedError)

Add these routes into api/main.py by importing from this module,
or paste the endpoint functions directly into main.py.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from agent.llm_analyst import (
    GRRNarrative,
    PredictiveInsight,
    SPCNarrative,
    answer_quality_question,
    generate_grr_narrative,
    generate_predictive_insight,
    interpret_spc_violations,
    stream_quality_answer,
)
from agent.adapters.registry import get_adapter
from api.rate_limit import limiter
from core.config import settings
from db.database import AsyncSessionLocal
from db.models import GrrStudy
from grr.acceptance import AcceptanceVerdict, AcceptanceLevel
from grr.calculator import GRRResult
from grr.report_generator import create_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ai"])


# ─── Request / Response schemas ──────────────────────────────────────────────

class GRRNarrativeResponse(BaseModel):
    study_id: str
    equipment_id: str
    characteristic_name: str
    grr_percent: float
    acceptance: str
    narrative: dict[str, Any]


class SPCInterpretRequest(BaseModel):
    chart_type: str = "i_mr"
    part_number: str = "UNKNOWN"
    characteristic_name: str = "UNKNOWN"
    violated_rules: dict[str, list[int]]
    ucl: float
    cl: float
    lcl: float
    recent_values: list[float] = Field(..., min_length=2)


class SPCInterpretResponse(BaseModel):
    pattern_description: str
    manufacturing_significance: str
    likely_causes: list[str]
    urgency: str
    recommended_actions: list[str]


class PredictRequest(BaseModel):
    part_number: str
    characteristic_name: str
    values_history: list[float] = Field(..., min_length=5)
    ucl: float
    cl: float
    lcl: float
    recent_grr_pct: float | None = None


class PredictResponse(BaseModel):
    trend_summary: str
    predicted_violation_risk: str
    time_to_action: str
    leading_indicators: list[str]
    preventive_actions: list[str]


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3)
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    context_override: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    answer: str
    context_used: list[str]  # which data sources were included


class PredictionForecast(BaseModel):
    process_id: str
    characteristic_name: str
    measurement_count: int
    cusum_shift_detected: bool
    cusum_violation_indices: list[int]
    ewma_trend_detected: bool
    ewma_violation_indices: list[int]
    predicted_breach_in: int | None  # observations until predicted UCL/LCL breach
    drift_direction: str             # "upward" | "downward" | "none"
    confidence_interval: dict[str, float]  # {"lower": ..., "upper": ...}
    suggested_action: str
    model_run_id: str                # MLflow run ID (empty string if unavailable)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _check_api_key() -> str:
    """Return API key or raise 503 if not configured."""
    key = settings.gemini_api_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY not configured. Set it in .env to enable AI features.",
        )
    return key


async def _load_study(study_id: str) -> GrrStudy:
    """Load a GrrStudy by UUID or raise 404."""
    try:
        uid = uuid.UUID(study_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid study ID format")

    async with AsyncSessionLocal() as session:
        study = await session.get(GrrStudy, uid)
        if not study:
            raise HTTPException(status_code=404, detail=f"Study {study_id} not found")
        return study


async def _build_system_context() -> dict[str, Any]:
    """
    Snapshot current system state to inject into the conversational agent.
    Pulls recent GR&R studies and unacknowledged violations from TimescaleDB.
    """
    context: dict[str, Any] = {}

    try:
        async with AsyncSessionLocal() as session:
            # Recent GR&R studies
            result = await session.execute(
                text("""
                    SELECT equipment_id, characteristic_name, grr_pct, ndc,
                           acceptance_decision, created_at
                    FROM grr_studies
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
            )
            studies = [dict(row) for row in result.mappings().all()]
            context["recent_grr_studies"] = studies

            # Unacknowledged violations
            result = await session.execute(
                text("""
                    SELECT part_number, characteristic_name, violation_type,
                           severity, measured_value, ucl, lcl, created_at
                    FROM quality_violations
                    WHERE alert_sent = FALSE OR acknowledged_by IS NULL
                    ORDER BY created_at DESC
                    LIMIT 20
                """)
            )
            violations = [dict(row) for row in result.mappings().all()]
            context["open_violations"] = violations

            # Pending reviews
            result = await session.execute(
                text("""
                    SELECT rq.id, gs.equipment_id, gs.grr_pct, gs.acceptance_decision
                    FROM review_queue rq
                    JOIN grr_studies gs ON gs.id = rq.study_id
                    WHERE rq.status = 'pending'
                    ORDER BY rq.created_at DESC
                    LIMIT 5
                """)
            )
            reviews = [dict(row) for row in result.mappings().all()]
            context["pending_reviews"] = reviews

    except Exception as exc:
        logger.warning("Could not load full system context: %s", exc)
        context["error"] = "Partial context — database may be unavailable"

    return context


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/studies/{study_id}/narrative",
    response_model=GRRNarrativeResponse,
    summary="Generate AI narrative for a GR&R study",
    description=(
        "Uses Gemini to generate a natural-language GR&R study report including "
        "root-cause analysis, corrective action recommendations, and production "
        "risk assessment. Study must already exist in the database."
    ),
)
@limiter.limit("20/minute")
async def get_grr_narrative(request: Request, study_id: str) -> GRRNarrativeResponse:
    api_key = _check_api_key()
    study = await _load_study(study_id)

    # Reconstruct enough of GRRResult for the prompt
    grr_result_dict = {
        "total_grr": study.grr_pct or 0.0,
        "repeatability": study.ev or 0.0,
        "reproducibility": study.av or 0.0,
        "part_variation": study.pv or 0.0,
        "total_variation": (
            ((study.ev or 0) ** 2 + (study.av or 0) ** 2 + (study.pv or 0) ** 2) ** 0.5
        ),
        "ndc": study.ndc or 0,
        "details": {"method": "xbar_r"},
    }
    verdict_dict = {
        "level": study.acceptance_decision or "unknown",
        "grr_percent": study.grr_pct or 0.0,
        "ndc": study.ndc or 0,
        "ndc_adequate": (study.ndc or 0) >= 5,
    }

    narrative: GRRNarrative = await generate_grr_narrative(
        grr_result=grr_result_dict,
        verdict=verdict_dict,
        equipment_id=study.equipment_id,
        characteristic_name=study.characteristic_name,
        api_key=api_key,
    )

    return GRRNarrativeResponse(
        study_id=study_id,
        equipment_id=study.equipment_id,
        characteristic_name=study.characteristic_name,
        grr_percent=study.grr_pct or 0.0,
        acceptance=study.acceptance_decision or "unknown",
        narrative={
            "summary": narrative.summary,
            "root_cause_analysis": narrative.root_cause_analysis,
            "recommendations": narrative.recommendations,
            "risk_assessment": narrative.risk_assessment,
            "confidence": narrative.confidence,
        },
    )


@router.get(
    "/studies/{study_id}/report",
    summary="Download PDF report for a GR&R study",
    description="Generates and returns a PDF report for the specified study. Fixes the NotImplementedError in the base orchestrator.",
    response_class=Response,
)
@limiter.limit("30/minute")
async def download_grr_report(request: Request, study_id: str) -> Response:
    """
    Generate a PDF report for a completed GR&R study.
    Returns raw PDF bytes with appropriate Content-Disposition header.
    """
    study = await _load_study(study_id)

    # Reconstruct GRRResult and AcceptanceVerdict from stored data
    ev = study.ev or 0.0
    av = study.av or 0.0
    pv = study.pv or 0.0
    grr_pct = study.grr_pct or 0.0
    ndc = study.ndc or 0
    tv = ((ev**2 + av**2 + pv**2) ** 0.5) if (ev or av or pv) else 1.0

    result = GRRResult(
        total_grr=grr_pct,
        repeatability=ev,
        reproducibility=av,
        part_variation=pv,
        total_variation=tv,
        ndc=ndc,
        details={"method": "xbar_r"},
    )

    acceptance_str = study.acceptance_decision or "not_acceptable"
    try:
        level = AcceptanceLevel(acceptance_str)
    except ValueError:
        level = AcceptanceLevel.NOT_ACCEPTABLE

    verdict = AcceptanceVerdict(
        level=level,
        grr_percent=grr_pct,
        ndc=ndc,
        ndc_adequate=ndc >= 5,
        remarks=[
            f"%GR&R = {grr_pct:.1f}% — {acceptance_str}",
            f"NDC = {ndc}",
            f"Equipment: {study.equipment_id}",
        ],
        requires_human_review=(level == AcceptanceLevel.CONDITIONAL),
    )

    from datetime import date
    metadata = {
        "Study Date": str(study.created_at.date() if study.created_at else date.today()),
        "Equipment ID": study.equipment_id,
        "Characteristic": study.characteristic_name,
        "Method": "Xbar-R",
        "Generated By": "Arad Quality Agent",
    }

    pdf_bytes = create_pdf(result, verdict, study_metadata=metadata)

    filename = f"grr_report_{study_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/spc/interpret",
    response_model=SPCInterpretResponse,
    summary="AI interpretation of SPC Nelson rule violations",
    description=(
        "Pass SPC violation data and receive a manufacturing-meaningful "
        "interpretation with likely root causes and recommended actions."
    ),
)
@limiter.limit("20/minute")
async def interpret_spc(request: Request) -> SPCInterpretResponse:
    body = SPCInterpretRequest.model_validate(await request.json())
    api_key = _check_api_key()

    narrative: SPCNarrative = await interpret_spc_violations(
        chart_type=body.chart_type,
        part_number=body.part_number,
        characteristic_name=body.characteristic_name,
        violated_rules=body.violated_rules,
        control_limits={"ucl": body.ucl, "cl": body.cl, "lcl": body.lcl},
        recent_values=body.recent_values,
        api_key=api_key,
    )

    return SPCInterpretResponse(
        pattern_description=narrative.pattern_description,
        manufacturing_significance=narrative.manufacturing_significance,
        likely_causes=narrative.likely_causes,
        urgency=narrative.urgency,
        recommended_actions=narrative.recommended_actions,
    )


@router.post(
    "/spc/predict",
    response_model=PredictResponse,
    summary="Predict quality violations before they occur",
    description=(
        "Gemini analyzes measurement trends and predicts future violations "
        "before Nelson rules fire. Acts as an early-warning system."
    ),
)
@limiter.limit("20/minute")
async def predict_violations(request: Request) -> PredictResponse:
    body = PredictRequest.model_validate(await request.json())
    api_key = _check_api_key()

    insight: PredictiveInsight = await generate_predictive_insight(
        part_number=body.part_number,
        characteristic_name=body.characteristic_name,
        values_history=body.values_history,
        control_limits={"ucl": body.ucl, "cl": body.cl, "lcl": body.lcl},
        recent_grr_pct=body.recent_grr_pct,
        api_key=api_key,
    )

    return PredictResponse(
        trend_summary=insight.trend_summary,
        predicted_violation_risk=insight.predicted_violation_risk,
        time_to_action=insight.time_to_action,
        leading_indicators=insight.leading_indicators,
        preventive_actions=insight.preventive_actions,
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Conversational quality engineering agent",
    description=(
        "Ask quality engineering questions in plain English. "
        "Gemini has access to current GR&R studies, SPC violations, "
        "and pending reviews. Maintains conversation context across turns."
    ),
)
@limiter.limit("30/minute")
async def chat_with_agent(request: Request) -> ChatResponse:
    body = ChatRequest.model_validate(await request.json())
    api_key = _check_api_key()

    # Load live system context (or use override for testing)
    if body.context_override is not None:
        context = body.context_override
        context_sources = ["context_override"]
    else:
        context = await _build_system_context()
        context_sources = [k for k in context if k != "error"]

    history = [{"role": m.role, "content": m.content} for m in body.conversation_history]

    answer = await answer_quality_question(
        question=body.question,
        context=context,
        conversation_history=history,
        api_key=api_key,
    )

    return ChatResponse(answer=answer, context_used=context_sources)


# Real context queries the streaming agent runs, in order. Each maps to one
# node in the dashboard's live work-log. (id, label, detail, sql, context_key,
# result-formatter). These are the SAME queries _build_system_context() runs —
# here we emit an event the instant each one actually finishes.
_STREAM_CONTEXT_STEPS: list[tuple[str, str, str, str, str, Any]] = [
    (
        "grr",
        "Querying GR&R studies",
        "Measurement-system capability",
        """
            SELECT equipment_id, characteristic_name, grr_pct, ndc,
                   acceptance_decision, created_at
            FROM grr_studies
            ORDER BY created_at DESC
            LIMIT 10
        """,
        "recent_grr_studies",
        lambda n: f"{n} stud{'y' if n == 1 else 'ies'}",
    ),
    (
        "spc",
        "Scanning SPC violations",
        "Control-chart breaches",
        """
            SELECT part_number, characteristic_name, violation_type,
                   severity, measured_value, ucl, lcl, created_at
            FROM quality_violations
            WHERE alert_sent = FALSE OR acknowledged_by IS NULL
            ORDER BY created_at DESC
            LIMIT 20
        """,
        "open_violations",
        lambda n: f"{n} open",
    ),
    (
        "review",
        "Checking pending reviews",
        "Awaiting sign-off",
        """
            SELECT rq.id, gs.equipment_id, gs.grr_pct, gs.acceptance_decision
            FROM review_queue rq
            JOIN grr_studies gs ON gs.id = rq.study_id
            WHERE rq.status = 'pending'
            ORDER BY rq.created_at DESC
            LIMIT 5
        """,
        "pending_reviews",
        lambda n: f"{n} pending",
    ),
]


@router.post(
    "/chat/stream",
    summary="Conversational quality agent (streaming)",
    description=(
        "Same agent as POST /chat, but streams its real work as Server-Sent "
        "Events: one event per actual context query as it completes (with real "
        "row counts), then the Gemini answer token-by-token. The dashboard renders "
        "these events directly as the live 'thinking' work-log — no choreography."
    ),
)
@limiter.limit("30/minute")
async def chat_with_agent_stream(request: Request) -> StreamingResponse:
    body = ChatRequest.model_validate(await request.json())
    api_key = _check_api_key()  # raises 503 before streaming starts if unset
    history = [{"role": m.role, "content": m.content} for m in body.conversation_history]
    question = body.question

    async def event_stream():
        def sse(obj: dict[str, Any]) -> str:
            return f"data: {json.dumps(obj)}\n\n"

        t_start = time.perf_counter()
        context: dict[str, Any] = {}
        sources: list[str] = []

        # ── Real context queries — emit start/done around each actual query ──
        if body.context_override is not None:
            context = body.context_override
            sources = ["context_override"]
        else:
            for step_id, label, detail, sql, key, fmt in _STREAM_CONTEXT_STEPS:
                yield sse({"t": "step", "id": step_id, "phase": "start", "label": label, "detail": detail})
                try:
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(text(sql))
                        rows = [dict(row) for row in result.mappings().all()]
                    context[key] = rows
                    sources.append(key)
                    yield sse({"t": "step", "id": step_id, "phase": "done", "count": len(rows), "result": fmt(len(rows))})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("stream context step %s failed: %s", step_id, exc)
                    yield sse({"t": "step", "id": step_id, "phase": "done", "status": "skipped", "result": "unavailable"})

        # ── Reasoning + token-streamed answer ───────────────────────────────
        yield sse({"t": "step", "id": "reason", "phase": "start", "label": "Reasoning with Gemini", "detail": "Synthesizing answer"})

        answer_parts: list[str] = []
        composing = False
        try:
            async for piece in stream_quality_answer(question, context, history, api_key):
                if not composing:
                    composing = True
                    yield sse({"t": "step", "id": "reason", "phase": "done", "result": "synthesized"})
                    yield sse({"t": "step", "id": "compose", "phase": "start", "label": "Composing answer", "detail": "Drafting response"})
                answer_parts.append(piece)
                yield sse({"t": "delta", "text": piece})
        except Exception as exc:  # noqa: BLE001
            logger.error("stream answer generation failed: %s", exc)

        if not composing:
            # Nothing streamed (e.g. Gemini unavailable) — close out the reason step.
            yield sse({"t": "step", "id": "reason", "phase": "done", "result": "synthesized"})
        else:
            yield sse({"t": "step", "id": "compose", "phase": "done", "result": "drafted"})

        answer = "".join(answer_parts)
        yield sse({
            "t": "final",
            "answer": answer,
            "sources": sources,
            "ms": int((time.perf_counter() - t_start) * 1000),
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx/uvicorn)
        },
    )


@router.get(
    "/predictions/{process_id}",
    response_model=PredictionForecast,
    summary="Statistical prediction forecast for a process",
    description=(
        "Runs CUSUM and EWMA detection on recent measurement history for the "
        "given process (part_number). Returns predicted breach timing, drift "
        "direction, confidence interval, and a suggested action. All prediction "
        "runs are logged to MLflow under experiment 'spc_predictions'."
    ),
)
@limiter.limit("30/minute")
async def get_process_predictions(
    request: Request,
    process_id: str,
    characteristic: str = Query(default="", description="Characteristic name filter (optional)"),
    window: int = Query(default=30, ge=5, le=200, description="Number of recent measurements to use"),
) -> PredictionForecast:
    """
    Statistical prediction endpoint — no LLM calls, pure SPC math.

    1. Pull last `window` measurements from TimescaleDB for `process_id`.
    2. Compute I-MR control limits.
    3. Run CUSUM (shift detection) and EWMA (trend detection).
    4. Extrapolate linear trend to predict breach timing.
    5. Log prediction run to MLflow.
    6. Return structured forecast with suggested action.
    """
    import numpy as np
    from spc.control_charts import individuals_mr_chart
    from spc.cusum import cusum_from_limits
    from spc.ewma import ewma_from_limits
    from spc.anomaly_detector import linear_trend_extrapolation

    # ── 1. Load measurement history ───────────────────────────────────────────
    query_params: dict[str, Any] = {"pn": process_id, "window": window}
    sql = """
        SELECT measured_value, characteristic_name
        FROM measurements
        WHERE part_number = :pn
    """
    if characteristic:
        sql += " AND characteristic_name = :cn"
        query_params["cn"] = characteristic

    sql += " ORDER BY timestamp DESC LIMIT :window"

    async with AsyncSessionLocal() as session:
        result = await session.execute(text(sql), query_params)
        rows = result.mappings().all()

    if len(rows) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Insufficient measurement history for '{process_id}' "
                f"(found {len(rows)}, need ≥5). Collect more data first."
            ),
        )

    values = list(reversed([float(r["measured_value"]) for r in rows]))
    char_name = rows[0]["characteristic_name"] if rows else (characteristic or "unknown")
    vals_arr = np.asarray(values, dtype=float)

    # ── 2. Compute control limits via I-MR chart ──────────────────────────────
    i_chart, _ = individuals_mr_chart(values)
    ucl = i_chart.limits.ucl
    lcl = i_chart.limits.lcl
    cl = i_chart.limits.cl
    sigma = i_chart.limits.sigma

    # ── 3. CUSUM + EWMA detection ─────────────────────────────────────────────
    cusum_result = cusum_from_limits(vals_arr, ucl, lcl)
    ewma_result = ewma_from_limits(vals_arr, ucl, lcl)

    # ── 4. Linear trend extrapolation ────────────────────────────────────────
    slope, drift_direction, obs_until = linear_trend_extrapolation(vals_arr, ucl, lcl)

    # Confidence interval: mean ± 2*sigma of recent 10 points
    recent = vals_arr[-10:]
    ci_mean = float(recent.mean())
    ci_half = 2.0 * sigma
    confidence_interval = {
        "lower": round(ci_mean - ci_half, 6),
        "upper": round(ci_mean + ci_half, 6),
    }

    # ── 5. Suggested action ───────────────────────────────────────────────────
    if cusum_result.shift_detected:
        suggested_action = (
            f"STOP — CUSUM detected a sustained process shift "
            f"({cusum_result.shift_direction}) at measurement index "
            f"{cusum_result.first_signal_index}. Investigate assignable cause immediately."
        )
    elif ewma_result.shift_detected:
        suggested_action = (
            f"WARNING — EWMA trend detected ({ewma_result.drift_direction}). "
            f"Adjust process parameters before next {obs_until or '?'} measurements."
        )
    elif obs_until is not None and obs_until <= 10:
        suggested_action = (
            f"CAUTION — Linear trend predicts control limit breach in ~{obs_until} "
            f"measurements ({drift_direction}). Schedule preventive maintenance."
        )
    else:
        suggested_action = "Process is in statistical control. Continue routine monitoring."

    # ── 6. Log to MLflow ──────────────────────────────────────────────────────
    run_id = ""
    try:
        adapter = get_adapter()
        run_id = await adapter.log_experiment(
            experiment_name="spc_predictions",
            run_name=f"{process_id}_{char_name}",
            params={
                "model_type": "cusum+ewma",
                "input_window": len(values),
                "process_id": process_id,
                "characteristic": char_name,
            },
            metrics={
                "cusum_violations": float(len(cusum_result.shift_indices)),
                "ewma_violations": float(len(ewma_result.violation_indices)),
                "trend_slope": round(float(slope), 6),
                "obs_until_breach": float(obs_until) if obs_until is not None else -1.0,
            },
            tags={
                "shift_detected": str(cusum_result.shift_detected),
                "drift_direction": drift_direction,
                "suggested_action_level": (
                    "critical" if cusum_result.shift_detected
                    else "warning" if ewma_result.shift_detected
                    else "ok"
                ),
            },
        )
    except Exception:
        logger.warning("MLflow logging failed for prediction run (non-fatal)", exc_info=True)

    return PredictionForecast(
        process_id=process_id,
        characteristic_name=char_name,
        measurement_count=len(values),
        cusum_shift_detected=cusum_result.shift_detected,
        cusum_violation_indices=cusum_result.shift_indices,
        ewma_trend_detected=ewma_result.shift_detected,
        ewma_violation_indices=ewma_result.violation_indices,
        predicted_breach_in=obs_until,
        drift_direction=drift_direction,
        confidence_interval=confidence_interval,
        suggested_action=suggested_action,
        model_run_id=run_id,
    )
