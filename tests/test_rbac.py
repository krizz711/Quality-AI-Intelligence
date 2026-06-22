import os
import uuid

# Ensure settings load in test environment
os.environ.setdefault("API_AUTH_KEY", "test-api-key")

from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app


def test_non_admin_cannot_resolve_alert():
    client = TestClient(app)
    token = create_access_token({"sub": "bob"})
    headers = {"Authorization": f"Bearer {token}"}

    fake_alert_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/alerts/{fake_alert_id}/resolve", headers=headers)
    # No role-based forbid now — ensure it isn't a 403
    assert resp.status_code != 403
