"""Lightweight Slack + JIRA dispatch for the ADK agent.

Reads the SAME environment variables the rest of the app uses
(SLACK_WEBHOOK_URL, JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY) but
without pulling in the full alert_manager/DB stack, so the agent layer runs
standalone. The production `agent.alert_manager` remains the heavyweight path used
by the streaming pipeline.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


def slack_configured() -> bool:
    return bool(os.environ.get("SLACK_WEBHOOK_URL"))


def jira_configured() -> bool:
    return all(os.environ.get(k) for k in ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"))


def send_slack(text: str, *, severity: str = "warning", timeout: int = 10) -> dict[str, Any]:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return {"ok": False, "error": "SLACK_WEBHOOK_URL not configured"}
    color = {"critical": "#ef4444", "warning": "#eab308", "info": "#22c55e"}.get(severity, "#eab308")
    payload = {"text": text, "attachments": [{"color": color, "text": text}]}
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        return {"ok": resp.status_code == 200, "status": resp.status_code}
    except requests.RequestException as exc:
        logger.warning("Slack send failed: %s", exc)
        return {"ok": False, "error": str(exc)}


def _adf(text: str) -> dict[str, Any]:
    return {"type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


def create_jira_issue(summary: str, description: str, *, issue_type: str = "Task",
                      timeout: int = 15) -> dict[str, Any]:
    base = os.environ.get("JIRA_URL")
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")
    project = os.environ.get("JIRA_PROJECT_KEY", "KAN")
    if not (base and email and token):
        return {"ok": False, "error": "JIRA_* not configured"}
    base = base.rstrip("/")
    payload = {"fields": {
        "project": {"key": project}, "summary": summary[:240],
        "description": _adf(description), "issuetype": {"name": issue_type},
    }}
    try:
        resp = requests.post(
            f"{base}/rest/api/3/issue", json=payload, auth=(email, token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=timeout,
        )
        if resp.status_code in (200, 201):
            key = resp.json().get("key")
            return {"ok": True, "key": key, "url": f"{base}/browse/{key}"}
        return {"ok": False, "status": resp.status_code, "body": resp.text[:300]}
    except requests.RequestException as exc:
        logger.warning("JIRA create failed: %s", exc)
        return {"ok": False, "error": str(exc)}
