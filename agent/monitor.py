"""
Continuous autonomous monitor — the always-on "quality engineer".

The ingestion consumer (``agent/consumer.py``) persists measurements and
broadcasts them, but it does not analyse them. This module closes that loop:
on a fixed interval it scans every active ``(part_number, characteristic_name)``
series that has received new data and runs SPC control-chart analysis
(Individuals / Moving-Range + the eight Nelson rules). When the most recent
measurement is out of statistical control it records a quality violation and the
``AlertEngine`` dispatches a proactive alert — with no endpoint call required.

Design notes:
  * Idempotent — a series is only re-analysed when new data has arrived, and a
    fresh critical violation is suppressed if one was already recorded for the
    same series within the last hour, so steady-state out-of-control conditions
    don't flood the violation table or the alert channels.
  * Resilient — every cycle and every per-series analysis is wrapped so one bad
    series (or a transient DB blip) never stops the loop.
  * Reuses the existing SPC engine and AlertEngine; it adds no new statistics.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import text

from agent.alert_engine import AlertEngine
from api.realtime import publish_realtime_event
from core.config import settings
from db.database import AsyncSessionLocal
from db.models import QualityViolation

logger = logging.getLogger(__name__)


class ContinuousMonitor:
    """Periodically analyse the live measurement stream and raise alerts."""

    def __init__(
        self,
        *,
        interval_seconds: int | None = None,
        window: int = 30,
        lookback_minutes: int = 180,
        min_points: int = 10,
        duplicate_suppression_minutes: int = 60,
    ) -> None:
        self.interval = (
            interval_seconds if interval_seconds is not None else settings.monitor_interval_seconds
        )
        self.window = window
        self.lookback = timedelta(minutes=lookback_minutes)
        self.min_points = min_points
        self.duplicate_suppression = timedelta(minutes=duplicate_suppression_minutes)
        self.alert_engine = AlertEngine()
        # Track the latest measurement timestamp we've already analysed per series.
        self._last_seen: dict[tuple[str, str], datetime] = {}

    # ── discovery ────────────────────────────────────────────────────────────

    async def discover_active_series(self, session) -> list[dict[str, Any]]:
        """Return series with at least one measurement inside the lookback window."""
        cutoff = datetime.now(timezone.utc) - self.lookback
        result = await session.execute(
            text(
                """
                SELECT part_number,
                       characteristic_name,
                       max(timestamp) AS latest,
                       count(*)       AS n
                FROM measurements
                WHERE timestamp > :cutoff
                GROUP BY part_number, characteristic_name
                """
            ),
            {"cutoff": cutoff},
        )
        return [dict(row) for row in result.mappings().all()]

    # ── per-series analysis ──────────────────────────────────────────────────

    async def analyze_series(self, part_number: str, characteristic_name: str) -> dict[str, Any]:
        """Analyse the most recent window for one series.

        Persists a single critical violation when the latest point is out of
        control (subject to duplicate suppression). Returns a summary dict.
        """
        from spc.control_charts import individuals_mr_chart
        from spc.nelson_rules import evaluate_all_rules

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    """
                    SELECT measured_value, timestamp
                    FROM measurements
                    WHERE part_number = :pn AND characteristic_name = :cn
                    ORDER BY timestamp DESC
                    LIMIT :lim
                    """
                ),
                {"pn": part_number, "cn": characteristic_name, "lim": self.window},
            )
            rows = result.mappings().all()
            if len(rows) < self.min_points:
                return {"status": "skipped", "reason": "insufficient_data", "points": len(rows)}

            # DB returns newest-first; analyse in chronological order.
            values = [float(r["measured_value"]) for r in reversed(rows)]
            i_chart, _ = individuals_mr_chart(values)
            chart_values = np.asarray(i_chart.points, dtype=float)

            # Prefer the frozen, validated baseline (Phase II) so the monitor and the
            # SPC page judge points against the SAME limits; fall back to limits from
            # this window when no baseline is set (Phase I).
            from core import spc_baseline_store

            baseline = await spc_baseline_store.get_baseline(characteristic_name)
            if baseline is not None:
                cl, sigma, ucl, lcl = baseline.cl, baseline.sigma, baseline.ucl, baseline.lcl
            else:
                cl, sigma = i_chart.limits.cl, i_chart.limits.sigma
                ucl, lcl = i_chart.limits.ucl, i_chart.limits.lcl
            violations = evaluate_all_rules(chart_values, cl, sigma)

            rule_1_hits = violations.get("rule_1", [])
            # Flag if ANY point in the analysed window breached the 3-sigma limits,
            # not just the most recent one — otherwise a batch upload (CSV / MES pull)
            # whose out-of-control reading isn't the final row would never alert.
            # Report the most recent offending point; the duplicate suppression below
            # keeps a lingering breach from re-alerting more than once per hour.
            ooc_index = max(rule_1_hits) if rule_1_hits else None
            out_of_control = ooc_index is not None

            persisted = 0
            if out_of_control and not await self._recently_recorded(
                session, part_number, characteristic_name
            ):
                session.add(
                    QualityViolation(
                        timestamp=datetime.now(timezone.utc),
                        part_number=part_number,
                        characteristic_name=characteristic_name,
                        violation_type="nelson_rule_1",
                        severity="critical",
                        measured_value=float(chart_values[ooc_index]),
                        ucl=ucl,
                        lcl=lcl,
                        alert_sent=False,
                    )
                )
                await session.commit()
                persisted = 1

        await self._broadcast(part_number, characteristic_name, i_chart, violations, persisted)

        return {
            "status": "analyzed",
            "points": len(values),
            "out_of_control": out_of_control,
            "rule_1_violations": persisted,
            "total_rule_hits": sum(len(v) for v in violations.values()),
            "ucl": i_chart.limits.ucl,
            "cl": i_chart.limits.cl,
            "lcl": i_chart.limits.lcl,
        }

    async def _recently_recorded(self, session, part_number: str, characteristic_name: str) -> bool:
        cutoff = datetime.now(timezone.utc) - self.duplicate_suppression
        result = await session.execute(
            text(
                """
                SELECT count(*) FROM quality_violations
                WHERE part_number = :pn
                  AND characteristic_name = :cn
                  AND violation_type = 'nelson_rule_1'
                  AND created_at > :cutoff
                """
            ),
            {"pn": part_number, "cn": characteristic_name, "cutoff": cutoff},
        )
        return (result.scalar() or 0) > 0

    async def _broadcast(self, part_number, characteristic_name, i_chart, violations, persisted) -> None:
        try:
            await publish_realtime_event(
                {
                    "type": "monitor.analysis",
                    "part_number": part_number,
                    "characteristic_name": characteristic_name,
                    "ucl": i_chart.limits.ucl,
                    "cl": i_chart.limits.cl,
                    "lcl": i_chart.limits.lcl,
                    "rule_1_violations": persisted,
                    "total_rule_hits": sum(len(v) for v in violations.values()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            logger.debug("monitor.broadcast_failed", exc_info=True)

    # ── scan + loop ──────────────────────────────────────────────────────────

    async def scan_once(self) -> dict[str, Any]:
        """Run a single monitoring pass over all active series."""
        async with AsyncSessionLocal() as session:
            series = await self.discover_active_series(session)

        analyzed = 0
        new_violations = 0
        for s in series:
            pn = s["part_number"]
            cn = s["characteristic_name"]
            latest = s["latest"]
            key = (pn, cn)
            prev = self._last_seen.get(key)
            if prev is not None and latest is not None and latest <= prev:
                continue  # nothing new since last scan
            try:
                summary = await self.analyze_series(pn, cn)
            except Exception:
                logger.exception("monitor.analyze_failed part=%s char=%s", pn, cn)
                continue
            if latest is not None:
                self._last_seen[key] = latest
            if summary.get("status") == "analyzed":
                analyzed += 1
                new_violations += summary.get("rule_1_violations", 0)

        # Always dispatch any unsent violations (from the monitor or the API).
        try:
            alerts_sent = await self.alert_engine.process_pending_violations()
        except Exception:
            logger.exception("monitor.alert_dispatch_failed")
            alerts_sent = 0

        summary = {
            "series_total": len(series),
            "series_analyzed": analyzed,
            "new_violations": new_violations,
            "alerts_sent": alerts_sent,
        }
        if analyzed or new_violations or alerts_sent:
            logger.info(
                "monitor.scan series_total=%s analyzed=%s new_violations=%s alerts_sent=%s",
                len(series),
                analyzed,
                new_violations,
                alerts_sent,
            )
        return summary

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        """Run :meth:`scan_once` every ``interval`` seconds until ``stop_event`` is set."""
        logger.info(
            "ContinuousMonitor started (interval=%ss window=%s min_points=%s)",
            self.interval,
            self.window,
            self.min_points,
        )
        while not stop_event.is_set():
            try:
                await self.scan_once()
            except Exception:
                logger.exception("monitor.cycle_failed")
            try:
                await asyncio.wait_for(asyncio.shield(stop_event.wait()), timeout=self.interval)
            except asyncio.TimeoutError:
                pass
        logger.info("ContinuousMonitor stopped")
