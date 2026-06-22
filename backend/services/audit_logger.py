import json
import hashlib
import logging
from typing import Any

from db.database import AsyncSessionLocal
from db.models import AuditEvent

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {"password", "ssn", "credit_card", "token", "auth", "secret", "credentials", "passwd"}


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: (_redact(v) if k not in SENSITIVE_KEYS else "[REDACTED]") for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


async def log_event(
    *,
    actor: str | None = "system",
    user_id: str | None = None,
    event_type: str,
    component: str | None = None,
    metadata: dict | None = None,
    algorithm_version: str | None = None,
    result_summary: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Append an audit event to the `audit_events` table.

    Hashes the input payload and redacts obvious sensitive keys. Uses the shared
    application session factory (``AsyncSessionLocal``) so audit writes go through
    the same configured engine and can be patched in tests.

    This function never raises: audit logging is best-effort and must not be able
    to crash the request or background task that triggered it.
    """
    redacted = _redact(metadata or {})
    payload_bytes = json.dumps(redacted, sort_keys=True, default=str).encode("utf-8")
    input_hash = hashlib.sha256(payload_bytes).hexdigest()

    try:
        async with AsyncSessionLocal() as session:
            session.add(
                AuditEvent(
                    actor=actor,
                    user_id=user_id,
                    event_type=event_type,
                    component=component,
                    input_hash=input_hash,
                    algorithm_version=algorithm_version,
                    result_summary=result_summary or (redacted if redacted else None),
                    details=redacted,
                    ip_address=ip_address,
                )
            )
            await session.commit()
    except Exception:
        logger.warning("audit_log_write_failed event_type=%s", event_type, exc_info=True)
