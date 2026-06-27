"""Dashboard-facing endpoints for the live 'AI Agent' page.

Registered onto the ADK FastAPI app (see web.py):

* GET  /agent/processes — list scannable processes (live backend, else sample fleet).
* POST /agent/scan      — autonomous scan of one process (monitor → cost → draft alert).
* POST /agent/fleet     — scan ALL processes, ranked by risk/cost.
* POST /agent/analyze   — LLM root-cause + corrective action for a violation.
* POST /agent/chat      — message the ADK multi-agent system (LLM).
* POST /agent/dispatch  — actually send the drafted alert (human-in-the-loop).
"""

from __future__ import annotations

import json
from typing import Any

from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from adk_agent import backend_client, skills

PROCESS = "CNC-07 / bore_diameter"

# Shared COPQ assumptions (kept in one place so scan + fleet agree).
_COPQ = dict(
    units_per_hour=120, hours_out_of_control=0.5, baseline_defect_rate=0.01,
    out_of_control_defect_rate=0.15, scrap_cost_per_unit=45,
    escape_rate=0.10, escape_cost_per_unit=500, events_per_year=12,
)

# A representative multi-process "plant" for when no live backend is connected.
SAMPLE_FLEET = [
    ("CNC-07 / bore_diameter", "shift", 11),
    ("CNC-03 / shaft_OD", "in_control", 5),
    ("PRESS-02 / pin_height", "trend", 9),
    ("MILL-05 / slot_width", "drift_to_breach", 2),
    ("LATHE-09 / face_runout", "in_control", 7),
]


class ChatReq(BaseModel):
    message: str


class DispatchReq(BaseModel):
    title: str
    message: str
    severity: str = "critical"
    process_name: str | None = None


class AnalyzeReq(BaseModel):
    process: str
    summary: str
    total_copq: float = 0.0
    savings: float = 0.0


def _sample(scenario: str = "shift", seed: int = 11) -> list[float]:
    return skills.generate_sample_series(n=40, scenario=scenario, seed=seed)["values"]


def _resolve_series(process_name: str | None, scenario: str) -> tuple[str, list[float], str]:
    """Return (process, series, data_source). Live backend if possible, else sample."""
    if process_name:
        try:
            vals = backend_client.get_series(process_name)
            if len(vals) >= 10:
                return process_name, vals, "live backend"
        except Exception:
            pass
        return process_name, _sample(scenario), "sample"
    live = backend_client.get_live_series()
    if live:
        return live[0], live[1], "live backend"
    return PROCESS, _sample(scenario), "sample"


def run_scan(process_name: str | None = None, scenario: str = "shift") -> dict[str, Any]:
    """Autonomous scan of one process: monitor → cost → draft alert (nothing sent)."""
    process, series, data_source = _resolve_series(process_name, scenario)
    # Judge against the process's frozen baseline (the same limits the SPC monitor uses) so a
    # drifting tail doesn't inflate its own limits and mislabel the in-control points.
    baseline = backend_client.get_baseline(process)
    if baseline:
        spc = skills.analyze_spc_series(
            series, baseline_cl=baseline.get("cl"), baseline_sigma=baseline.get("sigma"),
            baseline_ucl=baseline.get("ucl"), baseline_lcl=baseline.get("lcl"))
    else:
        spc = skills.analyze_spc_series(series)
    scan_detail = f"{spc['n_points']} samples on {process} · source: {data_source}"

    if spc["in_control"]:
        return {
            "process": process, "in_control": True, "data_source": data_source, "series": series,
            "control_limits": spc["control_limits"], "violations": [], "violation_count": 0,
            "summary": spc["summary"], "steps": [
                {"agent": "process_monitor", "title": "Pulled measurements", "detail": scan_detail, "status": "done"},
                {"agent": "process_monitor", "title": "In control",
                 "detail": "No special-cause variation detected.", "status": "ok"},
            ], "alert": None,
        }

    copq = skills.calculate_copq(**_COPQ)
    alert = {
        "title": f"[Quality AI] SPC violation on {process}",
        "message": (f"{spc['summary']} Estimated impact ${copq['total_copq']:,.0f} this event; "
                    f"early autonomous detection saves ${copq['savings_from_early_detection']:,.0f} "
                    f"vs once-per-shift inspection. Recommend stopping the line and checking tool wear."),
        "severity": "critical",
        "process_name": process,
    }
    steps = [
        {"agent": "process_monitor", "title": "Pulled measurements", "detail": scan_detail, "status": "done"},
        {"agent": "process_monitor", "title": "Out of control", "detail": spc["summary"], "status": "alert"},
        {"agent": "business_analyst", "title": "Cost of Poor Quality",
         "detail": (f"${copq['total_copq']:,.0f} lost this event · "
                    f"${copq['savings_from_early_detection']:,.0f} saved by early detection · "
                    f"${copq['annualized_copq']:,.0f}/yr exposure"), "status": "done"},
        {"agent": "action_dispatch", "title": "Drafted alert — awaiting approval",
         "detail": "Slack + JIRA corrective-action ticket (human-in-the-loop)", "status": "pending"},
    ]
    return {
        "process": process, "in_control": False, "data_source": data_source, "series": series,
        "control_limits": spc["control_limits"], "violations": spc["violations"],
        "violation_count": spc["violation_count"], "summary": spc["summary"],
        "copq": copq, "steps": steps, "alert": alert,
    }


