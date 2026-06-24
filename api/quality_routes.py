"""Additional /api routes for GR&R, SPC, alerts, dashboard, and audit log."""

from __future__ import annotations

import hashlib
import logging
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text


from backend.services import gemini_service as geminiService
from api.rate_limit import limiter
from api.realtime import publish_realtime_event, state as realtime_state
from core.config import settings
from db.database import AsyncSessionLocal
from db.models import Alert, AlertFeedback, AlertRule, AuditLog, Gage, GrrStudy, Measurement, NotificationDelivery
from backend.services.audit_logger import log_event as audit_log_event
from api.auth import get_current_user
from core import settings_store, spc_baseline_store
from fastapi.responses import StreamingResponse
import io, csv
from grr.acceptance import evaluate
from grr.calculator import grr_anova, grr_xbar_r
from spc.baseline import Baseline, compute_baseline

class AlertResolveResponse(BaseModel):
    alert_id: str
    resolved_at: datetime
    
def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

logger = logging.getLogger(__name__)

_AI_UNAVAILABLE = "AI analysis unavailable — set GEMINI_API_KEY to enable Gemini narrative."


async def _optional_gemini(coro):
    """Run a Gemini coroutine; return a fallback message when the API key is absent."""
    try:
        return await coro
    except ValueError as exc:
        if "GEMINI_API_KEY" in str(exc):
            return _AI_UNAVAILABLE
        raise


router = APIRouter(prefix="/api/v1", tags=["quality-api"])


@router.patch("/alerts/{alert_id}/acknowledge", response_model=AlertResolveResponse)
async def acknowledge_alert(alert_id: str, request: Request):
    """Mark an alert as acknowledged and record the actor.

    Requires an Authorization header. For tests a bearer token of the form
    'Bearer <username>' will set the acknowledging user name.
    """
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication")
    user = getattr(request.state, "user", None)
    actor = getattr(user, "username", None) or "system"
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM alerts WHERE id::text = :id"), {"id": alert_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

        await session.execute(
            text("UPDATE alerts SET status='acknowledged', resolved_at=NOW(), resolved_by=:actor WHERE id::text = :id"),
            {"actor": actor, "id": alert_id},
        )
        await session.commit()
        return AlertResolveResponse(alert_id=alert_id, resolved_at=_now())



@router.websocket("/ws/measurements")
async def websocket_measurements(websocket: WebSocket) -> None:
    await realtime_state.manager.connect(websocket)
    try:
        while True:
            try:
                message = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break

            try:
                payload = json.loads(message)
            except Exception:
                continue

            if payload.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": _now().isoformat()})
    finally:
        await realtime_state.manager.disconnect(websocket)


@router.get("/__test/limiter")
@limiter.limit("2/minute")
async def _test_limiter(request: Request) -> dict:
    return {"ok": True}

# RBAC dependency (lazy import to avoid hard dependency at module import time)
def require_role(role: str):
    # Backwards-compatible dependency: accept any authenticated user.
    from fastapi import Depends
    from .auth import get_current_user

    def _dep(user=Depends(get_current_user)):
        if not user:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication")
        return user

    return _dep


class GRRMeasurementInput(BaseModel):
    operator: str = Field(..., min_length=1)
    part: int = Field(..., ge=1)
    trial: int = Field(..., ge=1)
    value: float

    @model_validator(mode="after")
    def validate_required_fields(self) -> "GRRMeasurementInput":
        if not self.operator.strip():
            raise ValueError("operator is required")
        return self


class GRRAnalyzeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    measurements: list[GRRMeasurementInput] = Field(..., min_length=1)
    part_tolerance: float | None = Field(default=None, alias="partTolerance")
    process_name: str | None = Field(default=None, alias="processName", max_length=200)

    @model_validator(mode="after")
    def validate_sample_sizes(self) -> "GRRAnalyzeRequest":
        operators = {item.operator.strip() for item in self.measurements if item.operator.strip()}
        parts = {item.part for item in self.measurements}
        trials = {item.trial for item in self.measurements}

        if len(operators) < 2:
            raise ValueError("GR&R analysis requires at least 2 operators")
        if len(parts) < 5:
            raise ValueError("GR&R analysis requires at least 5 parts")
        if len(trials) < 2:
            raise ValueError("GR&R analysis requires at least 2 trials")

        return self


class GRRAnalyzeResponse(BaseModel):
    grr_percent: float
    repeatability: float
    reproducibility: float
    number_of_distinct_categories: int
    ai_analysis: str
    timestamp: datetime


class GRRHistoryItem(BaseModel):
    id: str
    timestamp: datetime
    grr_percent: float | None = None
    verdict: Literal["pass", "acceptable", "fail"]
    operator_count: int
    part_count: int
    process_name: str | None = None


class SPCDataRequest(BaseModel):
    process_name: str = Field(..., min_length=1)
    measurements: list[float] = Field(..., min_length=1)
    ucl: float | None = None
    lcl: float | None = None
    target: float | None = None
    # When provided, only these values are persisted as new measurement rows;
    # `measurements` is then treated as the analysis window. Pass [] to run a
    # stats-only recompute without writing anything. Omitted → legacy behavior
    # (every submitted value is persisted).
    new_values: list[float] | None = None

    @model_validator(mode="after")
    def validate_measurements(self) -> "SPCDataRequest":
        if not self.process_name.strip():
            raise ValueError("process_name is required")
        if not self.measurements:
            raise ValueError("measurements must not be empty")
        return self


class SPCViolation(BaseModel):
    rule: str
    index: int
    value: float
    description: str


class SPCDataResponse(BaseModel):
    mean: float
    std_dev: float
    ucl: float
    lcl: float
    violations: list[SPCViolation]
    ai_analysis: str


class SPCHistoryPoint(BaseModel):
    timestamp: datetime
    value: float
    part_number: str | None = None
    characteristic_name: str | None = None


class SPCHistoryResponse(BaseModel):
    process_name: str
    points: list[SPCHistoryPoint]


class SpcBaselineResponse(BaseModel):
    process_name: str
    configured: bool
    ucl: float | None = None
    cl: float | None = None
    lcl: float | None = None
    sigma: float | None = None
    n_points: int | None = None


class SpcBaselineEstablishRequest(BaseModel):
    # Explicit window to baseline from; if omitted, the most recent `window`
    # persisted measurements for the process are used.
    measurements: list[float] | None = None
    window: int = Field(default=30, ge=2, le=500)
    # Lock the limits even if the baseline window isn't fully in control (Phase I
    # override — the user has reviewed the flagged points).
    force: bool = False


class SpcBaselineEstablishResponse(BaseModel):
    ok: bool                 # True only when the baseline was actually saved
    reason: str              # why it wasn't saved (empty when ok)
    process_name: str
    baseline: SpcBaselineResponse | None = None
    violations: dict[str, list[int]] = Field(default_factory=dict)


class DashboardSummaryResponse(BaseModel):
    total_grr_analyses: int
    passing_rate: float
    active_alerts_count: int
    recent_violations: list[dict[str, Any]]
    last_updated: datetime


class AlertTriggerRequest(BaseModel):
    type: Literal["grr_fail", "spc_violation", "trend_detected"]
    severity: Literal["low", "medium", "high", "critical"]
    message: str = Field(..., min_length=1)
    process_name: str = Field(..., min_length=1)


class AlertResponse(BaseModel):
    id: str
    type: str
    severity: str
    message: str
    process_name: str
    status: str
    created_at: datetime
    resolved_at: datetime | None = None


class AlertTriggerResponse(BaseModel):
    alert_id: str
    created_at: datetime


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    limit: int


class AlertResolveResponse(BaseModel):
    alert_id: str
    resolved_at: datetime


class AlertFeedbackRequest(BaseModel):
    is_relevant: bool
    category: Literal["true_positive", "false_positive", "duplicate", "late", "missing_context"] | None = None
    notes: str = ""
    submitted_by: str = Field("quality-engineer", min_length=1)


class AlertFeedbackResponse(BaseModel):
    feedback_id: str
    alert_id: str
    is_relevant: bool
    created_at: datetime


class AlertAccuracyResponse(BaseModel):
    feedback_count: int
    relevant_count: int
    false_positive_count: int
    accuracy_rate: float | None
    target_rate: float = 95.0
    target_met: bool | None


