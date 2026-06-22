"""
Alert engine — reads pending quality violations and dispatches Slack/JIRA alerts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from agent.alert_manager import AlertEvent, AlertManager
from core.config import settings
from db.database import AsyncSessionLocal
from db.models import QualityViolation

logger = logging.getLogger(__name__)


class AlertEngine:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.alert_manager = AlertManager()

    async def process_pending_violations(self, session=None) -> int:
        """
        Reads all unsent violations from DB, scores them,
        deduplicates, and dispatches alerts.
        Returns count of alerts sent.
        """
        own_session = session is None
        if own_session:
            session = AsyncSessionLocal()

        try:
            # STEP 1: Query all unsent violations
            result = await session.execute(
                text(
                    "SELECT * FROM quality_violations "
                    "WHERE alert_sent = FALSE ORDER BY created_at ASC"
                )
            )
            violations = result.mappings().all()
            self.logger.info(f"Found {len(violations)} unsent violations")

            sent_count = 0
            for v in violations:
                # STEP 2: Score severity
                severity = self._score_severity(v["violation_type"])

                # STEP 3: Dedup check — skip if same part+characteristic alerted in last 4 hours
                if await self._is_duplicate(
                    session, v["part_number"], v["characteristic_name"]
                ):
                    self.logger.info(
                        f"Dedup skip: {v['part_number']} {v['characteristic_name']}"
                    )
                    continue

                # STEP 4: Build message
                message = (
                    f"Quality violation detected on {v['part_number']} — "
                    f"{v['characteristic_name']}\n"
                    f"Type: {v['violation_type']} | "
                    f"Value: {v['measured_value']:.4f} | "
                    f"UCL: {v['ucl']:.4f} | LCL: {v['lcl']:.4f}"
                )

                # STEP 5: Use AlertManager to dispatch
                ev = AlertEvent(
                    type="spc_violation",
                    severity=severity,
                    message=message,
                    process_name=f"{v.get('part_number')}:{v.get('characteristic_name')}",
                    payload={"violation_id": str(v.get("id"))},
                )
                await self.alert_manager.send(ev)

                # STEP 7: Mark alert_sent = True
                await session.execute(
                    text("UPDATE quality_violations SET alert_sent=TRUE WHERE id=:id"),
                    {"id": str(v["id"])},
                )
                await session.commit()
                sent_count += 1

            self.logger.info(f"Alert engine: sent {sent_count} alerts")
            return sent_count

        except Exception as e:
            self.logger.error(f"Alert engine error: {e}")
            await session.rollback()
            return 0
        finally:
            if own_session:
                await session.close()

    def _score_severity(self, violation_type: str) -> str:
        """
        nelson_rule_1 = critical (point outside 3 sigma — immediate problem)
        nelson_rule_2 = warning  (shift — serious but not immediate)
        nelson_rule_3 = warning  (trend — catch before it becomes critical)
        all others    = info
        """
        if violation_type == "nelson_rule_1":
            return "critical"
        if violation_type in ("nelson_rule_2", "nelson_rule_3"):
            return "warning"
        return "info"

    async def _is_duplicate(
        self, session, part_number: str | None, characteristic_name: str | None
    ) -> bool:
        """
        Returns True if an alert was already sent for this
        part+characteristic in the last 4 hours.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=4)
        result = await session.execute(
            text("""
                SELECT COUNT(*) FROM quality_violations
                WHERE part_number = :pn
                AND characteristic_name = :cn
                AND alert_sent = TRUE
                AND created_at > :cutoff
            """),
            {"pn": part_number, "cn": characteristic_name, "cutoff": cutoff},
        )
        count = result.scalar()
        return (count or 0) > 0
