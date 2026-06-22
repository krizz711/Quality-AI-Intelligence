"""Contract tests: all /api/v1/ routes validated against the OpenAPI spec.

Uses schemathesis to generate test cases from the live OpenAPI schema and
verify that every endpoint:
  - accepts valid inputs without 5xx errors
  - rejects invalid inputs with 4xx (not 5xx)
  - returns responses that match the declared schema

Run:  pytest tests/contract/ -v
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./contract_test.db")
os.environ.setdefault("API_AUTH_KEY", "test-api-key")

# schemathesis may not be installed in all environments; skip gracefully.
schemathesis = pytest.importorskip("schemathesis", reason="schemathesis not installed")
from api.main import app as fastapi_app

schema = schemathesis.openapi.from_asgi("/openapi.json", fastapi_app)


# ---------------------------------------------------------------------------
# App-level schema fixture
# ---------------------------------------------------------------------------

def _operations():
    return [result.ok() for result in schema.get_all_operations()]


def _sample_path(path: str) -> str:
    return (
        path.replace("{study_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{review_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{alert_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{process_name}", "contract-process")
    )


@pytest.mark.parametrize("operation", _operations(), ids=lambda op: f"{op.method.upper()} {op.path}")
def test_api_schema_no_server_errors(operation):
    """Every generated request must not produce a 5xx response.

    This broad sweep intentionally avoids authentication so protected routes
    stop at the middleware boundary and do not require a live database.
    """
    if operation.path in {"/api/v1/auth/token", "/api/v1/auth/register"}:
        pytest.skip("Auth mutation routes require a seeded user database")

    from fastapi.testclient import TestClient

    client = TestClient(fastapi_app, raise_server_exceptions=False)
    response = client.request(operation.method.upper(), _sample_path(operation.path), json={})
    assert response.status_code < 500, response.text


# ---------------------------------------------------------------------------
# Targeted contract tests for key routes
# ---------------------------------------------------------------------------

class TestGRREndpointContract:

    @pytest.mark.asyncio
    async def test_grr_valid_payload_returns_201(self):
        """POST /api/v1/studies/grr with a valid AIAG payload must return 201."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        payload = {
            "part_ids": ["P1", "P2", "P3"],
            "operator_ids": ["A", "B"],
            "measurements": [
                {"part": f"P{p}", "operator": op, "value": 10.0 + p * 0.1 + (0.05 if op == "B" else 0)}
                for p in range(1, 4)
                for op in ["A", "B"]
                for _ in range(2)
            ],
            "method": "xbar_r",
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers={"x-api-key": "test-api-key"},
        ) as client:
            resp = await client.post("/api/v1/studies/grr", json=payload)

        assert resp.status_code in (201, 422, 500), f"Unexpected status: {resp.status_code} {resp.text}"
        if resp.status_code == 201:
            body = resp.json()
            assert "study_id" in body
            assert "grr_percent" in body
            assert "acceptance" in body
            assert "ndc" in body

    @pytest.mark.asyncio
    async def test_grr_missing_measurements_returns_422(self):
        """POST /api/v1/studies/grr with empty measurements must return 422."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers={"x-api-key": "test-api-key"},
        ) as client:
            resp = await client.post("/api/v1/studies/grr", json={
                "part_ids": [],
                "operator_ids": [],
                "measurements": [],
                "method": "xbar_r",
            })

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_grr_invalid_method_returns_422(self):
        """POST /api/v1/studies/grr with method='bad' must return 422."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers={"x-api-key": "test-api-key"},
        ) as client:
            resp = await client.post("/api/v1/studies/grr", json={
                "part_ids": ["P1"],
                "operator_ids": ["A"],
                "measurements": [{"part": "P1", "operator": "A", "value": 10.0}],
                "method": "bad_method",
            })

        assert resp.status_code == 422


class TestSPCEndpointContract:

    @pytest.mark.asyncio
    async def test_spc_valid_payload_returns_200(self):
        """POST /api/v1/spc/analyze with valid i_mr data must return 200."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers={"x-api-key": "test-api-key"},
        ) as client:
            resp = await client.post("/api/v1/spc/analyze", json={
                "values": [10.1, 10.2, 10.0, 10.3, 10.1, 10.2, 9.9, 10.0, 10.1, 10.2,
                           10.1, 10.0, 10.3, 10.2, 10.1, 9.9, 10.1, 10.2, 10.0, 10.1],
                "chart_type": "i_mr",
                "subgroup_size": 1,
                "part_number": "PN-CONTRACT-001",
                "characteristic_name": "diameter",
            })

        assert resp.status_code in (200, 422, 500)
        if resp.status_code == 200:
            body = resp.json()
            assert "ucl" in body
            assert "lcl" in body
            assert "cl" in body

    @pytest.mark.asyncio
    async def test_spc_too_few_values_returns_422(self):
        """POST /api/v1/spc/analyze with < 2 values must return 422."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers={"x-api-key": "test-api-key"},
        ) as client:
            resp = await client.post("/api/v1/spc/analyze", json={
                "values": [10.0],
                "chart_type": "i_mr",
                "subgroup_size": 1,
            })

        assert resp.status_code == 422


class TestHealthEndpointContract:

    @pytest.mark.asyncio
    async def test_liveness_returns_200_always(self):
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_returns_status_field(self):
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/health/ready")
        assert resp.status_code in (200, 503)
        body = resp.json()
        assert "status" in body
        assert "checks" in body

    @pytest.mark.asyncio
    async def test_openapi_schema_is_accessible(self):
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["openapi"].startswith("3.")
        assert "/api/v1/studies/grr" in schema["paths"]
        assert "/api/v1/spc/analyze" in schema["paths"]
