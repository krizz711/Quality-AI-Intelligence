"""
Full workflow test for the Quality Control AI Agent.
Tests: Auth -> GR&R Analysis -> SPC Monitoring -> AI Chat -> Alerts -> Audit Trail
"""
import os, sys
os.environ['PYTHONIOENCODING'] = 'utf-8'
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import requests
import json
import sys

BASE = "http://localhost:8000"
HEADERS = {}

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def ok(msg): print(f"  [OK]   {msg}")
def fail(msg): print(f"  [FAIL] {msg}")
def info(msg): print(f"  [INFO] {msg}")

# ─────────────────────────────────────────────────────────────
# STEP 1 — Health Check
# ─────────────────────────────────────────────────────────────
section("STEP 1 — API Health Check")
try:
    r = requests.get(f"{BASE}/api/v1/health", timeout=10)
    data = r.json()
    ok(f"Status: {data.get('status')} | Version: {data.get('version')}")
    info(f"Dependencies: {data.get('dependencies')}")
except Exception as e:
    fail(f"API not reachable: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# STEP 2 — Authentication
# ─────────────────────────────────────────────────────────────
section("STEP 2 — Authentication (Get JWT Token)")
token = None
for creds in [
    {"username": "admin", "password": "admin"},
    {"username": "quality_admin", "password": "admin123"},
    {"username": "testuser", "password": "testpass"},
]:
    try:
        r = requests.post(
            f"{BASE}/api/v1/auth/token",
            data=creds,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if r.status_code == 200:
            token = r.json().get("access_token")
            ok(f"Logged in as '{creds['username']}' — token: {token[:30]}...")
            break
        else:
            info(f"Tried {creds['username']}: {r.status_code} — {r.text[:80]}")
    except Exception as e:
        fail(str(e))

if not token:
    # Try API key auth instead (read from the environment — never hard-code secrets)
    API_KEY = os.environ.get("API_AUTH_KEY", "")
    HEADERS = {"X-API-Key": API_KEY}
    ok("Using API key authentication")
else:
    HEADERS = {"Authorization": f"Bearer {token}"}

# ─────────────────────────────────────────────────────────────
# STEP 3 — GR&R Analysis
# ─────────────────────────────────────────────────────────────
section("STEP 3 — GR&R Analysis (CMM-001 / Shaft Diameter)")

# Build 3 operators × 10 parts × 2 reps measurement data
op_a = [10.02, 10.01, 9.99, 10.03, 10.00, 9.98, 10.01, 10.02, 9.99, 10.00,
        10.01, 10.00, 9.98, 10.02, 10.00, 9.99, 10.01, 10.00, 9.98, 10.02]
op_b = [10.03, 10.02, 10.00, 10.04, 10.01, 9.99, 10.02, 10.03, 10.00, 10.01,
        10.02, 10.01, 9.99, 10.03, 10.01, 10.00, 10.02, 10.01, 9.99, 10.03]
op_c = [10.01, 10.00, 9.98, 10.02, 9.99, 9.97, 10.00, 10.01, 9.98, 9.99,
        10.00, 9.99, 9.97, 10.01, 9.99, 9.98, 10.00, 9.99, 9.97, 10.01]

measurements = []
parts = [f"P{i+1:03d}" for i in range(10)]
operators = ["Op-A", "Op-B", "Op-C"]
op_data = [op_a, op_b, op_c]

for op_idx, (op, vals) in enumerate(zip(operators, op_data)):
    for rep in range(2):
        for part_idx, part in enumerate(parts):
            measurements.append({
                "part": part,
                "operator": op,
                "measurement": vals[rep * 10 + part_idx]
            })

payload = {
    "part_ids": parts,
    "operator_ids": operators,
    "measurements": measurements,
    "method": "xbar_r",
    "tolerance": 0.1,
    "equipment_id": "CMM-001",
    "metadata": {"characteristic_name": "Shaft Diameter"}
}

try:
    r = requests.post(f"{BASE}/api/v1/studies/grr", json=payload, headers=HEADERS, timeout=30)
    if r.status_code in (200, 201):
        data = r.json()
        ok(f"GR&R Study Completed!")
        ok(f"  Study ID   : {data.get('study_id')}")
        ok(f"  GR&R %     : {data.get('grr_percent'):.2f}%")
        ok(f"  Acceptance : {data.get('acceptance')}")
        ok(f"  NDC        : {data.get('ndc')}")
        details = data.get('details', {})
        if details:
            info(f"  EV (Repeatability)   : {details.get('ev', details.get('repeatability', 'N/A'))}")
            info(f"  AV (Reproducibility) : {details.get('av', details.get('reproducibility', 'N/A'))}")
        grr_study_id = data.get('study_id')
    else:
        fail(f"GR&R failed: {r.status_code} — {r.text[:300]}")
        grr_study_id = None
except Exception as e:
    fail(f"GR&R exception: {e}")
    grr_study_id = None

# ─────────────────────────────────────────────────────────────
# STEP 4 — SPC Analysis (Out-of-Control Scenario)
# ─────────────────────────────────────────────────────────────
section("STEP 4 — SPC Real-Time Monitoring (Out-of-Control Process)")

spc_values = [10.01, 10.02, 9.99, 10.03, 10.00, 9.98, 10.01, 10.02, 9.99, 10.00,
              10.15, 10.18, 10.20, 10.22, 10.19, 10.21, 10.23, 10.25, 10.20, 10.22]

try:
    r = requests.post(f"{BASE}/api/v1/spc/analyze", json={
        "values": spc_values,
        "chart_type": "xbar_r",
        "subgroup_size": 5,
        "part_number": "SHAFT-001",
        "characteristic_name": "OD"
    }, headers=HEADERS, timeout=30)
    if r.status_code == 200:
        data = r.json()
        ok(f"SPC Analysis Complete!")
        ok(f"  Chart Type : {data.get('chart_type')}")
        ok(f"  UCL        : {data.get('ucl'):.4f}")
        ok(f"  CL         : {data.get('cl'):.4f}")
        ok(f"  LCL        : {data.get('lcl'):.4f}")
        ooc = data.get('out_of_control_indices', [])
        if ooc:
            fail(f"  OUT-OF-CONTROL POINTS at indices: {ooc}")
        else:
            ok("  No out-of-control points detected")
        nelson = data.get('nelson_violations', {})
        if nelson:
            for rule, indices in nelson.items():
                if indices:
                    fail(f"  Nelson {rule} violated at: {indices}")
        else:
            ok("  No Nelson rule violations")
    else:
        fail(f"SPC failed: {r.status_code} — {r.text[:300]}")
except Exception as e:
    fail(f"SPC exception: {e}")

# ─────────────────────────────────────────────────────────────
# STEP 5 — AI Chat / Copilot
# ─────────────────────────────────────────────────────────────
section("STEP 5 — AI Copilot Chat")

prompts = [
    "Analyze the current quality trends and identify any concerning patterns",
    "What GR&R threshold should we use for a critical safety measurement?",
    "Our SPC chart is showing a run of 7 consecutive points above the centerline on the shaft diameter process. What action should we take?"
]

for i, prompt in enumerate(prompts, 1):
    try:
        r = requests.post(f"{BASE}/api/v1/chat", json={"message": prompt}, headers=HEADERS, timeout=60)
        if r.status_code == 200:
            data = r.json()
            reply = data.get('response') or data.get('message') or data.get('content') or str(data)
            ok(f"Q{i}: {prompt[:60]}...")
            info(f"   AI: {reply[:200]}...")
        else:
            # Try alternative endpoint
            r2 = requests.post(f"{BASE}/api/v1/ai/chat", json={"message": prompt}, headers=HEADERS, timeout=60)
            if r2.status_code == 200:
                data = r2.json()
                reply = data.get('response') or data.get('message') or str(data)
                ok(f"Q{i} (via /ai/chat): {prompt[:60]}...")
                info(f"   AI: {reply[:200]}...")
            else:
                fail(f"Q{i} chat: {r.status_code}/{r2.status_code} — {r.text[:100]}")
    except Exception as e:
        fail(f"Q{i} chat exception: {e}")

# ─────────────────────────────────────────────────────────────
# STEP 6 — Alerts
# ─────────────────────────────────────────────────────────────
section("STEP 6 — Alerts Dashboard")

for endpoint in ["/api/v1/alerts", "/api/v1/quality/alerts"]:
    try:
        r = requests.get(f"{BASE}{endpoint}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            alerts = data if isinstance(data, list) else data.get('alerts', data.get('items', []))
            ok(f"Alerts endpoint: {endpoint} — {len(alerts)} alerts found")
            for a in alerts[:3]:
                info(f"   [{a.get('severity','?')}] {a.get('message', a.get('title', str(a)))[:80]}")
            break
        else:
            info(f"  {endpoint}: {r.status_code}")
    except Exception as e:
        info(f"  {endpoint}: {e}")

# ─────────────────────────────────────────────────────────────
# STEP 7 — Review Queue
# ─────────────────────────────────────────────────────────────
section("STEP 7 — Review Queue (Pending GR&R Reviews)")
try:
    r = requests.get(f"{BASE}/api/v1/reviews", headers=HEADERS, timeout=10)
    if r.status_code == 200:
        reviews = r.json()
        ok(f"Reviews found: {len(reviews)}")
        for rev in reviews[:3]:
            info(f"   ID:{rev.get('id','?')} Status:{rev.get('status','?')} Equipment:{rev.get('equipment_id','?')}")
    else:
        fail(f"Reviews: {r.status_code} — {r.text[:100]}")
except Exception as e:
    fail(f"Reviews exception: {e}")

# ─────────────────────────────────────────────────────────────
# STEP 8 — Audit Trail
# ─────────────────────────────────────────────────────────────
section("STEP 8 — Audit Trail")
for endpoint in ["/api/v1/audit", "/api/v1/audit/events", "/api/v1/quality/audit"]:
    try:
        r = requests.get(f"{BASE}{endpoint}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            events = data if isinstance(data, list) else data.get('events', data.get('items', []))
            ok(f"Audit endpoint: {endpoint} — {len(events)} events")
            for ev in events[:3]:
                info(f"   {ev.get('event_type','?')} by {ev.get('actor','?')} at {str(ev.get('timestamp','?'))[:19]}")
            break
        else:
            info(f"  {endpoint}: {r.status_code}")
    except Exception as e:
        info(f"  {endpoint}: {e}")

# ─────────────────────────────────────────────────────────────
# STEP 9 — GR&R Retrieve Study
# ─────────────────────────────────────────────────────────────
section("STEP 9 — Retrieve Previously Submitted GR&R Study")
if grr_study_id:
    try:
        r = requests.get(f"{BASE}/api/v1/studies/{grr_study_id}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            ok(f"Study retrieved: {data.get('study_id')}")
            ok(f"  GR&R%: {data.get('grr_percent'):.2f}% | Acceptance: {data.get('acceptance')} | NDC: {data.get('ndc')}")
        else:
            fail(f"Retrieve study: {r.status_code} — {r.text[:100]}")
    except Exception as e:
        fail(f"Retrieve study exception: {e}")

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
section("TEST COMPLETE — All Workflows Executed")
print()
