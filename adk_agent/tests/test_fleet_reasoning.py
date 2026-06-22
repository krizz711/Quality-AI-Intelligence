"""Tests for fleet scan and the LLM root-cause fallback (no real LLM/backend)."""

from adk_agent import dashboard_api, reasoning


def test_run_fleet_sample_ranks_in_control_last(monkeypatch):
    def boom():
        raise RuntimeError("backend down")
    monkeypatch.setattr(dashboard_api.backend_client, "list_processes", boom)

    out = dashboard_api.run_fleet()
    assert out["source"] == "sample"
    assert len(out["processes"]) == len(dashboard_api.SAMPLE_FLEET)
    assert out["at_risk"] >= 1
    # In-control processes must rank last (the picker shows worst-first).
    statuses = [r["in_control"] for r in out["processes"]]
    assert statuses == sorted(statuses)  # False (at-risk) before True (healthy)
    # Exposure is the sum of the at-risk COPQ.
    assert out["total_exposure"] == round(
        sum(r["copq_total"] for r in out["processes"]), 2
    )


def test_run_fleet_uses_live_when_available(monkeypatch):
    monkeypatch.setattr(dashboard_api.backend_client, "list_processes",
                        lambda: [{"name": "live_proc", "points": 50}])
    monkeypatch.setattr(dashboard_api.backend_client, "get_series",
                        lambda name: [float(v) for v in range(1, 41)])
    out = dashboard_api.run_fleet()
    assert out["source"] == "live backend"
    assert out["processes"][0]["process"] == "live_proc"


def test_root_cause_falls_back_without_llm(monkeypatch):
    from google import genai

    def boom(*a, **k):
        raise RuntimeError("no api key")
    monkeypatch.setattr(genai, "Client", boom)

    out = reasoning.root_cause_analysis("CNC-07", "34 violations, upward shift", 798, 11970)
    assert isinstance(out, str) and len(out) > 30
    assert "unavailable" in out.lower()  # the graceful fallback message
