"""
Async alerting via Slack webhooks, JIRA REST API, aiosmtplib email, and Twilio SMS.

Production-grade: Block Kit formatting, Jinja2 HTML emails, retry-safe,
and never raises to callers (all functions return True / None).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SEVERITY_COLORS: dict[str, str] = {
    "info": "#36a64f",
    "warning": "#ffcc00",
    "critical": "#ff0000",
    "high": "#e65100",
    "low": "#90a4ae",
    "medium": "#fb8c00",
}

_SEVERITY_EMOJI: dict[str, str] = {
    "critical": "🔴",
    "high": "🟠",
    "warning": "🟡",
    "medium": "🟡",
    "info": "🔵",
    "low": "⚪",
}

# ─── Jinja2 template setup ──────────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).parent / "templates"

try:
    from jinja2 import Environment, FileSystemLoader

    _jinja_env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )
except ImportError:
    _jinja_env = None  # type: ignore[assignment]
    logger.warning("jinja2 not installed — HTML email templates will use plain-text fallback")


def _render_email_html(context: dict[str, Any]) -> str:
    """Render the alert_email.html template; fall back to plain text."""
    if _jinja_env is not None:
        try:
            tmpl = _jinja_env.get_template("alert_email.html")
            return tmpl.render(**context)
        except Exception:
            logger.warning("Failed to render Jinja2 template; using plain-text fallback")

    # Fallback
    lines = [
        f"Quality Alert — {context.get('severity', 'UNKNOWN').upper()}",
        f"Process: {context.get('process_name', 'N/A')}",
        f"Message: {context.get('message', '')}",
    ]
    if context.get("llm_explanation"):
        lines.append(f"\nAI Analysis: {context['llm_explanation']}")
    return "\n".join(lines)


# ─── Slack ───────────────────────────────────────────────────────────────────

def _build_block_kit_payload(
    message: str,
    severity: str,
    process_name: str = "",
    study_id: str | None = None,
    llm_explanation: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Slack Block Kit message with severity badge, fields, and AI box."""
    emoji = _SEVERITY_EMOJI.get(severity, "⚪")
    color = _SEVERITY_COLORS.get(severity, "#cccccc")

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} Quality Alert — {severity.upper()}", "emoji": True},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message},
        },
    ]

    # Metadata fields
    fields = []
    if process_name:
        fields.append({"type": "mrkdwn", "text": f"*Process:*\n{process_name}"})
    if study_id:
        fields.append({"type": "mrkdwn", "text": f"*Study ID:*\n{study_id}"})
    if payload:
        rule = payload.get("rule") if isinstance(payload, dict) else None
        if rule:
            fields.append({"type": "mrkdwn", "text": f"*Rule:*\n{rule}"})
        grr = payload.get("grr_percent") if isinstance(payload, dict) else None
        if grr is not None:
            fields.append({"type": "mrkdwn", "text": f"*%GRR:*\n{grr:.1f}%"})

    if fields:
        blocks.append({"type": "section", "fields": fields})

    # LLM explanation box
    if llm_explanation:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"🤖 *AI Analysis:*\n_{llm_explanation}_"},
        })

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Arad Quality Agent • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"},
        ],
    })

    return {
        "blocks": blocks,
        "attachments": [{"color": color, "blocks": []}],
    }


async def send_slack_alert(
    webhook_url: str,
    message: str,
    severity: str,
    study_id: str | None = None,
    llm_explanation: str | None = None,
    process_name: str = "",
    payload: dict[str, Any] | None = None,
) -> bool | None:
    """Post a Block Kit formatted message to a Slack incoming webhook.

    Returns True on success, None on missing config or failure (never raises).
    """
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not configured")
        return None

    body = _build_block_kit_payload(
        message=message,
        severity=severity,
        process_name=process_name,
        study_id=study_id,
        llm_explanation=llm_explanation,
        payload=payload,
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=body)
            response.raise_for_status()
        logger.info("Slack alert sent: %s — %s", severity, message[:60])
        return True
    except (httpx.HTTPError, Exception) as exc:
        logger.error("Failed to send Slack alert: %s", exc)
        return None


# ─── JIRA ────────────────────────────────────────────────────────────────────

async def create_jira_ticket(
    jira_url: str,
    email: str,
    api_token: str,
    project_key: str,
    summary: str,
    description: str,
) -> str | None:
    """Create a JIRA issue via REST API v3.

    Returns the ticket key (e.g. QUAL-42) on success, None on failure (never raises).
    """
    if not jira_url or not api_token:
        logger.warning("JIRA URL or API token not configured")
        return None

    url = f"{jira_url.rstrip('/')}/rest/api/3/issue"
    auth = httpx.BasicAuth(email, api_token)
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": "Bug"},
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                json=payload,
                auth=auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            ticket_key = response.json()["key"]
        logger.info("JIRA ticket created: %s", ticket_key)
        return ticket_key
    except (httpx.HTTPError, Exception) as exc:
        logger.error("Failed to create JIRA ticket: %s", exc)
        return None


# ─── Email (aiosmtplib + Jinja2) ────────────────────────────────────────────

