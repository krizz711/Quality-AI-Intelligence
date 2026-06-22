#!/usr/bin/env python3
"""One-time helper: merge arad-quality-agent/.env into root .env (docker-safe defaults).

Run from repo root:
    python scripts/bootstrap_env.py
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "arad-quality-agent" / ".env"
TARGET = ROOT / ".env"


def parse_env(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def main() -> None:
    if not LEGACY.is_file():
        raise SystemExit(f"Legacy env not found: {LEGACY}")

    src = parse_env(LEGACY.read_text(encoding="utf-8"))
    password = src.get("POSTGRES_PASSWORD", "arad_pass")
    encoded_pw = urllib.parse.quote(password, safe="")

    lines = [
        "# Arad Quality Agent — single source of truth (repo root only)",
        "# Copy from .env.example for fresh installs; never commit this file.",
        "",
        f"ENVIRONMENT={src.get('ENVIRONMENT', 'development')}",
        f"LOG_LEVEL={src.get('LOG_LEVEL', 'INFO')}",
        f"API_AUTH_KEY={src.get('API_AUTH_KEY', '')}",
        f"CORS_ORIGINS={src.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')}",
        f"ALLOW_MOCK_DATA={src.get('ALLOW_MOCK_DATA', 'false')}",
        "",
        "# Database (host port 5433 — see docker-compose.yml)",
        f"POSTGRES_DB={src.get('POSTGRES_DB', 'arad_quality')}",
        f"POSTGRES_USER={src.get('POSTGRES_USER', 'arad')}",
        f"POSTGRES_PASSWORD={password}",
        f"DATABASE_URL=postgresql+asyncpg://arad:{encoded_pw}@localhost:5433/arad_quality",
        "",
        "# Kafka / MLflow (host access when API runs outside Docker)",
        f"KAFKA_BOOTSTRAP_SERVERS={src.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')}",
        f"MLFLOW_TRACKING_URI={src.get('MLFLOW_TRACKING_URI', 'http://localhost:5000')}",
        "",
        "# Redis: unset for docker-compose (uses redis://redis:6379). For local API only:",
        "# REDIS_URL=redis://localhost:6379/0",
        "",
        "# Dashboard: unset for Docker (compose uses http://api:8000). For npm run dev:",
        "# API_URL=http://localhost:8000",
        f"NEXT_PUBLIC_ALLOW_MOCK_DATA={src.get('NEXT_PUBLIC_ALLOW_MOCK_DATA', 'false')}",
        f"DASHBOARD_URL={src.get('DASHBOARD_URL', 'http://localhost:3000')}",
        "",
        "# Notifications",
        f"SLACK_WEBHOOK_URL={src.get('SLACK_WEBHOOK_URL', '')}",
        f"JIRA_URL={src.get('JIRA_URL', '')}",
        f"JIRA_EMAIL={src.get('JIRA_EMAIL', '')}",
        f"JIRA_API_TOKEN={src.get('JIRA_API_TOKEN', '')}",
        f"JIRA_PROJECT_KEY={src.get('JIRA_PROJECT_KEY', 'QUAL')}",
        "",
        "# Email (SMTP)",
        f"SMTP_HOST={src.get('SMTP_HOST', '')}",
        f"SMTP_PORT={src.get('SMTP_PORT', '587')}",
        f"SMTP_USER={src.get('SMTP_USER', '')}",
        f"SMTP_PASSWORD={src.get('SMTP_PASSWORD', '')}",
        f"SMTP_FROM_ADDRESS={src.get('SMTP_FROM_ADDRESS', '')}",
        f"ALERT_EMAIL_RECIPIENTS={src.get('ALERT_EMAIL_RECIPIENTS', '')}",
        "",
        "# SMS",
        f"SMS_WEBHOOK_URL={src.get('SMS_WEBHOOK_URL', '')}",
        f"SMS_AUTH_TOKEN={src.get('SMS_AUTH_TOKEN', '')}",
        f"SMS_FROM_NUMBER={src.get('SMS_FROM_NUMBER', '')}",
        f"SMS_TO_NUMBERS={src.get('SMS_TO_NUMBERS', '')}",
        f"TWILIO_ACCOUNT_SID={src.get('TWILIO_ACCOUNT_SID', '')}",
        f"TWILIO_AUTH_TOKEN={src.get('TWILIO_AUTH_TOKEN', '')}",
        "",
        "# Integrations",
        f"QMS_API_URL={src.get('QMS_API_URL', '')}",
        f"ML_TOOL_NAME={src.get('ML_TOOL_NAME', 'mlflow')}",
        "",
        "# AI",
        f"GEMINI_API_KEY={src.get('GEMINI_API_KEY', '')}",
        f"GEMINI_MODEL={src.get('GEMINI_MODEL', 'gemini-2.0-flash')}",
        "",
        "# Admin UIs",
        f"PGADMIN_DEFAULT_EMAIL={src.get('PGADMIN_DEFAULT_EMAIL', 'admin@arad.com')}",
        f"PGADMIN_DEFAULT_PASSWORD={src.get('PGADMIN_DEFAULT_PASSWORD', 'admin')}",
        f"GRAFANA_ADMIN_USER={src.get('GRAFANA_ADMIN_USER', 'admin')}",
        f"GRAFANA_ADMIN_PASSWORD={src.get('GRAFANA_ADMIN_PASSWORD', 'admin')}",
        "",
    ]

    TARGET.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {TARGET} ({len(lines)} lines) from {LEGACY}")


if __name__ == "__main__":
    main()
