"""
Orchestrator — Central agent that coordinates quality-control workflows.

Responsibilities:
  1. Receive measurement events (Kafka / API).
  2. Dispatch to the appropriate analysis module (GR&R, SPC).
  3. Evaluate results against acceptance criteria.
  4. Trigger alerts (Slack, email) when out-of-spec conditions are detected.
  5. Log experiment runs to MLflow for traceability.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent.adapters.registry import get_adapter
import numpy as np
import pandas as pd
from sqlalchemy import text

from agent.alert_engine import AlertEngine
from api.realtime import publish_realtime_event
from core.config import settings
from db.database import AsyncSessionLocal
from db.models import QualityViolation

logger = logging.getLogger(__name__)


# ─── Domain models ────────────────────────────────────────────────────────────

@dataclass
class MeasurementEvent:
    """Incoming measurement payload from the shop floor."""

    part_id: str
    operator_id: str
    values: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Unified result envelope returned by every analysis module."""

    study_type: str  # "grr" | "spc"
    passed: bool
    summary: dict[str, Any] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)


# ─── Orchestrator ─────────────────────────────────────────────────────────────

class QualityOrchestrator:
    """
    Main agent loop that ties together GR&R studies, SPC monitoring,
    acceptance gating, alerting, and experiment tracking.
    """

    def __init__(self) -> None:
        self.alert_engine = AlertEngine()
        self.logger = logging.getLogger(__name__)
        self.logger.info("QualityOrchestrator initialised")

    # ── Kafka integration ────────────────────────────────────────────────────

    async def start_consumer_loop(self) -> None:
        """
        Long-running loop that polls Kafka for new measurement events
        and dispatches them to the appropriate handler.
        """
        from confluent_kafka import Consumer

        consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "group.id": "arad-quality-orchestrator",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        consumer.subscribe(["quality.measurements"])

        self.logger.info("Kafka consumer loop started on topic quality.measurements")
        try:
            while True:
                kafka_message = consumer.poll(timeout=1.0)
                if kafka_message is None:
                    continue
                if kafka_message.error():
                    self.logger.error("Kafka consumer error: %s", kafka_message.error())
                    continue

                try:
                    raw = kafka_message.value()
                    payload = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                    event = json.loads(payload)
                    await self.handle_measurement_event(event)
                    consumer.commit(message=kafka_message, asynchronous=False)
                except Exception:
                    self.logger.exception("Failed to process Kafka message")
        finally:
            consumer.close()

    # ── Event handling ───────────────────────────────────────────────────────

    async def handle_measurement_event(self, event: dict) -> dict:
        """
        Main entry point. Called for every Kafka message.
        event dict has keys: part_number, characteristic_name,
        measured_value, nominal_value, equipment_id, operator_id,
        shift, timestamp, and optionally study_type.
        """
        study_type = event.get("study_type", "spc")

        if study_type == "spc":
            return await self._handle_spc_event(event)
        if study_type == "grr":
            return await self._handle_grr_event(event)

        self.logger.warning(f"Unknown study_type: {study_type}")
        return {"status": "skipped", "reason": f"unknown study_type: {study_type}"}

    async def handle_event(self, event: MeasurementEvent) -> AnalysisResult:
        """
        Legacy adapter for MeasurementEvent payloads (tests / older callers).
        """
        payload: dict[str, Any] = {
            "part_number": event.part_id,
            "operator_id": event.operator_id,
            "measured_value": event.values[-1] if event.values else 0.0,
            "study_type": event.metadata.get("study_type", "spc"),
            **event.metadata,
        }
        if event.metadata.get("study_type") == "grr" and event.values:
            payload["measurements"] = event.metadata.get("measurements", [])

        result = await self.handle_measurement_event(payload)
        passed = result.get("status") == "processed" and result.get(
            "acceptance", "acceptable"
        ) in ("acceptable",)
        return AnalysisResult(
            study_type=result.get("study_type", "unknown"),
            passed=passed,
            summary=result,
        )

    async def _handle_spc_event(self, event: dict) -> dict:
        """
        For a single measurement event:
        1. Pull last 30 measurements for same part+characteristic from TimescaleDB
        2. Append the new measurement
        3. Run individuals_mr_chart on the window
        4. Run evaluate_all_rules on I-chart values
        5. Persist any Rule 1 violations to quality_violations
        6. Run alert_engine.process_pending_violations()
        7. Return summary dict
        """
        from spc.control_charts import individuals_mr_chart
        from spc.nelson_rules import evaluate_all_rules

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT measured_value FROM measurements
                    WHERE part_number = :pn AND characteristic_name = :cn
                    ORDER BY timestamp DESC LIMIT 30
                """),
                {"pn": event["part_number"], "cn": event["characteristic_name"]},
            )
            rows = result.scalars().all()
            values = list(reversed(rows)) + [event["measured_value"]]

            if len(values) < 5:
                return {
                    "status": "skipped",
                    "reason": "insufficient_history",
                    "count": len(values),
                }

            i_chart, _ = individuals_mr_chart(values)
            chart_values = np.array(i_chart.points)
            sigma = i_chart.limits.sigma

            violations = evaluate_all_rules(
                chart_values, i_chart.limits.cl, sigma
            )

            rule1 = violations.get("rule_1", [])
            if rule1:
                now = datetime.now(timezone.utc)
                for idx in rule1:
                    session.add(
                        QualityViolation(
                            timestamp=now,
                            part_number=event["part_number"],
                            characteristic_name=event["characteristic_name"],
                            violation_type="nelson_rule_1",
                            severity="critical",
                            measured_value=float(chart_values[idx]),
                            ucl=i_chart.limits.ucl,
                            lcl=i_chart.limits.lcl,
                            alert_sent=False,
                        )
                    )
                await session.commit()

        await self.alert_engine.process_pending_violations()

        # ── Predictive layer: CUSUM + EWMA ────────────────────────────────────
        from spc.cusum import cusum_from_limits
        from spc.ewma import ewma_from_limits
        from spc.anomaly_detector import linear_trend_extrapolation

        cusum_result = cusum_from_limits(chart_values, i_chart.limits.ucl, i_chart.limits.lcl)
        ewma_result = ewma_from_limits(chart_values, i_chart.limits.ucl, i_chart.limits.lcl)
        slope, drift_direction, obs_until = linear_trend_extrapolation(
            chart_values, i_chart.limits.ucl, i_chart.limits.lcl
        )

        # Emit predictive alert when breach is imminent (≤5 measurements away)
        if cusum_result.shift_detected:
            from agent.alert_manager import AlertManager, AlertEvent
            alert_ev = AlertEvent(
                type="spc_predicted_breach",
                severity="critical",
                message=(
                    f"CUSUM shift detected — {cusum_result.shift_direction} shift on "
                    f"{event.get('part_number')} / {event.get('characteristic_name')}. "
                    f"First signal at index {cusum_result.first_signal_index}."
                ),
                process_name=event.get("part_number", "unknown"),
                payload={
                    "part_number": event.get("part_number"),
                    "characteristic_name": event.get("characteristic_name"),
                    "shift_direction": cusum_result.shift_direction,
                    "first_signal_index": cusum_result.first_signal_index,
                },
            )
            await AlertManager().send(alert_ev)
        elif obs_until is not None and obs_until <= 5:
            from agent.alert_manager import AlertManager, AlertEvent
            alert_ev = AlertEvent(
                type="spc_predicted_breach",
                severity="warning",
                message=(
                    f"Predicted UCL/LCL breach in ~{obs_until} measurements — "
                    f"{drift_direction} drift on "
                    f"{event.get('part_number')} / {event.get('characteristic_name')}."
                ),
                process_name=event.get("part_number", "unknown"),
                payload={
                    "part_number": event.get("part_number"),
                    "characteristic_name": event.get("characteristic_name"),
                    "obs_until_breach": obs_until,
                    "drift_direction": drift_direction,
                },
            )
            await AlertManager().send(alert_ev)

        # Log prediction run to MLflow
        try:
            adapter = get_adapter()
            await adapter.log_experiment(
                experiment_name="spc_predictions",
                run_name=f"{event.get('part_number', 'unknown')}_{event.get('characteristic_name', 'unknown')}",
                params={
                    "model_type": "cusum+ewma",
                    "input_window": len(values),
                    "process_id": event.get("part_number", "unknown"),
                    "characteristic": event.get("characteristic_name", "unknown"),
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
                },
            )
        except Exception:
            self.logger.warning("MLflow SPC prediction logging failed (non-fatal)", exc_info=True)

        await publish_realtime_event(
            {
                "type": "spc.analysis",
                "part_number": event.get("part_number"),
                "characteristic_name": event.get("characteristic_name"),
                "measured_value": event.get("measured_value"),
                "values_used": len(values),
                "rule_1_violations": len(rule1),
                "total_violations": sum(len(v) for v in violations.values()),
                "cusum_shift_detected": cusum_result.shift_detected,
                "ewma_trend_detected": ewma_result.shift_detected,
                "predicted_breach_in": obs_until,
                "drift_direction": drift_direction,
                "timestamp": event.get("timestamp"),
                "source_event_id": event.get("event_id") or event.get("source_event_id"),
            }
        )

        return {
            "status": "processed",
            "study_type": "spc",
            "values_used": len(values),
            "rule_1_violations": len(rule1),
            "total_violations": sum(len(v) for v in violations.values()),
            "cusum_shift_detected": cusum_result.shift_detected,
            "ewma_trend_detected": ewma_result.shift_detected,
            "predicted_breach_in": obs_until,
            "drift_direction": drift_direction,
        }

    async def _handle_grr_event(self, event: dict) -> dict:
        """
        For a GR&R trigger event:
        The event must have a 'measurements' key — list of
        {part, operator, value} dicts for the full study.
        1. Run grr_xbar_r
        2. Run evaluate
        3. Persist to grr_studies
        4. If CONDITIONAL: add to review_queue + alert
        5. Log to MLflow
        6. Return summary
        """
        from grr.acceptance import evaluate
        from grr.calculator import grr_xbar_r

        measurements = event.get("measurements", [])
        if not measurements:
            return {"status": "error", "reason": "no measurements in GRR event"}

        df = pd.DataFrame(measurements)
        df = df.rename(columns={"value": "measurement"})

        result = grr_xbar_r(df)
        verdict = evaluate(result)
        study_id = str(uuid.uuid4())

        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO grr_studies
                    (id, equipment_id, characteristic_name, status,
                     ev, av, pv, grr_pct, ndc, acceptance_decision,
                     started_at, completed_at, created_by)
                    VALUES (:id, :eq, :cn, :status,
                            :ev, :av, :pv, :grr, :ndc, :decision,
                            NOW(), NOW(), 'orchestrator')
                """),
                {
                    "id": study_id,
                    "eq": event.get("equipment_id", "unknown"),
                    "cn": event.get("characteristic_name", "unknown"),
                    "status": verdict.level.value,
                    "ev": result.repeatability,
                    "av": result.reproducibility,
                    "pv": result.part_variation,
                    "grr": result.total_grr,
                    "ndc": result.ndc,
                    "decision": verdict.level.value,
                },
            )

            if verdict.requires_human_review:
                await session.execute(
                    text("""
                        INSERT INTO review_queue (study_id, status, created_at)
                        VALUES (:sid, 'pending', NOW())
                    """),
                    {"sid": study_id},
                )
                from agent.alert_manager import AlertManager, AlertEvent
                ev = AlertEvent(
                    type="grr_review_required",
                    severity="warning",
                    message=(
                        f"GR&R study requires human review.\n"
                        f"Equipment: {event.get('equipment_id')} | "
                        f"%GRR: {result.total_grr:.1f}% | NDC: {result.ndc}\n"
                        f"Review at: http://localhost:8000/docs#/reviews"
                    ),
                    process_name=event.get("equipment_id", "Unknown Equipment"),
                    payload={"study_id": study_id, "grr_percent": result.total_grr, "ndc": result.ndc},
                )
                await AlertManager().send(ev)

            await session.commit()

        await publish_realtime_event(
            {
                "type": "grr.analysis",
                "study_id": study_id,
                "equipment_id": event.get("equipment_id", "unknown"),
                "characteristic_name": event.get("characteristic_name", "unknown"),
                "grr_percent": result.total_grr,
                "acceptance": verdict.level.value,
                "requires_human_review": verdict.requires_human_review,
                "source_event_id": event.get("event_id") or event.get("source_event_id"),
            }
        )

        details = result.details or {}
        operators = [
            m.get("operator", "unknown")
            for m in measurements
            if isinstance(m, dict)
        ]
        unique_operators = sorted(set(operators))

        try:
            adapter = get_adapter()
            await adapter.log_experiment(
                experiment_name="grr_studies",
                run_name=study_id,
                params={
                    "method": details.get("method", "xbar_r"),
                    "n_operators": details.get("n_operators", len(unique_operators)),
                    "n_parts": details.get("n_parts", 0),
                    "n_trials": details.get("n_trials", 0),
                    "characteristic_name": event.get("characteristic_name", "unknown"),
                },
                metrics={
                    "grr_pct": result.total_grr,
                    "ndc": float(result.ndc),
                    "ev": result.repeatability,
                    "av": result.reproducibility,
                    "pv": result.part_variation,
                },
                tags={
                    "acceptance": verdict.level.value,
                    "pass_fail": "pass" if verdict.level.value == "acceptable" else "fail",
                    "equipment_id": event.get("equipment_id", "unknown"),
                    "operator_list": ",".join(unique_operators) if unique_operators else "unknown",
                },
            )
        except Exception as mlflow_exc:
            self.logger.warning("MLflow logging failed (non-fatal): %s", mlflow_exc)

        return {
            "status": "processed",
            "study_type": "grr",
            "study_id": study_id,
            "grr_percent": result.total_grr,
            "acceptance": verdict.level.value,
            "requires_human_review": verdict.requires_human_review,
        }

    # ── Alerting ─────────────────────────────────────────────────────────────

    async def _send_alert(self, message: str, severity: str = "warning") -> None:
        """Dispatch an alert to configured channels (Slack webhook)."""
        await send_slack_alert(
            settings.slack_webhook_url,
            message,
            severity=severity,
        )

    # ── Reporting ────────────────────────────────────────────────────────────

    async def generate_report(self, study_id: str) -> bytes:
        """
        Build a PDF report for a completed study and return raw bytes.
        """
        from grr.report_generator import create_pdf
        from grr.calculator import GRRResult
        from grr.acceptance import AcceptanceLevel, AcceptanceVerdict

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM grr_studies WHERE id = :id"),
                {"id": study_id},
            )
            row = result.mappings().first()
            if not row:
                raise ValueError(f"Study {study_id} not found")

        ev = row.get("ev") or 0.0
        av = row.get("av") or 0.0
        pv = row.get("pv") or 0.0
        grr = np.sqrt(ev**2 + av**2)
        tv = np.sqrt(grr**2 + pv**2)

        grr_result = GRRResult(
            total_grr=row.get("grr_pct") or 0.0,
            repeatability=ev,
            reproducibility=av,
            part_variation=pv,
            total_variation=tv,
            ndc=row.get("ndc") or 0,
            details={}
        )

        status_str = row.get("status", "not_acceptable")
        try:
            level = AcceptanceLevel(status_str)
        except ValueError:
            level = AcceptanceLevel.NOT_ACCEPTABLE

        verdict = AcceptanceVerdict(
            level=level,
            grr_percent=grr_result.total_grr,
            ndc=grr_result.ndc,
            ndc_adequate=grr_result.ndc >= 5,
            remarks=[f"Database status: {status_str}"],
            requires_human_review=(level == AcceptanceLevel.CONDITIONAL)
        )

        metadata = {
            "Study Date": str(row.get("created_at")),
            "Equipment ID": row.get("equipment_id"),
            "Characteristic": row.get("characteristic_name"),
            "Operators": row.get("operator_count"),
            "Parts": row.get("part_count"),
            "Generated By": "QualityOrchestrator"
        }

        return create_pdf(grr_result, verdict, study_metadata=metadata)