class AuditLogResponse(BaseModel):
    id: str
    timestamp: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, Any] | None = None


class QMSInspectionEquipmentEvent(BaseModel):
    equipment_id: str = Field(..., min_length=1)
    fixture_id: str | None = None
    characteristic_name: str = Field("inspection_characteristic", min_length=1)
    operator_ids: list[str] = Field(default_factory=list)
    measurements: list[GRRMeasurementInput] = Field(default_factory=list)
    part_tolerance: float | None = None
    source_system: str = "qms"
    event_id: str | None = None


class QMSInspectionEquipmentResponse(BaseModel):
    event_id: str
    accepted: bool
    grr_analysis_started: bool
    grr_result: GRRAnalyzeResponse | None = None
    message: str


class MESMeasurementEvent(BaseModel):
    process_name: str = Field(..., min_length=1)
    measurements: list[float] = Field(..., min_length=1)
    part_number: str | None = None
    characteristic_name: str | None = None
    target: float | None = None
    ucl: float | None = None
    lcl: float | None = None
    source_system: str = "mes"
    event_id: str | None = None


class MESMeasurementResponse(BaseModel):
    event_id: str
    accepted: bool
    analysis: SPCDataResponse
    message: str


def _verdict_from_grr(grr_percent: float | None) -> Literal["pass", "acceptable", "fail"]:
    if grr_percent is None:
        return "fail"
    if grr_percent < 10.0:
        return "pass"
    if grr_percent <= 30.0:
        return "acceptable"
    return "fail"


def _detect_western_electric_rules(values: list[float], center_line: float, sigma: float) -> list[SPCViolation]:
    violations: list[SPCViolation] = []
    if sigma <= 0:
        return violations

    upper_1 = center_line + sigma
    lower_1 = center_line - sigma
    upper_2 = center_line + 2 * sigma
    lower_2 = center_line - 2 * sigma
    upper_3 = center_line + 3 * sigma
    lower_3 = center_line - 3 * sigma

    for index, value in enumerate(values):
        if value > upper_3 or value < lower_3:
            violations.append(
                SPCViolation(
                    rule="rule_1",
                    index=index,
                    value=value,
                    description="One point beyond 3 sigma",
                )
            )

    for index in range(len(values) - 2):
        window = values[index : index + 3]
        above_2 = sum(value > upper_2 for value in window)
        below_2 = sum(value < lower_2 for value in window)
        if above_2 >= 2 or below_2 >= 2:
            violations.append(
                SPCViolation(
                    rule="rule_2",
                    index=index,
                    value=window[-1],
                    description="Two of three consecutive points beyond 2 sigma on the same side",
                )
            )

    for index in range(len(values) - 4):
        window = values[index : index + 5]
        above_1 = sum(value > upper_1 for value in window)
        below_1 = sum(value < lower_1 for value in window)
        if above_1 >= 4 or below_1 >= 4:
            violations.append(
                SPCViolation(
                    rule="rule_3",
                    index=index,
                    value=window[-1],
                    description="Four of five consecutive points beyond 1 sigma on the same side",
                )
            )

    streak = 1
    direction: int | None = None
    for index, value in enumerate(values):
        current_direction = 1 if value > center_line else -1 if value < center_line else 0
        if current_direction == 0:
            streak = 1
            direction = None
            continue
        if direction == current_direction:
            streak += 1
        else:
            direction = current_direction
            streak = 1
        if streak >= 8:
            violations.append(
                SPCViolation(
                    rule="rule_4",
                    index=index - 7,
                    value=value,
                    description="Eight consecutive points on the same side of the center line",
                )
            )

    return violations


