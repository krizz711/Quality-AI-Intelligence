"""Runtime configuration store — integration credentials + LLM key.

Values are persisted in the ``system_settings`` table and *applied* onto the live
``settings`` singleton and ``os.environ`` at startup and after every save, so all
existing code that reads ``settings.*`` / ``os.environ`` (AlertManager, the Gemini
service, etc.) picks them up with no refactor. Secret values are encrypted at rest
with Fernet (key derived from JWT_SECRET).

This is single-tenant: one config set per deployment.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass

from sqlalchemy import select

from core.config import settings
from db.database import AsyncSessionLocal
from db.models import SystemSetting

logger = logging.getLogger(__name__)

SECRET_SENTINEL = "********"  # what the UI shows / sends back for unchanged secrets
_TEST_PREFIX = "_test."  # rows that cache the last live-test result per channel


@dataclass(frozen=True)
class SettingSpec:
    key: str        # storage/UI key, e.g. "slack.webhook_url"
    attr: str       # settings attribute, e.g. "slack_webhook_url"
    env: str        # env var name, e.g. "SLACK_WEBHOOK_URL"
    secret: bool = False
    is_int: bool = False


SPEC: list[SettingSpec] = [
    SettingSpec("slack.webhook_url", "slack_webhook_url", "SLACK_WEBHOOK_URL", secret=True),
    SettingSpec("email.smtp_host", "smtp_host", "SMTP_HOST"),
    SettingSpec("email.smtp_port", "smtp_port", "SMTP_PORT", is_int=True),
    SettingSpec("email.smtp_user", "smtp_user", "SMTP_USER"),
    SettingSpec("email.smtp_password", "smtp_password", "SMTP_PASSWORD", secret=True),
    SettingSpec("email.from_address", "smtp_from_address", "SMTP_FROM_ADDRESS"),
    SettingSpec("email.recipients", "alert_email_recipients", "ALERT_EMAIL_RECIPIENTS"),
    SettingSpec("sms.webhook_url", "sms_webhook_url", "SMS_WEBHOOK_URL"),
    SettingSpec("sms.auth_token", "sms_auth_token", "SMS_AUTH_TOKEN", secret=True),
    SettingSpec("sms.from_number", "sms_from_number", "SMS_FROM_NUMBER"),
    SettingSpec("sms.to_numbers", "sms_to_numbers", "SMS_TO_NUMBERS"),
    SettingSpec("jira.url", "jira_url", "JIRA_URL"),
    SettingSpec("jira.email", "jira_email", "JIRA_EMAIL"),
    SettingSpec("jira.api_token", "jira_api_token", "JIRA_API_TOKEN", secret=True),
    SettingSpec("jira.project_key", "jira_project_key", "JIRA_PROJECT_KEY"),
    SettingSpec("qms.api_url", "qms_api_url", "QMS_API_URL"),
    SettingSpec("llm.provider", "llm_provider", "LLM_PROVIDER"),
    SettingSpec("llm.gemini_api_key", "gemini_api_key", "GEMINI_API_KEY", secret=True),
    SettingSpec("llm.anthropic_api_key", "anthropic_api_key", "ANTHROPIC_API_KEY", secret=True),
    SettingSpec("llm.openai_api_key", "openai_api_key", "OPENAI_API_KEY", secret=True),
    # MES/QMS auto-connector — pulls measurements from the org's API on a timer.
    SettingSpec("mes.api_url", "mes_api_url", "MES_API_URL"),
    SettingSpec("mes.api_token", "mes_api_token", "MES_API_TOKEN", secret=True),
    SettingSpec("mes.auth_header", "mes_auth_header", "MES_AUTH_HEADER"),
    SettingSpec("mes.auth_value", "mes_auth_value", "MES_AUTH_VALUE", secret=True),
    SettingSpec("mes.records_path", "mes_records_path", "MES_RECORDS_PATH"),
    SettingSpec("mes.field_map", "mes_field_map", "MES_FIELD_MAP"),
    SettingSpec("mes.id_field", "mes_id_field", "MES_ID_FIELD"),
    SettingSpec("mes.since_param", "mes_since_param", "MES_SINCE_PARAM"),
    SettingSpec("mes.poll_interval_seconds", "mes_poll_interval_seconds", "MES_POLL_INTERVAL_SECONDS", is_int=True),
]

_BY_KEY = {s.key: s for s in SPEC}


# ── Encryption ────────────────────────────────────────────────────────────────
def _fernet():
    from cryptography.fernet import Fernet

    secret = getattr(settings, "jwt_secret", "") or getattr(settings, "api_auth_key", "") or "dev-insecure-key"
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _encrypt(plaintext: str) -> str:
    try:
        return "enc:" + _fernet().encrypt(plaintext.encode()).decode()
    except Exception:
        logger.warning("Encryption unavailable; storing secret unencrypted")
        return "plain:" + plaintext


def _decrypt(stored: str) -> str:
    if stored.startswith("enc:"):
        try:
            return _fernet().decrypt(stored[4:].encode()).decode()
        except Exception:
            logger.exception("Failed to decrypt a stored secret")
            return ""
    if stored.startswith("plain:"):
        return stored[len("plain:"):]
    return stored


# ── Persistence ───────────────────────────────────────────────────────────────
async def _load_rows() -> dict[str, SystemSetting]:
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(SystemSetting))).scalars().all()
    return {r.key: r for r in rows}


async def get_decrypted() -> dict[str, str]:
    """All stored settings with secrets decrypted (for runtime use / tests)."""
    rows = await _load_rows()
    out: dict[str, str] = {}
    for key, row in rows.items():
        if row.value is None:
            continue
        spec = _BY_KEY.get(key)
        out[key] = _decrypt(row.value) if (spec and spec.secret) else row.value
    return out


async def get_masked() -> list[dict]:
    """Settings for the admin UI — secret values never leave the server."""
    rows = await _load_rows()
    result: list[dict] = []
    for spec in SPEC:
        row = rows.get(spec.key)
        configured = bool(row and row.value)
        entry: dict = {"key": spec.key, "secret": spec.secret, "configured": configured}
        if not spec.secret:
            entry["value"] = (row.value if row else "") or ""
        result.append(entry)
    return result


# The "llm" channel hosts interchangeable providers; each keeps its own cached
# test result under `_test.llm:<provider>`, keyed off the editable secret field.
_LLM_KEY_PROVIDER = {
    "llm.gemini_api_key": "gemini",
    "llm.anthropic_api_key": "claude",
    "llm.openai_api_key": "openai",
}


async def set_many(updates: dict[str, str | None], updated_by: str | None = None) -> None:
    touched_channels: set[str] = set()
    changed_keys: set[str] = set()
    async with AsyncSessionLocal() as session:
        existing = {r.key: r for r in (await session.execute(select(SystemSetting))).scalars().all()}
        for key, raw in updates.items():
            spec = _BY_KEY.get(key)
            if spec is None:
                continue
            # For secrets, an empty value or the masked sentinel means "unchanged".
            if spec.secret and (raw is None or raw == "" or raw == SECRET_SENTINEL):
                continue
            stored = _encrypt(raw) if (spec.secret and raw) else (raw or "")
            row = existing.get(key)
            # Only count a key as *changed* when its stored value actually differs.
            # The UI re-sends every non-secret field on every save, so without this
            # check an unrelated save (or a Send-test on another channel, which saves
            # first) would wipe a channel's "verified" state even though nothing about
            # it moved. Secrets that reach here are always newly typed, so they count.
            if row is None:
                if stored == "":
                    continue  # blank field that never existed — nothing to store
                session.add(
                    SystemSetting(key=key, value=stored, is_secret=spec.secret, updated_by=updated_by)
                )
                touched_channels.add(key.split(".", 1)[0])
                changed_keys.add(key)
                continue
            changed = spec.secret or stored != (row.value or "")
            row.value = stored
            row.is_secret = spec.secret
            row.updated_by = updated_by
            if changed:
                touched_channels.add(key.split(".", 1)[0])
                changed_keys.add(key)
        # Changing a channel's keys invalidates its prior live-test result, so a wrong
        # value can never stay "verified" just because an old test passed. For "llm",
        # the per-provider results live under `_test.llm:<provider>`, so switching the
        # provider (which touches the channel but changes no key) leaves them intact —
        # only editing a provider's key clears that one provider's result.
        for channel in touched_channels:
            trow = existing.get(f"{_TEST_PREFIX}{channel}")
            if trow is not None:
                await session.delete(trow)
        for key in changed_keys:
            provider = _LLM_KEY_PROVIDER.get(key)
            if provider:
                trow = existing.get(f"{_TEST_PREFIX}llm:{provider}")
                if trow is not None:
                    await session.delete(trow)
        await session.commit()
    await apply_to_runtime()


def channels() -> set[str]:
    """All known integration channel ids (e.g. ``{"slack", "email", ...}``)."""
    return {s.key.split(".", 1)[0] for s in SPEC}


async def clear_channel(channel: str) -> None:
    """Remove every stored credential for ``channel`` plus its cached test result,
    and reset the live runtime so the old values stop being used immediately."""
    specs = [s for s in SPEC if s.key.split(".", 1)[0] == channel]
    if not specs:
        return
    keys_to_delete = [s.key for s in specs] + [f"{_TEST_PREFIX}{channel}"]
    if channel == "llm":
        # AI-summary results are stored per provider — remove them all on clear.
        keys_to_delete += [f"{_TEST_PREFIX}llm:{p}" for p in ("gemini", "claude", "openai")]
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(SystemSetting).where(SystemSetting.key.in_(keys_to_delete))
            )
        ).scalars().all()
        for row in rows:
            await session.delete(row)
        await session.commit()
    # Reset the live ``settings`` singleton + env back to defaults so nothing keeps
    # using the cleared credentials (apply_to_runtime only ever sets truthy values).
    fields = type(settings).model_fields
    for spec in specs:
        os.environ.pop(spec.env, None)
        default = fields[spec.attr].default if spec.attr in fields else ""
        try:
            setattr(settings, spec.attr, default)
        except Exception:
            logger.debug("Could not reset setting %s to default", spec.attr)


async def _active_llm_provider() -> str:
    cfg = await get_decrypted()
    return (cfg.get("llm.provider") or settings.llm_provider or "gemini").lower()


async def _test_channel_key(channel: str) -> str:
    """Storage sub-key for a channel's cached test — per provider for ``llm`` so each
    of Gemini/Claude/OpenAI keeps its own result instead of one shared slot."""
    if channel == "llm":
        return f"llm:{await _active_llm_provider()}"
    return channel


async def record_test(channel: str, ok: bool, message: str) -> None:
    """Persist the result of a live integration test so 'verified' survives reloads."""
    payload = json.dumps({"ok": ok, "message": message, "ts": int(time.time())})
    key = f"{_TEST_PREFIX}{await _test_channel_key(channel)}"
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(select(SystemSetting).where(SystemSetting.key == key))
        ).scalar_one_or_none()
        if row is None:
            session.add(SystemSetting(key=key, value=payload, is_secret=False, updated_by="system"))
        else:
            row.value = payload
        await session.commit()


async def get_test_status() -> dict[str, dict]:
    """Last live-test result per channel: {channel: {ok, message, ts}}."""
    rows = await _load_rows()
    out: dict[str, dict] = {}
    for key, row in rows.items():
        if not key.startswith(_TEST_PREFIX) or not row.value:
            continue
        try:
            out[key[len(_TEST_PREFIX):]] = json.loads(row.value)
        except Exception:
            continue
    return out


async def apply_to_runtime() -> None:
    """Push stored settings onto the live ``settings`` singleton + ``os.environ``."""
    try:
        values = await get_decrypted()
    except Exception:
        logger.exception("Could not load settings for runtime apply")
        return
    for spec in SPEC:
        val = values.get(spec.key)
        if not val:
            continue
        try:
            os.environ[spec.env] = val
            setattr(settings, spec.attr, int(val) if spec.is_int else val)
        except Exception:
            logger.debug("Could not apply setting %s to runtime", spec.key)


# ── Connection tests ──────────────────────────────────────────────────────────
async def test_channel(channel: str) -> tuple[bool, str]:
    """Best-effort live test of a configured integration."""
    import httpx

    cfg = await get_decrypted()

    if channel == "slack":
        url = cfg.get("slack.webhook_url") or settings.slack_webhook_url
        if not url:
            return False, "No Slack webhook URL configured."
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    url,
                    json={"text": "✅ Arad Quality — Slack integration test. You're connected."},
                )
            ok = r.status_code < 400
            return (
                ok,
                "Test message delivered to your Slack channel."
                if ok
                else f"Slack rejected the webhook (HTTP {r.status_code}) — re-check the URL.",
            )
        except Exception as exc:
            return False, f"Slack test failed: {exc}"

    if channel == "email":
        host = cfg.get("email.smtp_host") or settings.smtp_host
        if not host:
            return False, "No SMTP host configured."
        try:
            import aiosmtplib

            port = int(cfg.get("email.smtp_port") or settings.smtp_port or 587)
            smtp = aiosmtplib.SMTP(hostname=host, port=port, timeout=10)
            await smtp.connect()
            user = cfg.get("email.smtp_user") or settings.smtp_user
            pwd = cfg.get("email.smtp_password") or settings.smtp_password
            if user and pwd:
                await smtp.login(user, pwd)
            # Actually send a test email so the user gets proof it works — not just a
            # silent connection check.
            from_addr = cfg.get("email.from_address") or settings.smtp_from_address or user
            recipients_raw = cfg.get("email.recipients") or getattr(settings, "alert_email_recipients", "") or ""
            recipients = [r.strip() for r in str(recipients_raw).split(",") if r.strip()]
            if from_addr and recipients:
                message = (
                    f"From: {from_addr}\r\n"
                    f"To: {', '.join(recipients)}\r\n"
                    "Subject: Arad Quality - email integration test\r\n\r\n"
                    "This is a test from Arad Quality Intelligence. "
                    "Your email alerts are configured correctly."
                )
                await smtp.sendmail(from_addr, recipients, message)
                await smtp.quit()
                return True, f"Test email sent to {', '.join(recipients)} - check the inbox."
            await smtp.quit()
            return True, "Mail server login succeeded - add a 'Send to' recipient to receive a test email."
        except Exception as exc:
            return False, f"SMTP test failed: {exc}"

    if channel == "llm":
        provider = (cfg.get("llm.provider") or settings.llm_provider or "gemini").lower()
        if provider == "claude":
            key = cfg.get("llm.anthropic_api_key") or settings.anthropic_api_key
            if not key:
                return False, "No Claude (Anthropic) API key configured."
            os.environ["ANTHROPIC_API_KEY"] = key
            return True, "Claude API key saved — AI summaries will use Claude."
        if provider == "openai":
            key = cfg.get("llm.openai_api_key") or settings.openai_api_key
            if not key:
                return False, "No OpenAI API key configured."
            os.environ["OPENAI_API_KEY"] = key
            return True, "OpenAI API key saved — AI summaries will use OpenAI."
        key = cfg.get("llm.gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            return False, "No Gemini API key configured."
        os.environ["GEMINI_API_KEY"] = key
        return True, "Gemini API key saved — AI summaries will use Gemini."

    if channel == "jira":
        url = cfg.get("jira.url") or settings.jira_url
        email = cfg.get("jira.email") or settings.jira_email
        token = cfg.get("jira.api_token") or settings.jira_api_token
        if not (url and email and token):
            return False, "JIRA URL, email, and API token are all required."
        project = cfg.get("jira.project_key") or settings.jira_project_key
        # Prefer the project endpoint: it works with least-privilege *scoped* tokens
        # (read:project:jira) and also validates the project key. Fall back to /myself
        # for classic unscoped tokens when no project key is configured.
        endpoint = f"/rest/api/2/project/{project}" if project else "/rest/api/2/myself"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{url.rstrip('/')}{endpoint}", auth=(email, token))
            if r.status_code < 400:
                return True, "Connected to JIRA — credentials verified."
            if r.status_code == 401:
                return False, "JIRA rejected the login (HTTP 401) — check the account email and API token."
            if r.status_code == 404 and project:
                return False, f"Connected, but project '{project}' wasn't found (HTTP 404) — check the project key."
            return False, f"JIRA test failed (HTTP {r.status_code})."
        except Exception as exc:
            return False, f"JIRA test failed: {exc}"

    if channel == "qms":
        url = cfg.get("qms.api_url") or settings.qms_api_url
        if not url:
            return False, "No QMS API URL configured."
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url)
            return (r.status_code < 500, f"QMS endpoint reachable (HTTP {r.status_code}).")
        except Exception as exc:
            return False, f"QMS test failed: {exc}"

    if channel == "sms":
        webhook = cfg.get("sms.webhook_url") or settings.sms_webhook_url
        to = cfg.get("sms.to_numbers") or settings.sms_to_numbers
        if not (webhook and to):
            return False, "SMS webhook and at least one recipient number are required."
        return True, "SMS credentials present (live send happens on critical alerts)."

    if channel == "mes":
        url = cfg.get("mes.api_url") or os.environ.get("MES_API_URL", "")
        if not url:
            return False, "No MES/QMS API URL configured."
        headers = {"Accept": "application/json"}
        token = cfg.get("mes.api_token") or os.environ.get("MES_API_TOKEN", "")
        auth_header = cfg.get("mes.auth_header") or os.environ.get("MES_AUTH_HEADER", "")
        auth_value = cfg.get("mes.auth_value") or os.environ.get("MES_AUTH_VALUE", "")
        if auth_header and auth_value:
            headers[auth_header] = auth_value
        elif token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, headers=headers)
            return (r.status_code < 500, f"MES/QMS endpoint reachable (HTTP {r.status_code}).")
        except Exception as exc:
            return False, f"MES/QMS test failed: {exc}"

    return False, f"Unknown channel '{channel}'."
