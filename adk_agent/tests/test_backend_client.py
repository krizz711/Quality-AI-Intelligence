"""Tests for the live-backend integration (mocked HTTP — no backend needed).

Verifies the agent reads real series when the backend is up, and that the scan
falls back to sample data when it's down — without ever hitting a real backend.
"""

from adk_agent import backend_client, dashboard_api


class _Resp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise backend_client.requests.HTTPError(f"status {self.status_code}")


def test_get_live_series_none_when_backend_down(monkeypatch):
    def boom(*a, **k):
        raise backend_client.requests.RequestException("connection refused")
    monkeypatch.setattr(backend_client.requests, "get", boom)
    assert backend_client.get_live_series() is None


def test_get_live_series_picks_process(monkeypatch):
    def fake_get(url, headers=None, timeout=None, **k):
        if url.endswith("/spc/processes"):
            return _Resp(payload={"processes": [
                {"name": "bore_diameter", "points": 60, "latest": "2026-06-21T00:00:00"},
            ]})
        if "/spc/history/" in url:
            # newest-first; client reverses to chronological
            return _Resp(payload={"points": [{"value": float(v)} for v in range(60, 0, -1)]})
        return _Resp(status_code=404)

    monkeypatch.setattr(backend_client.requests, "get", fake_get)
    result = backend_client.get_live_series(min_points=20)
    assert result is not None
    name, values = result
    assert name == "bore_diameter"
    assert len(values) == 60 and values[0] == 1.0 and values[-1] == 60.0  # chronological


def test_scan_uses_live_data_when_available(monkeypatch):
    monkeypatch.setattr(dashboard_api.backend_client, "get_live_series",
                        lambda: ("milling_depth", [float(v) for v in range(1, 41)]))
    out = dashboard_api.run_scan()
    assert out["data_source"] == "live backend"
    assert out["process"] == "milling_depth"


def test_scan_falls_back_to_sample(monkeypatch):
    monkeypatch.setattr(dashboard_api.backend_client, "get_live_series", lambda: None)
    out = dashboard_api.run_scan()
    assert out["data_source"] == "sample"
    assert out["violation_count"] > 0  # the sample 'shift' scenario is out of control


def test_dispatch_prefers_platform_pipeline(monkeypatch):
    from adk_agent import skills
    monkeypatch.setattr(skills.backend_client, "trigger_platform_alert",
                        lambda **k: {"ok": True, "alert_id": "ALRT-1"})
    out = skills.dispatch_quality_alert("SPC violation", "msg", process_name="CNC-07", confirm=True)
    assert out["status"] == "dispatched"
    assert out["via"] == "platform (Connections page)" and out["alert_id"] == "ALRT-1"


def test_dispatch_falls_back_to_direct_when_platform_down(monkeypatch):
    from adk_agent import skills
    monkeypatch.setattr(skills.backend_client, "trigger_platform_alert", lambda **k: {"ok": False})
    monkeypatch.setattr(skills.dispatch, "send_slack", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(skills.dispatch, "create_jira_issue", lambda *a, **k: {"ok": True, "key": "KAN-1"})
    out = skills.dispatch_quality_alert("SPC violation", "msg", process_name="CNC-07", confirm=True)
    assert out["via"] == "direct (.env fallback)"
    assert set(out["sent_to"]) == {"slack", "jira"}