async def _audit(session, actor: str, action: str, entity_type: str, entity_id: str, details: dict[str, Any]) -> None:
    session.add(
        AuditLog(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )


def _stored_alert_lookup_values(alert_id: str) -> tuple[str, str]:
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid alert ID format") from exc
    return str(alert_uuid), alert_uuid.hex


def _coerce_uuid(value: Any) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    text_value = str(value)
    try:
        return uuid.UUID(text_value)
    except ValueError:
        return uuid.UUID(hex=text_value)


async def _create_quality_alert(
    session,
    *,
    alert_type: Literal["grr_fail", "spc_violation", "trend_detected"],
    severity: Literal["low", "medium", "high", "critical"],
    message: str,
    process_name: str,
    payload: dict[str, Any],
    timestamp: datetime,
) -> uuid.UUID | None:
    from agent.alert_manager import AlertManager, AlertEvent
    manager = AlertManager()
    ev = AlertEvent(
        type=alert_type,
        severity=severity,
        message=message,
        process_name=process_name,
        payload=payload,
        grr_pct=payload.get("grr_percent") if payload else None,
    )
    alert_id = await manager.send(ev)
    
    # Still want to publish real-time event for UI
    if alert_id:
        await publish_realtime_event(
            {
                "type": "alert.created",
                "alert_id": str(alert_id),
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "process_name": process_name,
                "payload": payload,
            }
        )
    return alert_id


@limiter.limit("10/minute")
@router.post(
    "/grr/analyze",
    response_model=GRRAnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_grr(request: Request, payload: GRRAnalyzeRequest) -> GRRAnalyzeResponse:
    result = await _analyze_grr_impl(payload)
    # best-effort audit event for GRR run
    try:
        actor = getattr(getattr(request, "state", None), "user", None)
        actor_name = getattr(actor, "username", None) if actor else None
        user_id = getattr(actor, "username", None) if actor else None
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            ip_addr = forwarded_for.split(",")[0].strip()
        elif request.client and request.client.host:
            ip_addr = request.client.host
        else:
            ip_addr = "unknown"
        await audit_log_event(
            actor=actor_name,
            user_id=user_id,
            event_type="grr_study_run",
            component="grr_calculator",
            metadata={"grr_percent": result.grr_percent, "ndc": result.number_of_distinct_categories},
            algorithm_version=getattr(payload, "method", None) or "xbar_r",
            result_summary={"pct_grr": result.grr_percent, "ndc": result.number_of_distinct_categories, "verdict": getattr(result, 'total_grr', None)},
            ip_address=ip_addr,
        )
    except Exception:
        pass
    return result


async def _analyze_grr_impl(body: GRRAnalyzeRequest) -> GRRAnalyzeResponse:
    started = time.monotonic()
    try:
        df = pd.DataFrame([item.model_dump() for item in body.measurements])
        df = df.rename(columns={"value": "measurement"})

        try:
            result = grr_xbar_r(df, tolerance=body.part_tolerance)
        except ValueError:
            result = grr_anova(df, tolerance=body.part_tolerance)

        verdict = evaluate(result)
        ai_analysis = await _optional_gemini(
            geminiService.analyzeGRR(
                {
                    "measurements": [item.model_dump() for item in body.measurements],
                    "part_tolerance": body.part_tolerance,
                    "grr_percent": result.total_grr,
                    "repeatability": result.repeatability,
                    "reproducibility": result.reproducibility,
                    "number_of_distinct_categories": result.ndc,
                    "verdict": verdict.level.value,
                }
            )
        )

        study_id = uuid.uuid4()
        timestamp = _now()
        operators = {item.operator.strip() for item in body.measurements if item.operator.strip()}
        parts = {item.part for item in body.measurements}

        process_label = (body.process_name or "").strip() or "GR&R Analysis"

        async with AsyncSessionLocal() as session:
            session.add(
                GrrStudy(
                    id=study_id,
                    equipment_id=body.measurements[0].operator,
                    characteristic_name=process_label if process_label != "GR&R Analysis" else "grr_analysis",
                    status=verdict.level.value,
                    ev=result.repeatability,
                    av=result.reproducibility,
                    pv=result.part_variation,
                    grr_pct=result.total_grr,
                    ndc=result.ndc,
                    operator_count=len(operators),
                    part_count=len(parts),
                    acceptance_decision=verdict.level.value,
                    started_at=timestamp,
                    completed_at=timestamp,
                )
            )
            if result.total_grr > 30.0:
                await _create_quality_alert(
                    session,
                    alert_type="grr_fail",
                    severity="high",
                    message=(
                        f"GR&R study failed with {result.total_grr:.1f}% variation. "
                        f"Review the {process_label} measurement system."
                    ),
                    process_name=process_label,
                    payload={
                        "source": "api_grr_analyze",
                        "study_id": str(study_id),
                        "grr_percent": result.total_grr,
                    },
                    timestamp=timestamp,
                )
            await _audit(
                session,
                actor="system",
                action="api_grr_analyze",
                entity_type="grr_study",
                entity_id=str(study_id),
                details={
                    "grr_percent": result.total_grr,
                    "ndc": result.ndc,
                    "operator_count": len(operators),
                    "part_count": len(parts),
                    "verdict": verdict.level.value,
                    "duration_seconds": round(time.monotonic() - started, 4),
                    "slo_target_seconds": 7200,
                    "slo_met": (time.monotonic() - started) < 7200,
                },
            )
            await session.commit()

        await publish_realtime_event(
            {
                "type": "grr.analysis",
                "study_id": str(study_id),
                "grr_percent": result.total_grr,
                "repeatability": result.repeatability,
                "reproducibility": result.reproducibility,
                "ndc": result.ndc,
                "verdict": verdict.level.value,
                "timestamp": timestamp.isoformat(),
            }
        )

        return GRRAnalyzeResponse(
            grr_percent=result.total_grr,
            repeatability=result.repeatability,
            reproducibility=result.reproducibility,
            number_of_distinct_categories=result.ndc,
            ai_analysis=ai_analysis,
            timestamp=timestamp,
        )

        
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("GR&R analysis failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GR&R analysis failed") from exc


@router.get("/grr/history", response_model=list[GRRHistoryItem])
async def get_grr_history() -> list[GRRHistoryItem]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT id, completed_at, created_at, grr_pct, acceptance_decision,
                       operator_count, part_count, characteristic_name
                FROM grr_studies
                ORDER BY COALESCE(completed_at, created_at) DESC
                LIMIT 50
                """
            )
        )
        rows = result.mappings().all()

    history: list[GRRHistoryItem] = []
    for row in rows:
        grr_percent = row.get("grr_pct")
        characteristic = row.get("characteristic_name")
        process_name = None if not characteristic or characteristic == "grr_analysis" else characteristic
        history.append(
            GRRHistoryItem(
                id=str(row["id"]),
                timestamp=row.get("completed_at") or row.get("created_at") or _now(),
                grr_percent=grr_percent,
                verdict=_verdict_from_grr(grr_percent),
                operator_count=int(row.get("operator_count") or 0),
                part_count=int(row.get("part_count") or 0),
                process_name=process_name,
            )
        )
    return history


# ── Gage registry ────────────────────────────────────────────────────────────
class GageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(default="Inspection gage", max_length=200)
    nominal: float | None = None
    tolerance: float | None = None
    calibration_due: str | None = Field(default=None, max_length=32)


class GageResponse(BaseModel):
    id: str
    name: str
    type: str
    nominal: float | None = None
    tolerance: float | None = None
    calibration_due: str | None = None
    created_at: datetime


def _gage_to_response(g: Gage) -> GageResponse:
    return GageResponse(
        id=str(g.id),
        name=g.name,
        type=g.type,
        nominal=g.nominal,
        tolerance=g.tolerance,
        calibration_due=g.calibration_due,
        created_at=g.created_at,
    )


@router.get("/gages", response_model=list[GageResponse])
async def list_gages() -> list[GageResponse]:
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Gage).order_by(Gage.created_at.desc()))).scalars().all()
    return [_gage_to_response(g) for g in rows]


@router.post("/gages", response_model=GageResponse, status_code=status.HTTP_201_CREATED)
async def create_gage(body: GageCreate) -> GageResponse:
    async with AsyncSessionLocal() as session:
        gage = Gage(
            name=body.name.strip(),
            type=(body.type or "Inspection gage").strip(),
            nominal=body.nominal,
            tolerance=body.tolerance,
            calibration_due=body.calibration_due or None,
        )
        session.add(gage)
        await session.commit()
        await session.refresh(gage)
        return _gage_to_response(gage)


@router.delete("/gages/{gage_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_gage(gage_id: str) -> None:
    try:
        gid = uuid.UUID(gage_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid gage id") from exc
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM gages WHERE id = :id"), {"id": str(gid)})
        await session.commit()
    return None


# ── Alert routing rules ──────────────────────────────────────────────────────
_RULE_TRIGGERS = {"grr_fail", "spc_violation", "calibration_overdue", "pass_rate_below"}


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    trigger: str = Field(..., max_length=48)
    threshold: float | None = None
    scope: str = Field(default="Any process", max_length=200)
    channels: list[str] = Field(default_factory=list)
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    trigger: str | None = None
    threshold: float | None = None
    scope: str | None = None
    channels: list[str] | None = None
    enabled: bool | None = None


class AlertRuleResponse(BaseModel):
    id: str
    name: str
    trigger: str
    threshold: float | None = None
    scope: str
    channels: list[str]
    enabled: bool
    created_at: datetime


def _rule_to_response(r: AlertRule) -> AlertRuleResponse:
    return AlertRuleResponse(
        id=str(r.id),
        name=r.name,
        trigger=r.trigger,
        threshold=r.threshold,
        scope=r.scope,
        channels=list(r.channels or []),
        enabled=bool(r.enabled),
        created_at=r.created_at,
    )


@router.get("/alert-rules", response_model=list[AlertRuleResponse])
async def list_alert_rules() -> list[AlertRuleResponse]:
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(AlertRule).order_by(AlertRule.created_at.desc()))).scalars().all()
    return [_rule_to_response(r) for r in rows]


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(body: AlertRuleCreate) -> AlertRuleResponse:
    if body.trigger not in _RULE_TRIGGERS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown trigger")
    async with AsyncSessionLocal() as session:
        rule = AlertRule(
            name=body.name.strip(),
            trigger=body.trigger,
            threshold=body.threshold,
            scope=(body.scope or "Any process").strip(),
            channels=body.channels,
            enabled=body.enabled,
        )
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
        return _rule_to_response(rule)


@router.patch("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(rule_id: str, body: AlertRuleUpdate) -> AlertRuleResponse:
    try:
        rid = uuid.UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid rule id") from exc
    async with AsyncSessionLocal() as session:
        rule = await session.get(AlertRule, rid)
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
        for key, value in body.model_dump(exclude_unset=True).items():
            setattr(rule, key, value)
        await session.commit()
        await session.refresh(rule)
        return _rule_to_response(rule)


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_alert_rule(rule_id: str) -> None:
    try:
        rid = uuid.UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid rule id") from exc
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM alert_rules WHERE id = :id"), {"id": str(rid)})
        await session.commit()
    return None


# ── System settings (admin) — integration credentials + LLM key ──────────────
class SettingsUpdate(BaseModel):
    values: dict[str, str]


class SettingsTestRequest(BaseModel):
    channel: str


@router.get("/settings")
async def get_settings(_user: dict = Depends(get_current_user)) -> dict:
    """Masked integration config for the admin UI (secrets never returned).

    ``tests`` carries the last live-test result per channel so the UI can show
    "verified" (and gate alert routing) on real validation, not just presence.
    """
    return {
        "settings": await settings_store.get_masked(),
        "tests": await settings_store.get_test_status(),
    }


@router.put("/settings")
async def put_settings(payload: SettingsUpdate, _user: dict = Depends(get_current_user)) -> dict:
    actor = _user.get("username") if isinstance(_user, dict) else None
    await settings_store.set_many(payload.values, updated_by=actor)
    return {"settings": await settings_store.get_masked()}


@router.post("/settings/test")
async def test_settings(payload: SettingsTestRequest, _user: dict = Depends(get_current_user)) -> dict:
    ok, message = await settings_store.test_channel(payload.channel)
    # Persist so verification survives reloads and drives alert-routing gating.
    await settings_store.record_test(payload.channel, ok, message)
    return {"ok": ok, "message": message}


@router.delete("/settings/{channel}")
async def clear_settings(channel: str, _user: dict = Depends(get_current_user)) -> dict:
    """Remove a channel's stored credentials and its cached test result."""
    if channel not in settings_store.channels():
        raise HTTPException(status_code=404, detail=f"Unknown channel '{channel}'.")
    await settings_store.clear_channel(channel)
    return {"settings": await settings_store.get_masked()}


@router.get("/internal/llm-config")
async def internal_llm_config(_user: dict = Depends(get_current_user)) -> dict:
    """Active AI provider + decrypted key for the out-of-process ADK agent service.

    The "AI Agent" page runs in its own process (see ``adk_agent``) and can't read
    the encrypted Connections settings directly, so it fetches the active provider
    and key here — authenticated with the internal API key, same as its other backend
    calls. The Connections page (DB) is the source of truth; environment variables are
    the fallback for standalone runs.

    The key is returned in clear, so this endpoint is auth-gated and must stay
    internal (never expose it un-authenticated, and never log the value).
    """
    cfg = await settings_store.get_decrypted()
    provider = (cfg.get("llm.provider") or settings.llm_provider or "gemini").strip().lower()
    provider = {"anthropic": "claude", "gpt": "openai", "google": "gemini"}.get(provider, provider)
    if provider == "claude":
        key = cfg.get("llm.anthropic_api_key") or settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    elif provider == "openai":
        key = cfg.get("llm.openai_api_key") or settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
    else:
        provider = "gemini"
        key = cfg.get("llm.gemini_api_key") or settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    return {"provider": provider, "api_key": key, "configured": bool(key)}


async def _probe_tcp(target: str, timeout: float = 1.5) -> bool:
    """Best-effort TCP reachability probe of the first host:port in ``target``."""
    import asyncio as _asyncio
    import socket as _socket

    first = target.split(",")[0].strip()
    if "://" in first:
        first = first.split("://", 1)[1]
    if "/" in first:
        first = first.split("/", 1)[0]
    if ":" not in first:
        return False
    host, _, port = first.rpartition(":")
    try:
        await _asyncio.get_event_loop().run_in_executor(
            None, lambda: _socket.create_connection((host, int(port)), timeout)
        )
        return True
    except Exception:
        return False


@router.get("/integrations/status")
async def integrations_status(_user: dict = Depends(get_current_user)) -> dict:
    """Unified "what did my keys enable" view for onboarding and ops.

    Reports core-service reachability (DB / Redis / Kafka / MLflow), which optional
    integrations are configured, and which platform features are active — so an
    operator can confirm at a glance that filling in ``.env`` was enough. Read-only
    and side-effect free; secrets are never returned.
    """
    import os as _os

    services: dict[str, dict] = {}

    # Database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        services["database"] = {"configured": True, "status": "ok"}
    except Exception:
        services["database"] = {"configured": True, "status": "down"}

    # Redis
    redis_url = settings.redis_url or _os.environ.get("REDIS_URL", "")
    if redis_url:
        try:
            import redis.asyncio as _aioredis

            client = _aioredis.from_url(redis_url, socket_connect_timeout=1.5)
            await client.ping()
            await client.aclose()
            services["redis"] = {"configured": True, "status": "ok"}
        except Exception:
            services["redis"] = {"configured": True, "status": "down"}
    else:
        services["redis"] = {"configured": False, "status": "not_configured"}

    # Kafka / MLflow — light TCP probes
    kafka = settings.kafka_bootstrap_servers or _os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "")
    services["kafka"] = (
        {"configured": True, "status": "ok" if await _probe_tcp(kafka) else "down"}
        if kafka
        else {"configured": False, "status": "not_configured"}
    )
    mlflow_uri = settings.mlflow_tracking_uri or _os.environ.get("MLFLOW_TRACKING_URI", "")
    services["mlflow"] = (
        {"configured": True, "status": "ok" if await _probe_tcp(mlflow_uri) else "down"}
        if mlflow_uri
        else {"configured": False, "status": "not_configured"}
    )

    def _cfg(flag: Any) -> dict:
        return {"configured": bool(flag)}

    integrations = {
        "slack": _cfg(settings.slack_webhook_url),
        "email": _cfg(settings.smtp_host and settings.alert_email_recipients),
        "sms": _cfg((settings.sms_webhook_url or settings.twilio_account_sid) and settings.sms_to_numbers),
        "jira": _cfg(settings.jira_url and settings.jira_email and settings.jira_api_token),
        "qms": _cfg(settings.qms_api_url),
        "gemini": _cfg(settings.gemini_api_key),
    }

    features = {
        "autonomous_monitor": {
            "enabled": bool(settings.enable_autonomous_monitor),
            "interval_seconds": settings.monitor_interval_seconds,
        },
        "ai_analysis": {"enabled": bool(settings.gemini_api_key)},
    }

    summary = {
        "services_ok": sum(1 for s in services.values() if s["status"] == "ok"),
        "services_total": len(services),
        "integrations_configured": sum(1 for v in integrations.values() if v["configured"]),
        "integrations_total": len(integrations),
    }

    return {
        "environment": settings.environment,
        "services": services,
        "integrations": integrations,
        "features": features,
        "summary": summary,
    }


# ── Bulk measurement upload (CSV / Excel) ────────────────────────────────────
_UPLOAD_COLUMN_CANDIDATES: dict[str, list[str]] = {
    "timestamp": ["timestamp", "time", "datetime", "measured_at", "measuredat", "date", "logged_at"],
    "part_number": ["part_number", "part", "partno", "part_no", "partnumber", "part number"],
    "characteristic_name": ["characteristic_name", "characteristic", "feature", "parameter", "char", "dimension"],
    "measured_value": ["measured_value", "value", "measurement", "reading", "result", "actual"],
    "nominal_value": ["nominal_value", "nominal", "target", "nominal_val"],
    "unit": ["unit", "uom", "units"],
    "operator_id": ["operator_id", "operator", "appraiser", "inspector"],
    "equipment_id": ["equipment_id", "equipment", "machine", "gage", "gauge", "device", "instrument"],
    "shift": ["shift"],
}

_UPLOAD_INGEST_SQL = text(
    """
    INSERT INTO measurements (
        timestamp, part_number, characteristic_name, nominal_value, measured_value,
        unit, operator_id, equipment_id, shift, source_event_id, created_by
    ) VALUES (
        :timestamp, :part_number, :characteristic_name, :nominal_value, :measured_value,
        :unit, :operator_id, :equipment_id, :shift, :source_event_id, 'upload'
    )
    ON CONFLICT (source_event_id, timestamp) DO NOTHING
    """
)


def _upload_float(value: Any) -> float | None:
    try:
        if value is None or value == "" or (isinstance(value, float) and pd.isna(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _upload_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text_value = str(value).strip()
    return text_value[:64] if text_value else None


def _upload_timestamp(value: Any) -> datetime | None:
    try:
        parsed = pd.to_datetime(value, utc=True)
    except Exception:
        return None
    if parsed is None or pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _upload_row_to_measurement(record: pd.Series, resolved: dict[str, str]) -> dict[str, Any] | None:
    timestamp = _upload_timestamp(record[resolved["timestamp"]])
    measured_value = _upload_float(record[resolved["measured_value"]])
    if timestamp is None or measured_value is None:
        return None

    def optional(field: str) -> Any:
        column = resolved.get(field)
        return record[column] if column is not None else None

    part_number = (_upload_str(optional("part_number")) or _upload_str(optional("equipment_id")) or "UNKNOWN")[:64]
    characteristic = (_upload_str(optional("characteristic_name")) or "value")[:128]
    digest = hashlib.sha1(
        f"{part_number}|{characteristic}|{timestamp.isoformat()}|{measured_value}".encode()
    ).hexdigest()
    return {
        "timestamp": timestamp,
        "part_number": part_number,
        "characteristic_name": characteristic,
        "nominal_value": _upload_float(optional("nominal_value")),
        "measured_value": measured_value,
        "unit": _upload_str(optional("unit")),
        "operator_id": _upload_str(optional("operator_id")),
        "equipment_id": _upload_str(optional("equipment_id")),
        "shift": _upload_str(optional("shift")),
        "source_event_id": digest[:32],
    }


@router.post("/measurements/upload")
async def upload_measurements(
    file: UploadFile = File(...),
    mapping: str | None = Form(None),
    _user: dict = Depends(get_current_user),
) -> dict:
    """Bulk-ingest measurements from an uploaded CSV or Excel file.

    Columns are auto-detected (case-insensitive) against common header names; an
    optional ``mapping`` form field (JSON ``{our_field: column_name}``) overrides
    detection. Rows without a timestamp + numeric value are skipped, and ingestion
    de-duplicates so re-uploading the same file is safe. The autonomous monitor
    then analyses the new data — no further action needed.
    """
    content = await file.read()
    filename = (file.filename or "").lower()
    try:
        if filename.endswith((".xlsx", ".xls")):
            frame = pd.read_excel(io.BytesIO(content))
        else:
            frame = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse '{file.filename}': {exc}",
        )

    if frame.empty:
        return {"received": 0, "ingested": 0, "skipped": 0, "columns": [str(c) for c in frame.columns]}

    override: dict[str, str] = {}
    if mapping:
        try:
            override = {str(k): str(v) for k, v in json.loads(mapping).items()}
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="`mapping` must be valid JSON"
            )

    lower_columns = {str(c).strip().lower(): c for c in frame.columns}
    resolved: dict[str, str] = {}
    for field, candidates in _UPLOAD_COLUMN_CANDIDATES.items():
        if field in override and override[field] in frame.columns:
            resolved[field] = override[field]
            continue
        for candidate in candidates:
            if candidate in lower_columns:
                resolved[field] = lower_columns[candidate]
                break

    if "timestamp" not in resolved or "measured_value" not in resolved:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not detect a timestamp and a measured-value column. Rename your "
                "headers or pass a `mapping`. Columns seen: "
                + ", ".join(str(c) for c in frame.columns)
            ),
        )

    rows: list[dict[str, Any]] = []
    skipped = 0
    for _, record in frame.iterrows():
        built = _upload_row_to_measurement(record, resolved)
        if built is None:
            skipped += 1
        else:
            rows.append(built)

    ingested = 0
    duplicates = 0
    if rows:
        # Re-uploading the same file is idempotent (ON CONFLICT drops repeats); collapse
        # rows already on file (and repeats within this file) so the reported count is
        # genuinely-new measurements, not the batch size.
        async with AsyncSessionLocal() as session:
            existing = await session.execute(
                text("SELECT source_event_id FROM measurements WHERE source_event_id = ANY(:ids)"),
                {"ids": [r["source_event_id"] for r in rows]},
            )
            seen = {row[0] for row in existing.fetchall()}
            new_rows: list[dict[str, Any]] = []
            for r in rows:
                sid = r["source_event_id"]
                if sid in seen:
                    duplicates += 1
                    continue
                seen.add(sid)
                new_rows.append(r)
            if new_rows:
                await session.execute(_UPLOAD_INGEST_SQL, new_rows)
                await session.commit()
            ingested = len(new_rows)

    try:
        await audit_log_event(
            actor=_user.get("username") if isinstance(_user, dict) else "system",
            event_type="measurements_uploaded",
            component="upload",
            metadata={"file": file.filename, "received": int(len(frame)), "ingested": ingested, "duplicates": duplicates, "skipped": skipped},
        )
    except Exception:
        pass

    # ── Immediate SPC analysis for uploaded series ────────────────────────
    # The autonomous monitor only looks back 3 hours, so historical CSV data
    # would never be analysed. Run SPC inline so alerts appear immediately.
    upload_violations = 0
    upload_alerts = 0
    if ingested > 0:
        try:
            from agent.monitor import ContinuousMonitor
            from agent.alert_engine import AlertEngine

            # Use a generous lookback so even very old CSV timestamps are covered.
            monitor = ContinuousMonitor(lookback_minutes=525600)  # 1 year
            uploaded_series: set[tuple[str, str]] = set()
            for r in new_rows:
                pn = r.get("part_number") or "UNKNOWN"
                cn = r.get("characteristic_name") or "value"
                uploaded_series.add((pn, cn))

            for pn, cn in uploaded_series:
                try:
                    summary = await monitor.analyze_series(pn, cn)
                    upload_violations += summary.get("rule_1_violations", 0)
                except Exception:
                    logger.warning("upload_spc_analysis_failed part=%s char=%s", pn, cn, exc_info=True)

            # Dispatch any violations that were just created.
            if upload_violations > 0:
                try:
                    alert_engine = AlertEngine()
                    upload_alerts = await alert_engine.process_pending_violations()
                except Exception:
                    logger.warning("upload_alert_dispatch_failed", exc_info=True)

            logger.info(
                "upload_spc_analysis series=%d violations=%d alerts=%d",
                len(uploaded_series), upload_violations, upload_alerts,
            )
        except Exception:
            logger.warning("upload_spc_analysis_skipped", exc_info=True)

    return {
        "received": int(len(frame)),
        "ingested": ingested,
        "duplicates": duplicates,
        "skipped": skipped,
        "mapping": resolved,
        "violations_detected": upload_violations,
        "alerts_created": upload_alerts,
    }


