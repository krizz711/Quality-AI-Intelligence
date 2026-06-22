import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import app
from core.config import Settings


def test_health_is_available_without_api_key() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_business_endpoints_require_api_key() -> None:
    response = TestClient(app).get("/reviews")
    assert response.status_code == 403


def test_production_rejects_short_api_key() -> None:
    with pytest.raises(ValidationError, match="API_AUTH_KEY"):
        Settings(
            database_url="postgresql+asyncpg://user:pass@db:5432/arad_quality",
            environment="production",
            api_auth_key="short-secret",
            gemini_api_key="",
            slack_webhook_url="",
        )


def test_production_rejects_mock_data() -> None:
    with pytest.raises(ValidationError, match="ALLOW_MOCK_DATA"):
        Settings(
            database_url="postgresql+asyncpg://user:pass@db:5432/arad_quality",
            environment="production",
            api_auth_key="x" * 40,
            allow_mock_data=True,
        )
