#!/usr/bin/env python3
"""Live customer walkthrough — exercises USER_TESTING_GUIDE scenarios via API."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:3000").rstrip("/")
API_KEY = os.environ.get("API_AUTH_KEY", "test-api-key-e2e-local")

HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}

PASS = 0
FAIL = 0
SKIP = 0


def ok(label: str, detail: str = "") -> None:
    global PASS
    PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  PASS  {label}{suffix}")


def fail(label: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  FAIL  {label}{suffix}")


def skip(label: str, reason: str = "") -> None:
    global SKIP
    SKIP += 1
    print(f"  SKIP  {label}" + (f" — {reason}" if reason else ""))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def build_grr_measurements(
    operators: list[str],
    parts: int,
    trials: int,
    base: float = 12.7,
    spread: float = 0.02,
) -> list[dict]:
    rows = []
    for op in operators:
        for part in range(1, parts + 1):
            for trial in range(1, trials + 1):
                offset = (hash(f"{op}{part}{trial}") % 100) / 10000
                rows.append(
                    {
                        "operator": op,
                        "part": part,
                        "trial": trial,
                        "value": round(base + offset - spread / 2, 4),
                    }
                )
    return rows


def scenario_0_stack(client: httpx.Client) -> None:
    section("Scenario 0 — Stack health")
    r = client.get(f"{API_URL}/api/v1/health")
    if r.status_code == 200:
        body = r.json()
        deps = body.get("dependencies", {})
        ok("GET /api/v1/health", f"status={body.get('status')} db={deps.get('db')} kafka={deps.get('kafka')}")
    else:
        fail("GET /api/v1/health", f"HTTP {r.status_code}")

    r = client.get(f"{DASHBOARD_URL}/", timeout=15)
    if r.status_code == 200:
        ok("Dashboard loads", f"HTTP {r.status_code}")
    else:
        fail("Dashboard loads", f"HTTP {r.status_code}")


def scenario_1_grr(client: httpx.Client) -> str | None:
    section("Scenario 1 — GR&R study")
    # Validation: 1 operator must fail
    bad = client.post(
        f"{API_URL}/api/v1/grr/analyze",
        json={"measurements": build_grr_measurements(["Op1"], 10, 2)},
    )
    if bad.status_code == 422:
        ok("GR&R rejects <2 operators", bad.text[:120])
    else:
        fail("GR&R rejects <2 operators", f"HTTP {bad.status_code}")

    measurements = build_grr_measurements(["OpA", "OpB", "OpC"], 10, 2)
    if len(measurements) != 60:
        fail("Measurement table size", f"expected 60 got {len(measurements)}")
    else:
        ok("Measurement table", "60 rows (3×10×2)")

    r = client.post(
        f"{API_URL}/api/v1/grr/analyze",
        json={"measurements": measurements, "partTolerance": 0.5},
    )
    if r.status_code != 201:
        fail("Run GR&R analysis", f"HTTP {r.status_code}: {r.text[:200]}")
        return None

    body = r.json()
    grr = body.get("grr_percent")
    ndc = body.get("number_of_distinct_categories")
    ok("GR&R analysis", f"grr%={grr:.2f} ndc={ndc}")

    hist = client.get(f"{API_URL}/api/v1/grr/history")
    if hist.status_code == 200 and len(hist.json()) > 0:
        ok("GR&R history has entries")
    else:
        fail("GR&R history", f"HTTP {hist.status_code}")

    audit = client.get(f"{API_URL}/api/v1/audit-log")
    if audit.status_code == 200:
        actions = [e.get("action", "") for e in audit.json()]
        if any("grr" in a.lower() for a in actions):
            ok("Audit trail records GRR")
        else:
            fail("Audit trail GRR entry", f"actions sample: {actions[:5]}")
    else:
        fail("Audit log", f"HTTP {audit.status_code}")

    return None


def scenario_2_spc(client: httpx.Client) -> None:
    section("Scenario 2 — SPC monitoring")
    process = "Torque Press Line 1"
    baseline = [5.0, 5.01, 4.99, 5.02, 5.0, 4.98, 5.01, 5.0, 4.99, 5.02, 5.0, 5.01, 4.99, 5.0, 5.01]

    r = client.post(
        f"{API_URL}/api/v1/spc/data",
        json={"process_name": process, "measurements": baseline, "target": 5.0},
    )
    if r.status_code == 201:
        body = r.json()
        if not body.get("violations"):
            ok("Baseline SPC in control", f"mean={body.get('mean'):.4f}")
        else:
            fail("Baseline should be in control", str(body.get("violations")))
    else:
        fail("Baseline SPC", f"HTTP {r.status_code}: {r.text[:200]}")

    drift = baseline + [5.04, 5.05, 5.06, 5.07, 5.08, 5.09, 5.10, 5.11, 5.12]
    r = client.post(
        f"{API_URL}/api/v1/spc/data",
        json={"process_name": process, "measurements": drift, "target": 5.0},
    )
    if r.status_code == 201:
        body = r.json()
        violations = body.get("violations", [])
        if violations:
            ok("Drift triggers violation", f"{len(violations)} rule(s), first={violations[0].get('rule')}")
        else:
            fail("Drift should trigger Nelson violation")
    else:
        fail("Drift SPC", f"HTTP {r.status_code}")

    summary = client.get(f"{API_URL}/api/v1/dashboard/summary")
    if summary.status_code == 200:
        ok("Dashboard summary", json.dumps(summary.json())[:100])
    else:
        fail("Dashboard summary", f"HTTP {summary.status_code}")


def scenario_3_alerts(client: httpx.Client) -> None:
    section("Scenario 3 — Alert triage")
    import uuid as _uuid

    unique_msg = f"E2E walkthrough test alert {_uuid.uuid4().hex[:8]}"
    created = client.post(
        f"{API_URL}/api/v1/alerts/trigger",
        json={
            "type": "spc_violation",
            "severity": "high",
            "message": unique_msg,
            "process_name": "Torque Press Line 1",
        },
    )
    alert_id = None
    if created.status_code == 201:
        alert_id = created.json().get("alert_id")
        ok("Trigger alert", f"id={alert_id}")
    else:
        fail("Trigger alert", f"HTTP {created.status_code}")

    listing = client.get(f"{API_URL}/api/v1/alerts", params={"status": "active"})
    if listing.status_code == 200:
        items = listing.json().get("items", [])
        ok("List active alerts", f"count={len(items)}")
        if not alert_id and items:
            alert_id = items[0].get("id")
    else:
        fail("List alerts", f"HTTP {listing.status_code}")

    if alert_id:
        fb = client.post(
            f"{API_URL}/api/v1/alerts/{alert_id}/feedback",
            json={"is_relevant": True, "category": "true_positive", "submitted_by": "e2e-tester"},
        )
        if fb.status_code == 201:
            ok("Alert feedback (relevant)")
        else:
            fail("Alert feedback", f"HTTP {fb.status_code}: {fb.text[:120]}")

        res = client.put(f"{API_URL}/api/v1/alerts/{alert_id}/resolve")
        if res.status_code == 200:
            ok("Resolve alert")
        else:
            fail("Resolve alert", f"HTTP {res.status_code}: {res.text[:120]}")

    acc = client.get(f"{API_URL}/api/v1/alerts/accuracy")
    if acc.status_code == 200:
        ok("Alert accuracy metric", f"rate={acc.json().get('accuracy_rate')}")
    else:
        fail("Alert accuracy", f"HTTP {acc.status_code}")


def scenario_4_audit(client: httpx.Client) -> None:
    section("Scenario 4 — Compliance audit")
    r = client.get(f"{API_URL}/api/v1/audit-log")
    if r.status_code != 200:
        fail("Audit log list", f"HTTP {r.status_code}")
        return
    entries = r.json()
    ok("Audit log entries", f"count={len(entries)}")

    filtered = [e for e in entries if "grr" in json.dumps(e).lower()]
    if filtered:
        ok("Search finds grr-related entries", f"hits={len(filtered)}")
    else:
        fail("Search grr in audit log")

    export = client.get(f"{API_URL}/api/v1/audit-log/export", params={"format": "csv"})
    if export.status_code == 200 and "text/csv" in export.headers.get("content-type", ""):
        ok("Export audit CSV", f"{len(export.text)} bytes")
    else:
        fail("Export audit CSV", f"HTTP {export.status_code}")


def scenario_5_copilot(client: httpx.Client) -> None:
    section("Scenario 5 — AI Copilot")
    r = client.post(
        f"{API_URL}/api/v1/chat",
        json={"question": "Which equipment had the worst GR&R this week?"},
    )
    if r.status_code == 503 or (r.status_code == 500 and "GEMINI" in r.text.upper()):
        skip("AI chat without GEMINI_API_KEY", "expected graceful failure")
    elif r.status_code == 200:
        ok("AI chat responds", r.json().get("answer", "")[:80])
    elif r.status_code in (422, 503):
        skip("AI chat", f"HTTP {r.status_code} — no API key configured")
    else:
        fail("AI chat", f"HTTP {r.status_code}: {r.text[:150]}")


def scenario_6_failure(client: httpx.Client) -> None:
    section("Scenario 6 — Failure behavior")
    bad = client.get(f"{API_URL}/api/v1/grr/history", headers={"x-api-key": "wrong-key"})
    if bad.status_code == 403:
        ok("Wrong API key returns 403")
    else:
        fail("Wrong API key", f"HTTP {bad.status_code}")

    no_key = httpx.Client(timeout=10)
    r = no_key.get(f"{API_URL}/api/v1/grr/history")
    if r.status_code == 403:
        ok("Missing auth returns 403")
    else:
        fail("Missing auth", f"HTTP {r.status_code}")


def main() -> int:
    print(f"Customer walkthrough — API={API_URL} Dashboard={DASHBOARD_URL}")
    timeout = httpx.Timeout(60.0, connect=15.0)
    with httpx.Client(headers=HEADERS, timeout=timeout) as client:
        scenario_0_stack(client)
        scenario_1_grr(client)
        scenario_2_spc(client)
        scenario_3_alerts(client)
        scenario_4_audit(client)
        scenario_5_copilot(client)
        scenario_6_failure(client)

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped")
    print(f"{'=' * 60}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
