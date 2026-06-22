import os

# Provide minimal required settings so importing core.settings succeeds during test collection.
os.environ.setdefault("API_AUTH_KEY", "test-api-key")

from fastapi.testclient import TestClient

import api.auth as auth_mod
from api.main import app


async def _fake_auth(username: str, password: str):
    return {"username": "alice"}


def test_issue_token_monkeypatched(monkeypatch):
    monkeypatch.setattr(auth_mod, "authenticate_user", _fake_auth)

    client = TestClient(app)
    resp = client.post("/api/v1/auth/token", json={"username": "alice", "password": "secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
