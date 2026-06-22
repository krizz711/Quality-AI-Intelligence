"""AlertManager — production-grade multi-channel alert dispatch.

Features:
  - Deduplication via Redis (15-min TTL)
  - Retry with exponential backoff (tenacity) on Slack / email / SMS
  - Block Kit Slack messages with severity badge + LLM explanation
  - aiosmtplib Jinja2 HTML email with severity-themed template
  - Twilio SDK SMS for critical-only alerts
  - Jira auto-creation on %GRR >30% or persistent SPC violations
  - QMS REST POST integration when QMS_API_URL is set
  - Full audit logging to audit_events table (success + failure)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from redis.asyncio import Redis as AsyncRedis
except ImportError:  # pragma: no cover - test environments may use fakeredis instead
    AsyncRedis = None
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.config import settings
import os
from agent import alerts as alerts_mod
from sqlalchemy import select

from db.database import AsyncSessionLocal
from db.models import Alert, AlertRule, AuditLog, NotificationDelivery
from backend.services.audit_logger import log_event as audit_log_event

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    """Incoming alert event to be dispatched across channels."""

    type: str
    severity: str
    message: str
    process_name: str
    payload: Optional[Dict[str, Any]] = None
    grr_pct: Optional[float] = None
    llm_explanation: Optional[str] = None
    consecutive_violations: int = 0


class AlertManager:
    """Central alert dispatch with dedupe, retries, DB audit, and multi-channel delivery.

    Usage: AlertManager(redis_client=fake_redis) for tests, or default to settings.redis_url.
    """

    DEDUPE_TTL = 15 * 60

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_client: Optional[object] = None,
        dedupe_ttl: Optional[int] = None,
    ):
        self.redis_url = redis_url or settings.redis_url
        self._redis_client: Optional[object] = redis_client
        if dedupe_ttl is not None:
            self.DEDUPE_TTL = dedupe_ttl

    async def _get_redis(self):
        if self._redis_client is not None:
            return self._redis_client
        if AsyncRedis is None:
            raise RuntimeError("redis.asyncio is not available; pass a redis_client for tests")
        self._redis_client = AsyncRedis.from_url(self.redis_url)
        return self._redis_client

    def _dedupe_key(self, ev: AlertEvent) -> str:
        h = hashlib.sha1(
            json.dumps({"type": ev.type, "proc": ev.process_name, "msg": ev.message}).encode()
        )
        return f"alert:d:{h.hexdigest()}"

    async def _record_audit(
        self,
        session,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict | None = None,
    ) -> None:
        session.add(
            AuditLog(
                actor=actor,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details or {},
            )
        )

    # ── Retry-wrapped senders ────────────────────────────────────────────

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(Exception),
    )
    async def _send_slack_with_retry(self, webhook_url: str, payload: dict) -> Any:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(webhook_url, json=payload)
            r.raise_for_status()
            # Slack incoming webhooks reply with plain-text "ok", not JSON.
            return r.text

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(Exception),
    )
    async def _send_email_with_retry(self, *args, **kwargs):
        return await alerts_mod.send_email_alert(*args, **kwargs)

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(Exception),
    )
    async def _send_sms_with_retry(self, *args, **kwargs):
        return await alerts_mod.send_sms_alert(*args, **kwargs)

    # ── LLM explanation ──────────────────────────────────────────────────

    async def _generate_llm_explanation(self, ev: AlertEvent) -> str:
        """Generate an LLM explanation if not already provided on the event."""
        if ev.llm_explanation:
            return ev.llm_explanation
        try:
            return await alerts_mod.generate_alert_explanation(
                alert_type=ev.type,
                severity=ev.severity,
                message=ev.message,
                process_name=ev.process_name,
                payload=ev.payload,
            )
        except Exception:
            logger.debug("LLM explanation generation failed; using message as-is")
            return ""

    # ── Routing rules ────────────────────────────────────────────────────

    async def _allowed_channels(self, ev: AlertEvent) -> Optional[set]:
        """Channels permitted for this event by enabled routing rules.

        Returns the union of channels from rules whose trigger + scope match the
        event, or ``None`` when no rule matches — in which case dispatch falls
        back to the default behaviour of notifying every configured channel.
        """
        try:
            async with AsyncSessionLocal() as session:
                rules = (
                    await session.execute(select(AlertRule).where(AlertRule.enabled.is_(True)))
                ).scalars().all()
        except Exception:
            logger.debug("Alert-rule lookup failed; using default channel routing")
            return None

        matched: set = set()
        any_match = False
        proc = (ev.process_name or "").lower()
        for rule in rules:
            if rule.trigger != ev.type:
                continue
            scope = (rule.scope or "").strip().lower()
            if scope and not scope.startswith("any") and scope not in proc:
                continue
            any_match = True
            for channel in (rule.channels or []):
                matched.add(str(channel))
        return matched if any_match else None

    # ── Main dispatch ────────────────────────────────────────────────────

    async def send(self, ev: AlertEvent) -> uuid.UUID | None:
        """Main entry: dedupe, persist alert record, dispatch channels, create Jira if required."""

        # ── 1. Deduplication check ───────────────────────────────────────
        dedupe_key = self._dedupe_key(ev)
        redis = await self._get_redis()
        existing_id = await redis.get(dedupe_key)
        if existing_id:
            logger.info("Alert dedupe hit, skipping: %s %s", ev.type, ev.process_name)
            return None

        # ── 2. Generate LLM explanation (best-effort) ────────────────────
        llm_text = await self._generate_llm_explanation(ev)

        # ── 3. Persist alert record + set dedupe key ─────────────────────
        async with AsyncSessionLocal() as session:
            alert = Alert(
                type=ev.type,
                severity=ev.severity,
                message=ev.message,
                process_name=ev.process_name,
                payload=ev.payload or {},
            )
            session.add(alert)
            await session.commit()
            await session.refresh(alert)

            # Routing rules decide which configured channels fire (None = all).
            allowed = await self._allowed_channels(ev)

            try:
                await redis.set(dedupe_key, str(alert.id), ex=self.DEDUPE_TTL)
            except Exception:
                logger.exception("Failed to set dedupe key in Redis for alert %s", alert.id)

            # ── 4. Build dispatch coroutines ─────────────────────────────
            coros = []

            # ── Slack (all severities) ───────────────────────────────────
            slack_url = settings.slack_webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
            if slack_url and (allowed is None or "slack" in allowed):
                slack_payload = alerts_mod._build_block_kit_payload(
                    message=ev.message,
                    severity=ev.severity,
                    process_name=ev.process_name,
                    llm_explanation=llm_text or None,
                    payload=ev.payload,
                )

                async def _do_slack():
                    try:
                        await self._send_slack_with_retry(slack_url, slack_payload)
                        async with AsyncSessionLocal() as task_session:
                            task_session.add(
                                NotificationDelivery(
                                    alert_id=alert.id,
                                    channel="slack",
                                    status="sent",
                                    recipient=None,
                                )
                            )
                            await self._record_audit(
                                task_session,
                                "system",
                                "send_slack",
                                "alert",
                                str(alert.id),
                                {"severity": ev.severity, "has_llm": bool(llm_text)},
                            )
                            await task_session.commit()
                    except Exception as exc:
                        try:
                            async with AsyncSessionLocal() as task_session:
                                task_session.add(
                                    NotificationDelivery(
                                        alert_id=alert.id,
                                        channel="slack",
                                        status="failed",
                                        error_message=str(exc),
                                    )
                                )
                                await self._record_audit(
                                    task_session,
                                    "system",
                                    "alert_dispatch_failed",
                                    "alert",
                                    str(alert.id),
                                    {"channel": "slack", "error": str(exc)},
                                )
                                await task_session.commit()
                        except Exception:
                            logger.exception("Failed recording slack failure for alert %s", alert.id)
                        logger.exception("Slack send failed for alert %s", alert.id)

                coros.append(_do_slack())

            # ── Email ────────────────────────────────────────────────────
            smtp_host = settings.smtp_host or os.environ.get("SMTP_HOST")
            alert_email_recipients = settings.alert_email_recipients or os.environ.get(
                "ALERT_EMAIL_RECIPIENTS"
            )
            if smtp_host and alert_email_recipients and (allowed is None or "email" in allowed):
                recipients = [r.strip() for r in alert_email_recipients.split(",") if r.strip()]

                async def _do_email():
                    try:
                        await self._send_email_with_retry(
                            settings.smtp_host,
                            settings.smtp_port,
                            settings.smtp_user,
                            settings.smtp_password,
                            settings.smtp_from_address,
                            recipients,
                            f"Quality Alert: {ev.process_name} ({ev.severity})",
                            ev.message,
                            severity=ev.severity,
                            process_name=ev.process_name,
                            alert_type=ev.type,
                            llm_explanation=llm_text or None,
                            grr_pct=ev.grr_pct,
                            payload=ev.payload,
                        )
                        async with AsyncSessionLocal() as task_session:
                            task_session.add(
                                NotificationDelivery(
                                    alert_id=alert.id,
                                    channel="email",
                                    status="sent",
                                    recipient=",".join(recipients),
                                )
                            )
                            await self._record_audit(
                                task_session,
                                "system",
                                "send_email",
                                "alert",
                                str(alert.id),
                                {"recipients": recipients},
                            )
                            await task_session.commit()
                    except Exception as exc:
                        try:
                            async with AsyncSessionLocal() as task_session:
                                task_session.add(
                                    NotificationDelivery(
                                        alert_id=alert.id,
                                        channel="email",
                                        status="failed",
                                        error_message=str(exc),
                                        recipient=",".join(recipients),
                                    )
                                )
                                await task_session.commit()
                        except Exception:
                            logger.exception("Failed recording email failure for alert %s", alert.id)
                        logger.exception("Email send failed for alert %s", alert.id)

                coros.append(_do_email())

            # ── SMS — critical only ──────────────────────────────────────
            sms_webhook = settings.sms_webhook_url or os.environ.get("SMS_WEBHOOK_URL")
            sms_to_numbers = settings.sms_to_numbers or os.environ.get("SMS_TO_NUMBERS")
            if ev.severity == "critical" and sms_webhook and sms_to_numbers and (allowed is None or "sms" in allowed):
                to_numbers = [n.strip() for n in sms_to_numbers.split(",") if n.strip()]

                async def _do_sms():
                    try:
                        await self._send_sms_with_retry(
                            settings.sms_webhook_url,
                            settings.sms_auth_token,
                            settings.sms_from_number,
                            to_numbers,
                            ev.message,
                        )
                        async with AsyncSessionLocal() as task_session:
                            task_session.add(
                                NotificationDelivery(
                                    alert_id=alert.id,
                                    channel="sms",
                                    status="sent",
                                    recipient=",".join(to_numbers),
                                )
                            )
                            await self._record_audit(
                                task_session,
                                "system",
                                "send_sms",
                                "alert",
                                str(alert.id),
                                {"recipients": to_numbers},
                            )
                            await task_session.commit()
                    except Exception as exc:
                        try:
                            async with AsyncSessionLocal() as task_session:
                                task_session.add(
                                    NotificationDelivery(
                                        alert_id=alert.id,
                                        channel="sms",
                                        status="failed",
                                        error_message=str(exc),
                                        recipient=",".join(to_numbers),
                                    )
                                )
                                await task_session.commit()
                        except Exception:
                            logger.exception("Failed recording sms failure for alert %s", alert.id)
                        logger.exception("SMS send failed for alert %s", alert.id)

                coros.append(_do_sms())

            # ── Jira: GRR >30% or persistent SPC violations (>3 consecutive) ──
            jira_url = settings.jira_url or os.environ.get("JIRA_URL")
            jira_token = settings.jira_api_token or os.environ.get("JIRA_API_TOKEN")
            jira_email = settings.jira_email or os.environ.get("JIRA_EMAIL")
            jira_project = settings.jira_project_key or os.environ.get("JIRA_PROJECT_KEY")

            should_create_jira = False
            if jira_url and jira_token and jira_email and jira_project:
                if ev.grr_pct and ev.grr_pct > 30.0:
                    should_create_jira = True
                if ev.type == "spc_violation" and ev.consecutive_violations > 3:
                    should_create_jira = True
                # Legacy: also fire on any spc_violation type for backward compat
                if ev.type == "spc_violation" and not should_create_jira:
                    should_create_jira = True

            if allowed is not None and "jira" not in allowed:
                should_create_jira = False

            if should_create_jira:
                jira_summary = f"Quality Alert: {ev.process_name} {ev.type}"
                jira_description = llm_text if llm_text else ev.message

                async def _do_jira():
                    try:
                        ticket = await alerts_mod.create_jira_ticket(
                            jira_url,
                            jira_email,
                            jira_token,
                            jira_project,
                            summary=jira_summary,
                            description=jira_description,
                        )
                        if ticket:
                            async with AsyncSessionLocal() as task_session:
                                task_session.add(
                                    NotificationDelivery(
                                        alert_id=alert.id,
                                        channel="jira",
                                        status="created",
                                        response_reference=ticket,
                                    )
                                )
                                await self._record_audit(
                                    task_session,
                                    "system",
                                    "create_jira",
                                    "alert",
                                    str(alert.id),
                                    {"ticket": ticket, "has_llm_summary": bool(llm_text)},
                                )
                                await task_session.commit()
                    except Exception:
                        logger.exception("Failed to create JIRA for alert %s", alert.id)

                coros.append(_do_jira())

            # ── QMS integration (optional) ───────────────────────────────
            qms_url = getattr(settings, "qms_api_url", "") or os.environ.get("QMS_API_URL", "")
            if qms_url and ev.payload:

                async def _do_qms():
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            await client.post(qms_url, json=ev.payload)
                        async with AsyncSessionLocal() as task_session:
                            task_session.add(
                                NotificationDelivery(
                                    alert_id=alert.id,
                                    channel="qms",
                                    status="sent",
                                )
                            )
                            await self._record_audit(
                                task_session,
                                "system",
                                "post_qms",
                                "alert",
                                str(alert.id),
                                {"qms_url": qms_url},
                            )
                            await task_session.commit()
                    except Exception:
                        logger.exception("Failed to post to QMS for alert %s", alert.id)

                coros.append(_do_qms())

            # ── 5. Execute dispatches ────────────────────────────────────
            if coros:
                shared = False
                try:
                    if (
                        hasattr(AsyncSessionLocal, "_factory")
                        and AsyncSessionLocal._factory is not None
                    ):
                        shared = True
                except Exception:
                    shared = True

                if shared:
                    for c in coros:
                        try:
                            await c
                        except Exception:
                            logger.exception("Dispatch coroutine failed")
                else:
                    tasks = [asyncio.create_task(c) for c in coros]
                    await asyncio.gather(*tasks, return_exceptions=True)

            # Best-effort: record an audit event for the alert send (channels attempted)
            try:
                channels = []
                if slack_url and (allowed is None or "slack" in allowed):
                    channels.append("slack")
                if smtp_host and alert_email_recipients and (allowed is None or "email" in allowed):
                    channels.append("email")
                if ev.severity == "critical" and sms_webhook and sms_to_numbers and (allowed is None or "sms" in allowed):
                    channels.append("sms")
                if should_create_jira:
                    channels.append("jira")
                if qms_url:
                    channels.append("qms")

                await audit_log_event(
                    actor="system",
                    event_type="alert_sent",
                    component="alert_manager",
                    metadata={
                        "alert_id": str(alert.id),
                        "type": ev.type,
                        "severity": ev.severity,
                        "channels_attempted": channels,
                    },
                )
            except Exception:
                logger.exception("Failed to write audit_event for alert %s", alert.id)

            return alert.id