def _copq_for(spc: dict[str, Any]) -> float:
    """Per-process Cost of Poor Quality. The out-of-control *duration* scales with how many
    points actually breached 3σ (rule_1), so a hard drift costs more than a mild wobble —
    giving real cost variance across the fleet instead of one flat number for everyone."""
    if spc["in_control"]:
        return 0.0
    breaches = sum(1 for v in spc["violations"] if v["rule"] == "rule_1")
    params = dict(_COPQ)
    # ~0.05h of out-of-control production per breached point, capped so it stays realistic.
    # A ~10-point drift → 0.5h → matches the single-process scan's COPQ for the same line.
    params["hours_out_of_control"] = round(min(max(breaches, 1) * 0.05, 4.0), 3)
    return round(skills.calculate_copq(**params)["total_copq"], 2)


def _fleet_row(process: str, series: list[float]) -> dict[str, Any]:
    # Judge each process against its own frozen baseline (same limits as the SPC monitor),
    # so the fleet violation counts are realistic — not inflated by a drifting tail.
    baseline = backend_client.get_baseline(process)
    if baseline:
        spc = skills.analyze_spc_series(
            series, baseline_cl=baseline.get("cl"), baseline_sigma=baseline.get("sigma"),
            baseline_ucl=baseline.get("ucl"), baseline_lcl=baseline.get("lcl"))
    else:
        spc = skills.analyze_spc_series(series)
    return {"process": process, "in_control": spc["in_control"],
            "violation_count": spc["violation_count"], "copq_total": _copq_for(spc)}


def run_fleet() -> dict[str, Any]:
    """Scan every available process and rank by risk/cost (plant-wide view)."""
    rows: list[dict[str, Any]] = []
    source = "sample"
    try:
        procs = backend_client.list_processes()
    except Exception:
        procs = []
    if procs:
        source = "live backend"
        for p in procs[:8]:
            try:
                vals = backend_client.get_series(p["name"])
                if len(vals) >= 10:
                    rows.append(_fleet_row(p["name"], vals))
            except Exception:
                continue
    if not rows:
        source = "sample"
        for name, scenario, seed in SAMPLE_FLEET:
            rows.append(_fleet_row(name, _sample(scenario, seed)))

    rows.sort(key=lambda r: (r["in_control"], -r["violation_count"], -r["copq_total"]))
    return {
        "source": source, "processes": rows,
        "at_risk": sum(1 for r in rows if not r["in_control"]),
        "total_exposure": round(sum(r["copq_total"] for r in rows), 2),
    }


def register(app) -> None:
    """Attach the /agent/* routes to the given FastAPI app."""

    @app.get("/agent/processes")
    async def agent_processes() -> dict[str, Any]:
        try:
            procs = backend_client.list_processes()
            if procs:
                return {"processes": procs, "source": "live backend"}
        except Exception:
            pass
        return {"processes": [{"name": n, "points": 40} for n, _, _ in SAMPLE_FLEET], "source": "sample"}

    @app.post("/agent/scan")
    async def agent_scan(process: str | None = None, scenario: str = "shift") -> dict[str, Any]:
        return run_scan(process_name=process, scenario=scenario)

    @app.post("/agent/fleet")
    async def agent_fleet() -> dict[str, Any]:
        return run_fleet()

    @app.post("/agent/analyze")
    async def agent_analyze(req: AnalyzeReq) -> dict[str, Any]:
        from adk_agent import reasoning
        return {"analysis": reasoning.root_cause_analysis(
            req.process, req.summary, req.total_copq, req.savings)}

    @app.post("/agent/chat")
    async def agent_chat(req: ChatReq) -> dict[str, Any]:
        from adk_agent.run import run_query
        try:
            return {"response": await run_query(req.message, verbose=False)}
        except Exception as exc:
            return {"response": f"(agent error: {exc})", "error": True}

    @app.post("/agent/chat/stream")
    async def agent_chat_stream(req: ChatReq) -> StreamingResponse:
        """Stream the agent's answer as Server-Sent Events: ``{"t":"delta","text"}``
        fragments for live typing, then one ``{"t":"final","answer"}`` with the full
        reply. Powers the AI Agent page's chat (the upgraded Chat page)."""
        from adk_agent.run import stream_query

        async def event_stream():
            def sse(obj: dict[str, Any]) -> str:
                return f"data: {json.dumps(obj)}\n\n"

            try:
                async for kind, text in stream_query(req.message):
                    if kind == "delta":
                        yield sse({"t": "delta", "text": text})
                    else:
                        yield sse({"t": "final", "answer": text})
            except Exception as exc:  # never break the stream — deliver the error as the answer
                yield sse({"t": "final", "answer": f"(agent error: {exc})", "error": True})

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    @app.post("/agent/dispatch")
    async def agent_dispatch(req: DispatchReq) -> dict[str, Any]:
        return skills.dispatch_quality_alert(
            title=req.title, message=req.message, severity=req.severity,
            process_name=req.process_name, confirm=True)

    @app.get("/agent/health")
    async def agent_health() -> dict[str, Any]:
        return {"ok": True, "agents": ["measurement_analyst", "process_monitor",
                                       "business_analyst", "action_dispatch"]}
