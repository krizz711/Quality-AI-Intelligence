"""Read real measurement data from the main platform backend.

Lets the ADK agent analyze the SAME live series the dashboard's SPC Monitor shows,
instead of synthetic data — making it one integrated system. Falls back gracefully
(callers get None) when the backend is down, so the agent still runs standalone.

Uses only ``requests`` (already a dependency), so the lean agent venv is enough —
no need for the backend's SQLAlchemy/Kafka stack.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def _base() -> str:
    return (os.environ.get("API_URL") or "http://127.0.0.1:8000").rstrip("/").replace(
        "http://localhost:", "http://127.0.0.1:"
    )


def _headers() -> dict[str, str]:
    key = os.environ.get("API_AUTH_KEY")
    return {"x-api-key": key} if key else {}


def is_available(timeout: float = 3.0) -> bool:
    try:
        r = requests.get(f"{_base()}/api/v1/spc/processes", headers=_headers(), timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def list_processes(timeout: float = 5.0) -> list[dict]:
    r = requests.get(f"{_base()}/api/v1/spc/processes", headers=_headers(), timeout=timeout)
    r.raise_for_status()
    return r.json().get("processes", [])


def get_series(process_name: str, timeout: float = 8.0) -> list[float]:
    """Return the measurement values for a process, oldest → newest."""
    r = requests.get(
        f"{_base()}/api/v1/spc/history/{process_name}", headers=_headers(), timeout=timeout
    )
    r.raise_for_status()
    points = r.json().get("points", [])
    # The endpoint returns newest-first; reverse to chronological order for SPC.
    return [float(p["value"]) for p in reversed(points) if p.get("value") is not None]


def trigger_platform_alert(
    message: str,
    severity: str,
    process_name: str,
    alert_type: str = "spc_violation",
    timeout: float = 15.0,
) -> dict:
    """Route an alert through the PLATFORM's alert pipeline (POST /alerts/trigger).

    The platform's AlertManager dispatches to whatever channels the operator has
    configured and verified on the **Connections page** (encrypted in the DB) — so
    integrations are set up once, in one place, not duplicated in the agent's env.
    Returns {"ok": True, "alert_id": ...} on success.
    """
    try:
        r = requests.post(
            f"{_base()}/api/v1/alerts/trigger",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"type": alert_type, "severity": severity,
                  "message": message, "process_name": process_name},
            timeout=timeout,
        )
        if r.status_code in (200, 201):
            return {"ok": True, "alert_id": r.json().get("alert_id")}
        return {"ok": False, "status": r.status_code, "body": r.text[:200]}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def get_live_series(min_points: int = 20) -> Optional[tuple[str, list[float]]]:
    """Pick the most recently-updated process with enough data; return (name, values).

    Returns None if the backend is unreachable or no series has enough points.
    """
    try:
        candidates = [p for p in list_processes() if int(p.get("points", 0)) >= min_points]
        for proc in candidates:  # already ordered newest-first by the backend
            values = get_series(proc["name"])
            if len(values) >= min_points:
                logger.info("Using live backend series '%s' (%d points)", proc["name"], len(values))
                return proc["name"], values
    except requests.RequestException as exc:
        logger.info("Backend not available for live data (%s); using sample.", exc)
    return None
