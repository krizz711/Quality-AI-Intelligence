import os
import subprocess
import time

os.environ.setdefault("API_AUTH_KEY", "test-api-key")
# This test expects the test DB to be prepared (migrations + seed) via Docker compose.

from fastapi.testclient import TestClient
from jose import jwt

from api.main import app


def test_login_with_seeded_user():
    client = TestClient(app)
    resp = client.post("/api/v1/auth/token", json={"username": "admin", "password": "adminpass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    token = data["access_token"]
    payload = jwt.decode(token, "dev-jwt-secret-change-me", algorithms=["HS256"])
    assert payload.get("sub") == "admin"