@limiter.limit("20/minute")
@router.post("/spc/data", response_model=SPCDataResponse, status_code=status.HTTP_201_CREATED)
async def analyze_spc_data(request: Request, body: SPCDataRequest = Body(...)) -> SPCDataResponse:
    """Endpoint wrapper that delegates to the implementation.

    The limiter decorator expects the endpoint to receive a Starlette `Request`.
    Internal callers should call `_analyze_spc_data_impl` directly to avoid
    the rate-limit wrapper which requires a real `Request` instance.
    """
    return await _analyze_spc_data_impl(body)


async def _analyze_spc_data_impl(body: SPCDataRequest) -> SPCDataResponse:
    started = time.monotonic()
    try:
        values = [float(value) for value in body.measurements]
        mean_value = float(np.mean(values))
        std_dev = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0

        if body.ucl is not None and body.lcl is not None:
            # Explicit limits in the request override anything stored (back-compat / tests).
            ucl = float(body.ucl)
            lcl = float(body.lcl)
            sigma = abs(ucl - lcl) / 6 if ucl != lcl else std_dev
            center_line = float(body.target) if body.target is not None else mean_value
        else:
            stored = await spc_baseline_store.get_baseline(body.process_name)
            if stored is not None:
                # Phase II: judge points against the frozen, validated baseline so the
                # limits don't drift with the data (the whole point of a baseline).
                ucl, lcl, center_line, sigma = stored.ucl, stored.lcl, stored.cl, stored.sigma
            else:
                # No baseline yet → compute limits from the current window (Phase I).
                sigma = std_dev
                center_line = float(body.target) if body.target is not None else mean_value
                ucl = center_line + 3 * sigma
                lcl = center_line - 3 * sigma

        violations = _detect_western_electric_rules(values, center_line, sigma)

        # A stats-only recompute (new_values == []) — e.g. the dashboard redrawing the
        # chart for an existing process — must NOT call the LLM, persist, alert, or audit.
        # Return the computed limits/violations immediately so the chart loads instantly
        # even when the AI provider is slow or rate-limited (HTTP 429).
        if body.new_values is not None and len(body.new_values) == 0:
            return SPCDataResponse(
                mean=mean_value,
                std_dev=std_dev,
                ucl=ucl,
                lcl=lcl,
                violations=violations,
                ai_analysis="",
            )

        ai_analysis = await _optional_gemini(
            geminiService.analyzeSPCAnomaly(
                {
                    "process_name": body.process_name,
                    "measurements": values,
                    "mean": mean_value,
                    "std_dev": std_dev,
                    "ucl": ucl,
                    "lcl": lcl,
                    "target": body.target,
                    "violations": [violation.model_dump() for violation in violations],
                }
            )
        )

        timestamp = _now()
        values_to_persist = values if body.new_values is None else [float(v) for v in body.new_values]
        async with AsyncSessionLocal() as session:
            for value in values_to_persist:
                session.add(
                    Measurement(
                        timestamp=timestamp,
                        part_number=body.process_name,
                        characteristic_name=body.process_name,
                        nominal_value=body.target,
                        measured_value=value,
                        unit=None,
                        operator_id="api_spc",
                        equipment_id=body.process_name,
                        shift=None,
                        created_by="api_spc",
                    )
                )

            if violations:
                worst = next((violation for violation in violations if violation.rule == "rule_1"), violations[0])
                severity = "critical" if worst.rule == "rule_1" else "high"
                await _create_quality_alert(
                    session,
                    alert_type="spc_violation",
                    severity=severity,
                    message=(
                        f"{body.process_name} violated {worst.rule}: "
                        f"{worst.description} at measurement {worst.index + 1} ({worst.value:.4f})."
                    ),
                    process_name=body.process_name,
                    payload={
                        "source": "api_spc_data",
                        "violations": [violation.model_dump() for violation in violations],
                        "ucl": ucl,
                        "lcl": lcl,
                        "target": body.target,
                    },
                    timestamp=timestamp,
                )

            await _audit(
                session,
                actor="system",
                action="api_spc_data",
                entity_type="spc_process",
                entity_id=body.process_name,
                details={
                    "mean": mean_value,
                    "std_dev": std_dev,
                    "ucl": ucl,
                    "lcl": lcl,
                    "violations": [violation.model_dump() for violation in violations],
                    "duration_seconds": round(time.monotonic() - started, 4),
                },
            )
            await session.commit()

        await publish_realtime_event(
            {
                "type": "spc.analysis",
                "process_name": body.process_name,
                "mean": mean_value,
                "std_dev": std_dev,
                "ucl": ucl,
                "lcl": lcl,
                "violations": [violation.model_dump() for violation in violations],
                "timestamp": timestamp.isoformat(),
            }
        )

        return SPCDataResponse(
            mean=mean_value,
            std_dev=std_dev,
            ucl=ucl,
            lcl=lcl,
            violations=violations,
            ai_analysis=ai_analysis,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("SPC analysis failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SPC analysis failed") from exc


@router.get("/spc/history/{process_name}", response_model=SPCHistoryResponse)
async def get_spc_history(process_name: str) -> SPCHistoryResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT timestamp, measured_value, part_number, characteristic_name
                FROM measurements
                WHERE equipment_id = :process_name OR characteristic_name = :process_name
                ORDER BY timestamp DESC
                LIMIT 100
                """
            ),
            {"process_name": process_name},
        )
        rows = result.mappings().all()

    points = [
        SPCHistoryPoint(
            timestamp=row["timestamp"],
            value=float(row["measured_value"]),
            part_number=row.get("part_number"),
            characteristic_name=row.get("characteristic_name"),
        )
        for row in rows
    ]
    return SPCHistoryResponse(process_name=process_name, points=points)


@router.get("/spc/processes")
async def list_spc_processes() -> dict[str, Any]:
    """List the measurement series available to chart on the SPC monitor.

    Returns the distinct process identifiers (characteristic names) that have
    measurements, so the dashboard can offer a picker instead of making the
    engineer guess a name. Each name returned here works with
    ``/spc/history/{name}``.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT characteristic_name AS name,
                       count(*)            AS points,
                       max(timestamp)      AS latest
                FROM measurements
                WHERE characteristic_name IS NOT NULL AND characteristic_name <> ''
                GROUP BY characteristic_name
                ORDER BY max(timestamp) DESC
                LIMIT 50
                """
            )
        )
        rows = result.mappings().all()

    return {
        "processes": [
            {
                "name": row["name"],
                "points": int(row["points"]),
                "latest": row["latest"].isoformat() if row["latest"] else None,
            }
            for row in rows
        ]
    }


def _baseline_payload(process_name: str, b: Baseline | None, *, configured: bool | None = None) -> SpcBaselineResponse:
    if b is None:
        return SpcBaselineResponse(process_name=process_name, configured=False)
    return SpcBaselineResponse(
        process_name=process_name,
        configured=configured if configured is not None else True,
        ucl=b.ucl, cl=b.cl, lcl=b.lcl, sigma=b.sigma, n_points=b.n_points,
    )


@router.get("/spc/baseline/{process_name}", response_model=SpcBaselineResponse)
async def get_spc_baseline(process_name: str) -> SpcBaselineResponse:
    """Return the frozen baseline limits for a process (or configured=false if none)."""
    return _baseline_payload(process_name, await spc_baseline_store.get_baseline(process_name))


@router.post("/spc/baseline/{process_name}", response_model=SpcBaselineEstablishResponse)
async def set_spc_baseline(
    process_name: str,
    body: SpcBaselineEstablishRequest = Body(default_factory=SpcBaselineEstablishRequest),
) -> SpcBaselineEstablishResponse:
    """Establish (freeze) a baseline for a process from a stable, in-control window.

    Uses the provided ``measurements`` or, if omitted, the most recent ``window``
    persisted points. The window is validated (enough points, real variation, in
    control) before it is locked; pass ``force=true`` to override the in-control check.
    """
    if body.measurements is not None:
        values = [float(v) for v in body.measurements]
    else:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    """
                    SELECT measured_value
                    FROM measurements
                    WHERE equipment_id = :p OR characteristic_name = :p
                    ORDER BY timestamp DESC
                    LIMIT :lim
                    """
                ),
                {"p": process_name, "lim": body.window},
            )
            # DB returns newest-first; baseline math expects chronological order.
            values = [float(r["measured_value"]) for r in reversed(result.mappings().all())]

    result = compute_baseline(values, force=body.force)
    if result.ok and result.baseline is not None:
        await spc_baseline_store.save_baseline(process_name, result.baseline, created_by="spc_monitor")
        async with AsyncSessionLocal() as session:
            await _audit(
                session,
                actor="system",
                action="spc_baseline_set",
                entity_type="spc_process",
                entity_id=process_name,
                details={
                    "ucl": result.baseline.ucl,
                    "lcl": result.baseline.lcl,
                    "n_points": result.baseline.n_points,
                    "forced": body.force,
                },
            )
            await session.commit()

    return SpcBaselineEstablishResponse(
        ok=result.ok,
        reason=result.reason,
        process_name=process_name,
        baseline=_baseline_payload(process_name, result.baseline, configured=result.ok),
        violations=result.violations,
    )


@router.delete("/spc/baseline/{process_name}", response_model=SpcBaselineResponse)
async def clear_spc_baseline(process_name: str) -> SpcBaselineResponse:
    """Remove a process's frozen baseline (re-baseline after a known process change)."""
    if await spc_baseline_store.delete_baseline(process_name):
        async with AsyncSessionLocal() as session:
            await _audit(
                session,
                actor="system",
                action="spc_baseline_cleared",
                entity_type="spc_process",
                entity_id=process_name,
                details={},
            )
            await session.commit()
    return SpcBaselineResponse(process_name=process_name, configured=False)


@router.get("/audit/export")
async def export_audit(
    start: str | None = Query(None, description="ISO8601 start time"),
    end: str | None = Query(None, description="ISO8601 end time"),
    event_type: str | None = Query(None, description="Filter by event_type"),
    format: Literal["json", "csv"] = Query("json"),
):
    """Export audit events as JSON or CSV. Uses parameterized queries to avoid SQL injection."""
    from datetime import datetime, timedelta

    try:
        end_dt = datetime.fromisoformat(end) if end else datetime.now(timezone.utc)
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid end timestamp")
    try:
        start_dt = datetime.fromisoformat(start) if start else (end_dt - timedelta(days=30))
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid start timestamp")

    sql = text(
        """
        SELECT id, created_at, actor, event_type, component, input_hash, metadata, ip_address
        FROM audit_events
        WHERE created_at >= :start AND created_at <= :end
        AND (CAST(:event_type AS TEXT) IS NULL OR event_type = CAST(:event_type AS TEXT))
        ORDER BY created_at DESC
        LIMIT 10000
        """
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(sql, {"start": start_dt, "end": end_dt, "event_type": event_type})
        rows = result.mappings().all()

    items = [
        {
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
            "timestamp": row.get("created_at").isoformat() if row.get("created_at") else None,
            "id": str(row.get("id")) if row.get("id") else None,
            "actor": row.get("actor"),
            "event_type": row.get("event_type"),
            "component": row.get("component"),
            "input_hash": row.get("input_hash"),
            "metadata": row.get("metadata"),
            "ip_address": row.get("ip_address"),
        }
        for row in rows
    ]

    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id", "timestamp", "created_at", "actor", "event_type", "component", "input_hash", "ip_address", "metadata"])
        writer.writeheader()
        for it in items:
            writer.writerow({k: (json.dumps(v) if k == "metadata" and v is not None else v) for k, v in it.items()})
        buf.seek(0)
        return StreamingResponse(buf, media_type="text/csv")

    return items


@router.post("/integrations/qms/inspection-equipment", response_model=QMSInspectionEquipmentResponse)
async def receive_qms_inspection_equipment_event(
    body: QMSInspectionEquipmentEvent,
) -> QMSInspectionEquipmentResponse:
    event_id = body.event_id or str(uuid.uuid4())
    timestamp = _now()

    async with AsyncSessionLocal() as session:
        await _audit(
            session,
            actor=body.source_system,
            action="qms_equipment_event_received",
            entity_type="inspection_equipment",
            entity_id=body.equipment_id,
            details={
                "event_id": event_id,
                "fixture_id": body.fixture_id,
                "characteristic_name": body.characteristic_name,
                "operator_count": len(body.operator_ids),
                "measurement_count": len(body.measurements),
                "received_at": timestamp.isoformat(),
            },
        )
        await session.commit()

    await publish_realtime_event(
        {
            "type": "qms.event",
            "event_id": event_id,
            "equipment_id": body.equipment_id,
            "measurement_count": len(body.measurements),
            "source_system": body.source_system,
            "timestamp": timestamp.isoformat(),
        }
    )

    if not body.measurements:
        return QMSInspectionEquipmentResponse(
            event_id=event_id,
            accepted=True,
            grr_analysis_started=False,
            message="Equipment event accepted. Awaiting GR&R measurements.",
        )

    grr_result = await analyze_grr(
        GRRAnalyzeRequest(measurements=body.measurements, part_tolerance=body.part_tolerance)
    )
    return QMSInspectionEquipmentResponse(
        event_id=event_id,
        accepted=True,
        grr_analysis_started=True,
        grr_result=grr_result,
        message="Equipment event accepted and GR&R analysis completed.",
    )


@router.post("/integrations/mes/measurements", response_model=MESMeasurementResponse)
async def receive_mes_measurement_event(body: MESMeasurementEvent) -> MESMeasurementResponse:
    event_id = body.event_id or str(uuid.uuid4())
    timestamp = _now()

    async with AsyncSessionLocal() as session:
        await _audit(
            session,
            actor=body.source_system,
            action="mes_measurement_event_received",
            entity_type="spc_process",
            entity_id=body.process_name,
            details={
                "event_id": event_id,
                "process_name": body.process_name,
                "part_number": body.part_number,
                "characteristic_name": body.characteristic_name,
                "measurement_count": len(body.measurements),
                "received_at": timestamp.isoformat(),
            },
        )
        await session.commit()

    await publish_realtime_event(
        {
            "type": "mes.event",
            "event_id": event_id,
            "process_name": body.process_name,
            "measurement_count": len(body.measurements),
            "source_system": body.source_system,
            "timestamp": timestamp.isoformat(),
        }
    )

    analysis = await _analyze_spc_data_impl(
        SPCDataRequest(
            process_name=body.process_name,
            measurements=body.measurements,
            target=body.target,
            ucl=body.ucl,
            lcl=body.lcl,
        )
    )
    return MESMeasurementResponse(
        event_id=event_id,
        accepted=True,
        analysis=analysis,
        message="MES measurements accepted and SPC analysis completed.",
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary() -> DashboardSummaryResponse:
    async with AsyncSessionLocal() as session:
        grr_result = await session.execute(
            text(
                "SELECT COUNT(*) AS count, AVG(CASE WHEN grr_pct < 10 THEN 1.0 ELSE 0.0 END) AS pass_rate FROM grr_studies"
            )
        )
        grr_row = grr_result.mappings().first() or {"count": 0, "pass_rate": 0.0}

        active_alerts_result = await session.execute(
            text("SELECT COUNT(*) AS count FROM alerts WHERE status = 'active'")
        )
        active_alerts_row = active_alerts_result.mappings().first() or {"count": 0}

        violations_result = await session.execute(
            text(
                """
                SELECT id, timestamp, part_number, characteristic_name, violation_type, severity, measured_value
                FROM quality_violations
                ORDER BY timestamp DESC
                LIMIT 5
                """
            )
        )
        violation_rows = violations_result.mappings().all()

    total = int(grr_row.get("count") or 0)
    pass_rate = float(grr_row.get("pass_rate") or 0.0) * 100.0 if total else 0.0

    return DashboardSummaryResponse(
        total_grr_analyses=total,
        passing_rate=pass_rate,
        active_alerts_count=int(active_alerts_row.get("count") or 0),
        recent_violations=[dict(row) for row in violation_rows],
        last_updated=_now(),
    )


@router.post("/alerts/trigger", response_model=AlertTriggerResponse, status_code=status.HTTP_201_CREATED)
async def trigger_alert(body: AlertTriggerRequest) -> AlertTriggerResponse:
    timestamp = _now()
    async with AsyncSessionLocal() as session:
        alert_id = await _create_quality_alert(
            session,
            alert_type=body.type,
            severity=body.severity,
            message=body.message,
            process_name=body.process_name,
            payload={"source": "api", "triggered_by": "api"},
            timestamp=timestamp,
        )
        await session.commit()

    if alert_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alert could not be created (deduplication or dispatch failure)",
        )
    return AlertTriggerResponse(alert_id=str(alert_id), created_at=timestamp)


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    status_filter: Literal["active", "resolved"] | None = Query(default=None, alias="status"),
    severity: Literal["critical", "high", "medium", "low"] | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> AlertListResponse:
    conditions = []
    params: dict[str, Any] = {"limit": limit}
    if status_filter:
        conditions.append("status = :status")
        params["status"] = status_filter
    if severity:
        conditions.append("severity = :severity")
        params["severity"] = severity

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with AsyncSessionLocal() as session:
        count_result = await session.execute(
            text(f"SELECT COUNT(*) AS count FROM alerts {where_clause}"),
            {k: v for k, v in params.items() if k in {"status", "severity"}},
        )
        total_row = count_result.mappings().first() or {"count": 0}

        result = await session.execute(
            text(
                f"""
                SELECT id, type, severity, message, process_name, status,
                       COALESCE(created_at, resolved_at, now()) AS created_at, resolved_at
                FROM alerts
                {where_clause}
                ORDER BY COALESCE(created_at, resolved_at, now()) DESC
                LIMIT :limit
                """
            ),
            params,
        )
        rows = result.mappings().all()

    items: list[AlertResponse] = []
    for row in rows:
        row_data = dict(row)
        row_data["id"] = str(row_data["id"])
        items.append(AlertResponse.model_validate(row_data))

    return AlertListResponse(
        items=items,
        total=int(total_row.get("count") or 0),
        limit=limit,
    )


@router.put("/alerts/{alert_id}/resolve", response_model=AlertResolveResponse)
async def resolve_alert(alert_id: str, _user=Depends(require_role("admin"))) -> AlertResolveResponse:
    uuid_id, hex_id = _stored_alert_lookup_values(alert_id)

    resolved_at = _now()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM alerts WHERE id IN (:uuid_id, :hex_id)"),
            {"uuid_id": uuid_id, "hex_id": hex_id},
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

        stored_id = str(row["id"])

        await session.execute(
            text(
                """
                UPDATE alerts
                SET status = 'resolved', resolved_at = :resolved_at, resolved_by = :resolved_by
                WHERE id = :id
                """
            ),
            {"resolved_at": resolved_at, "resolved_by": "api", "id": stored_id},
        )
        await _audit(
            session,
            actor="system",
            action="alert_resolved",
            entity_type="alert",
            entity_id=stored_id,
            details={"status": "resolved"},
        )
        await session.commit()

    return AlertResolveResponse(alert_id=alert_id, resolved_at=resolved_at)


@router.post("/alerts/{alert_id}/feedback", response_model=AlertFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def record_alert_feedback(alert_id: str, body: AlertFeedbackRequest) -> AlertFeedbackResponse:
    uuid_id, hex_id = _stored_alert_lookup_values(alert_id)
    created_at = _now()
    feedback_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT id FROM alerts WHERE id IN (:uuid_id, :hex_id)"),
            {"uuid_id": uuid_id, "hex_id": hex_id},
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

        stored_alert_id = row["id"]
        session.add(
            AlertFeedback(
                id=feedback_id,
                alert_id=_coerce_uuid(stored_alert_id),
                is_relevant=body.is_relevant,
                category=body.category,
                notes=body.notes,
                submitted_by=body.submitted_by,
                created_at=created_at,
            )
        )
        await _audit(
            session,
            actor=body.submitted_by,
            action="alert_feedback_recorded",
            entity_type="alert",
            entity_id=str(stored_alert_id),
            details={
                "is_relevant": body.is_relevant,
                "category": body.category,
                "notes": body.notes,
            },
        )
        await session.commit()

    return AlertFeedbackResponse(
        feedback_id=str(feedback_id),
        alert_id=alert_id,
        is_relevant=body.is_relevant,
        created_at=created_at,
    )


@router.get("/alerts/accuracy", response_model=AlertAccuracyResponse)
async def get_alert_accuracy() -> AlertAccuracyResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS feedback_count,
                    SUM(CASE WHEN is_relevant THEN 1 ELSE 0 END) AS relevant_count,
                    SUM(CASE WHEN is_relevant THEN 0 ELSE 1 END) AS false_positive_count
                FROM alert_feedback
                """
            )
        )
        row = result.mappings().first() or {}

    feedback_count = int(row.get("feedback_count") or 0)
    relevant_count = int(row.get("relevant_count") or 0)
    false_positive_count = int(row.get("false_positive_count") or 0)
    accuracy_rate = (relevant_count / feedback_count) * 100.0 if feedback_count else None

    return AlertAccuracyResponse(
        feedback_count=feedback_count,
        relevant_count=relevant_count,
        false_positive_count=false_positive_count,
        accuracy_rate=accuracy_rate,
        target_met=accuracy_rate >= 95.0 if accuracy_rate is not None else None,
    )


@router.get("/audit-log", response_model=list[AuditLogResponse])
async def get_audit_log() -> list[AuditLogResponse]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT id, created_at, actor, action, entity_type, entity_id, details
                FROM audit_logs
                ORDER BY created_at DESC
                LIMIT 200
                """
            )
        )
        rows = result.mappings().all()

    audit_items: list[AuditLogResponse] = []
    for row in rows:
        details = row.get("details")
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except json.JSONDecodeError:
                details = {"raw": details}

        audit_items.append(
            AuditLogResponse(
                id=str(row["id"]),
                timestamp=row["created_at"],
                actor=row["actor"],
                action=row["action"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                details=details,
            )
        )

    return audit_items


@router.get("/audit-log/export")
async def export_audit_log_csv(
    format: Literal["csv", "json"] = Query(default="csv"),
):
    """Export audit log in compliance-ready format (CSV or JSON)."""
    from fastapi.responses import JSONResponse, StreamingResponse
    import io
    import csv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT id, created_at, actor, action, entity_type, entity_id, details
                FROM audit_logs
                ORDER BY created_at DESC
                LIMIT 10000
                """
            )
        )
        rows = result.mappings().all()

    if format == "json":
        items = []
        for row in rows:
            details = row.get("details")
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except json.JSONDecodeError:
                    details = {"raw": details}
            items.append({
                "id": str(row["id"]),
                "timestamp": str(row["created_at"]),
                "actor": row["actor"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "details": details,
            })
        return JSONResponse(content={"audit_log": items, "total": len(items)})

    # CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp", "actor", "action", "entity_type", "entity_id", "details"])
    for row in rows:
        details = row.get("details")
        if isinstance(details, dict):
            details = json.dumps(details)
        elif isinstance(details, str):
            pass
        else:
            details = str(details) if details else ""
        writer.writerow([
            str(row["id"]),
            str(row["created_at"]),
            row["actor"],
            row["action"],
            row["entity_type"],
            row["entity_id"],
            details,
        ])

    csv_bytes = output.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_log.csv"'},
    )


class CapabilityRequest(BaseModel):
    values: list[float] = Field(..., min_length=2)
    usl: float
    lsl: float
    subgroup_size: int = Field(1, ge=1)
    process_name: str = "unknown"


class CapabilityResponse(BaseModel):
    cp: float
    cpk: float
    pp: float
    ppk: float
    cpu: float
    cpl: float
    mean: float
    sigma_within: float
    sigma_overall: float
    ppm_total: float
    ai_analysis: str = ""


@router.post("/spc/capability", response_model=CapabilityResponse, status_code=status.HTTP_201_CREATED)
async def analyze_capability(body: CapabilityRequest) -> CapabilityResponse:
    """Calculate Cpk/Ppk process capability indices."""
    from spc.capability import capability_indices

    try:
        result = capability_indices(
            values=body.values,
            usl=body.usl,
            lsl=body.lsl,
            subgroup_size=body.subgroup_size,
        )

        ai_analysis = ""
        try:
            ai_analysis = await geminiService.analyzeSPCAnomaly({
                "analysis_type": "capability_study",
                "process_name": body.process_name,
                "cp": result.cp,
                "cpk": result.cpk,
                "pp": result.pp,
                "ppk": result.ppk,
                "ppm_total": result.ppm_total,
                "mean": result.mean,
                "usl": body.usl,
                "lsl": body.lsl,
            })
        except Exception:
            logger.warning("AI analysis unavailable for capability study")

        async with AsyncSessionLocal() as session:
            await _audit(
                session,
                actor="system",
                action="spc_capability_analysis",
                entity_type="spc_process",
                entity_id=body.process_name,
                details={
                    "cp": result.cp,
                    "cpk": result.cpk,
                    "pp": result.pp,
                    "ppk": result.ppk,
                    "ppm_total": result.ppm_total,
                },
            )
            await session.commit()

        return CapabilityResponse(
            cp=result.cp,
            cpk=result.cpk,
            pp=result.pp,
            ppk=result.ppk,
            cpu=result.cpu,
            cpl=result.cpl,
            mean=result.mean,
            sigma_within=result.sigma_within,
            sigma_overall=result.sigma_overall,
            ppm_total=result.ppm_total,
            ai_analysis=ai_analysis,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


class AnomalyDetectionRequest(BaseModel):
    values: list[float] = Field(..., min_length=5)
    cl: float
    sigma: float
    ucl: float
    lcl: float
    process_name: str = "unknown"


class AnomalyDetectionResponse(BaseModel):
    anomaly_detected: bool
    anomaly_score: float
    anomaly_indices: list[int]
    drift_detected: bool
    drift_direction: str
    drift_rate: float
    predicted_violation_in: int | None
    method: str
    details: dict[str, Any]


@router.post("/spc/anomaly-detect", response_model=AnomalyDetectionResponse, status_code=status.HTTP_201_CREATED)
async def detect_anomalies_endpoint(body: AnomalyDetectionRequest) -> AnomalyDetectionResponse:
    """Run statistical anomaly detection (EWMA + IQR + trend analysis)."""
    from spc.anomaly_detector import detect_anomalies

    result = detect_anomalies(
        values=body.values,
        cl=body.cl,
        sigma=body.sigma,
        ucl=body.ucl,
        lcl=body.lcl,
    )

    # Log to MLflow
    try:
        import mlflow
        mlflow.set_experiment("anomaly_detection")
        with mlflow.start_run(run_name=f"anomaly_{body.process_name}"):
            mlflow.log_metrics({
                "anomaly_score": result.anomaly_score,
                "drift_rate": result.drift_rate,
                "ewma_violations": result.details.get("ewma_violations", 0),
                "iqr_outliers": result.details.get("iqr_outliers", 0),
            })
            mlflow.set_tag("process_name", body.process_name)
            mlflow.set_tag("anomaly_detected", str(result.anomaly_detected))
    except Exception:
        logger.warning("MLflow logging failed for anomaly detection")

    async with AsyncSessionLocal() as session:
        await _audit(
            session,
            actor="system",
            action="anomaly_detection",
            entity_type="spc_process",
            entity_id=body.process_name,
            details={
                "anomaly_detected": result.anomaly_detected,
                "anomaly_score": result.anomaly_score,
                "drift_direction": result.drift_direction,
            },
        )

        if result.anomaly_detected and result.anomaly_score > 0.5:
            await _create_quality_alert(
                session,
                alert_type="trend_detected",
                severity="high" if result.anomaly_score > 0.7 else "medium",
                message=(
                    f"Statistical anomaly detected in {body.process_name}: "
                    f"score={result.anomaly_score:.2f}, drift={result.drift_direction}"
                ),
                process_name=body.process_name,
                payload={
                    "source": "anomaly_detector",
                    "anomaly_score": result.anomaly_score,
                    "drift_direction": result.drift_direction,
                    "predicted_violation_in": result.predicted_violation_in,
                },
                timestamp=_now(),
            )

        await session.commit()

    return AnomalyDetectionResponse(
        anomaly_detected=result.anomaly_detected,
        anomaly_score=result.anomaly_score,
        anomaly_indices=result.anomaly_indices,
        drift_detected=result.drift_detected,
        drift_direction=result.drift_direction,
        drift_rate=result.drift_rate,
        predicted_violation_in=result.predicted_violation_in,
        method=result.method,
        details=result.details,
    )
