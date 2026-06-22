import os
import asyncio

os.environ.setdefault("API_AUTH_KEY", "test-api-key")
# Tests must use TEST_DATABASE_URL (Postgres); do not fallback to SQLite.

from fastapi.testclient import TestClient

import backend.services.gemini_service as geminiService
from db import database as db_database

from api.main import app


class DummySession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, *args, **kwargs):
        class R:
            def mappings(self):
                return []

        return R()

    def add(self, *args, **kwargs):
        return None


async def _fake_analyze(*args, **kwargs):
    return "ok"


def test_rate_limit(monkeypatch):
    # Patch external services to be no-ops so endpoint executes quickly
    monkeypatch.setattr(geminiService, "analyzeGRR", _fake_analyze)
    # No DB monkeypatch: use seeded sqlite file so authentication works

    client = TestClient(app)

    # ensure seed DB exists
    seed_script = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'seed_users_db.py'))
    import subprocess
    subprocess.run(["python", seed_script], check=True)

    # get JWT token for seeded admin user
    auth_resp = client.post('/api/v1/auth/token', json={'username': 'admin', 'password': 'adminpass'})
    assert auth_resp.status_code == 200
    token = auth_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # exercise a lightweight test-only endpoint protected by limiter
    last_status = None
    for i in range(4):
        resp = client.get('/api/v1/__test/limiter')
        last_status = resp.status_code

    # limiter is set to 2/minute; the 3rd or 4th request should be rate-limited
    assert last_status == 429