async def send_email_alert(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_address: str,
    recipients: list[str],
    subject: str,
    body: str,
    severity: str = "info",
    process_name: str = "",
    alert_type: str = "",
    llm_explanation: str | None = None,
    grr_pct: float | None = None,
    payload: dict[str, Any] | None = None,
    dashboard_url: str = "",
) -> bool | None:
    """Send an alert email via aiosmtplib with Jinja2 HTML template.

    Falls back to synchronous smtplib + plain text if aiosmtplib is unavailable.
    Returns True on success, None on missing config or failure (never raises).
    """
    if not smtp_host or not recipients:
        logger.warning("SMTP not configured — email alert skipped")
        return None

    # Build the HTML body
    html_context = {
        "severity": severity,
        "message": body,
        "process_name": process_name or subject,
        "alert_type": alert_type,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "llm_explanation": llm_explanation,
        "grr_pct": grr_pct,
        "payload": payload or {},
        "dashboard_url": dashboard_url,
    }
    html_body = _render_email_html(html_context)

    # Build MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Try aiosmtplib first (truly async)
    try:
        import aiosmtplib

        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user or None,
            password=smtp_password or None,
            start_tls=smtp_port != 25,
            timeout=15,
        )
        logger.info("Email alert sent (aiosmtplib) to %s — %s", recipients, subject[:60])
        return True
    except ImportError:
        logger.debug("aiosmtplib not available; falling back to smtplib")
    except Exception as exc:
        logger.error("aiosmtplib send failed: %s — trying smtplib fallback", exc)

    # Fallback: synchronous smtplib in a thread
    import asyncio
    import smtplib

    def _send_sync() -> bool:
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                if smtp_port != 25:
                    server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.sendmail(from_address, recipients, msg.as_string())
            return True
        except Exception as exc2:
            logger.error("smtplib fallback failed: %s", exc2)
            return False

    try:
        result = await asyncio.to_thread(_send_sync)
        if result:
            logger.info("Email alert sent (smtplib) to %s — %s", recipients, subject[:60])
        return result or None
    except Exception as exc:
        logger.error("Email alert thread failed: %s", exc)
        return None


# ─── SMS (Twilio SDK) ────────────────────────────────────────────────────────

async def send_sms_alert(
    webhook_url: str,
    auth_token: str,
    from_number: str,
    to_numbers: list[str],
    message: str,
) -> bool | None:
    """Send SMS alerts via Twilio Python SDK (preferred) or generic webhook fallback.

    Returns True on success, None on missing config or failure (never raises).
    """
    if not webhook_url or not to_numbers:
        logger.warning("SMS webhook not configured — SMS alert skipped")
        return None

    # Try Twilio SDK first
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN", auth_token)
    if twilio_sid and twilio_token:
        try:
            import asyncio
            from twilio.rest import Client as TwilioClient

            def _send_twilio() -> bool:
                client = TwilioClient(twilio_sid, twilio_token)
                for number in to_numbers:
                    client.messages.create(
                        body=message[:160],
                        from_=from_number,
                        to=number,
                    )
                return True

            result = await asyncio.to_thread(_send_twilio)
            logger.info("SMS alert sent (Twilio SDK) to %s", to_numbers)
            return result
        except ImportError:
            logger.debug("Twilio SDK not installed; using webhook fallback")
        except Exception as exc:
            logger.error("Twilio SDK failed: %s — trying webhook fallback", exc)

    # Webhook fallback (Twilio-compatible REST)
    payload = {
        "from": from_number,
        "to": to_numbers,
        "body": message[:160],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload, headers=headers)
            response.raise_for_status()
        logger.info("SMS alert sent (webhook) to %s — %s", to_numbers, message[:40])
        return True
    except (httpx.HTTPError, Exception) as exc:
        logger.error("Failed to send SMS alert: %s", exc)
        return None


# ─── LLM Explanation Generator ──────────────────────────────────────────────

async def generate_alert_explanation(
    alert_type: str,
    severity: str,
    message: str,
    process_name: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """Use Gemini to generate a natural-language explanation for an alert.

    Returns an explanation string, or a sensible fallback if the LLM call fails.
    """
    try:
        from backend.services.gemini_service import _generate_text, _build_prompt

        prompt = _build_prompt(
            "alert explanation",
            {
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "process_name": process_name,
                "extra": payload or {},
            },
            (
                "Generate a concise 2-3 sentence explanation of this quality alert "
                "for a manufacturing quality engineer.  Explain what happened, why it "
                "matters, and what the engineer should do next.  Be specific and actionable."
            ),
        )
        return await _generate_text(prompt)
    except Exception as exc:
        logger.debug("LLM explanation unavailable (%s); using rule-based fallback", exc)

    # Rule-based fallback
    if "grr" in alert_type.lower():
        grr_pct = (payload or {}).get("grr_percent", (payload or {}).get("grr_pct", "unknown"))
        return (
            f"The GR&R study for {process_name} shows {grr_pct}% total gauge variation, "
            f"exceeding the 30% AIAG threshold.  The measurement system cannot reliably "
            f"distinguish between parts.  Recalibrate the gauge and retrain operators."
        )
    if "spc" in alert_type.lower():
        return (
            f"An SPC control chart violation was detected on {process_name}.  "
            f"This indicates the process may be out of statistical control.  "
            f"Investigate the assignable cause immediately and consider halting production."
        )
    return f"Quality alert on {process_name}: {message}"
