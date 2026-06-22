# User Testing Guide — Act Like a Customer

A scripted walkthrough that tests the product exactly the way a paying quality engineer would use it. Run it yourself before every demo, and hand it to Agentalent evaluators or pilot customers as their acceptance script.

---

## 0. Start the system

```bash
# Full stack (API + DB + Kafka + dashboard + Grafana):
cp .env.example .env
docker compose up --build

# OR lightweight local dev:
make install && make run-api          # backend on :8000
cd dashboard && npm install && npm run dev   # dashboard on :3000
```

Open http://localhost:3000.

**Check first:** the sidebar pill must say **"Backend connected"** (green dot). If it says "Backend unreachable", open **Settings** (sidebar, bottom) → verify the API Base URL → **Test Connection** → Save. Enter the API key here if the backend has `API_AUTH_KEY` set.

---

## Scenario 1 — New gage arrives: run a GR&R study (the core promise)

*You are a quality engineer. A new bore micrometer was installed; you must qualify it before production uses it.*

1. Sidebar → **GR&R Studies**.
2. Step 1 (Setup): keep 3 operators, 10 parts, 2 trials. Process Name: `Bore Diameter — Mic #7`. Click **Generate Measurement Table**.
   - ✅ Expect: wizard advances to Step 2, table shows 60 rows (3×10×2).
   - ✅ Validation check: try 1 operator — the form must refuse (minimum 2).
3. Step 2 (Data Entry): enter values around 12.7 with small variation (e.g. 12.69–12.72), OR prepare a CSV with header `operator,part,trial,value` and use **Import CSV**.
   - ✅ Expect: Grand Mean updates live; Data Integrity card counts entered values (e.g. 60/60).
   - ✅ Negative check: click **Proceed to Analysis** with empty cells — it must block with a toast.
4. Step 3: click **Run GR&R Analysis**.
   - ✅ Expect: gauge dial with Total GR&R %, verdict badge per AIAG (<10% Acceptable, 10–30% Conditional, >30% Unacceptable), EV/AV/NDC metrics, AI narrative.
5. Click **Export PDF Report** → print dialog with a clean report.
6. Sidebar → **Overview** → the study appears in *Recent GR&R Results*. Sidebar → **Audit Trail** → a `grr` entry was recorded.

**Pass criterion (the success metric you sell):** wall-clock time from step 1 to PDF < 2 hours including operator measurement time; the software portion takes minutes.

## Scenario 2 — Live production monitoring (SPC)

*Your torque press streams measurements; you want drift caught automatically.*

1. Sidebar → **SPC Monitor**. Register process `Torque Press Line 1` (＋ button).
2. Click **Load 15 baseline points** — control chart renders with UCL/CL/LCL and shaded sigma zones.
3. Submit normal points (5.01, 4.99, 5.02…) → chart stays **In control** (green badge).
4. Now simulate drift: submit 6–9 rising values (5.04, 5.05, 5.06, 5.07, 5.08, 5.09).
   - ✅ Expect: violation badge turns red, the offending points render as red dots, the Nelson rule + description appears below the chart, and a toast announces the violation count.
5. Sidebar → **Overview** → the process appears in *SPC Monitoring* with an **Open SPC Monitor** shortcut.

## Scenario 3 — Alert triage (the >95% accuracy loop)

1. Sidebar → **Alert Inbox**. Active/Critical/Resolved-Today counters at top.
2. Filter by severity, search by process name — list updates instantly.
3. Open **Details** on an alert: severity, process, message, timestamps, recommended action.
4. Click 👍 **Relevant** on a true alert, 👎 **False Positive** on a noisy one.
   - ✅ Expect: confirmation toast; buttons disable after voting (no double-counting).
   - This feedback drives `GET /api/v1/alerts/accuracy` — the metric in your sales pitch.
5. Click **Resolve** on an active alert → it moves to Resolved; the bell badge in the top bar decreases.
6. Toggle the bell icon in the filter bar to silence/enable popup notifications for incoming alerts.

## Scenario 4 — Compliance audit

1. Sidebar → **Audit Trail**.
2. ✅ Every action from scenarios 1–3 is listed with timestamp, action, entity, actor.
3. Search for `grr`, filter by entity type, then **Export CSV** → file downloads.

## Scenario 5 — AI Copilot

1. Sidebar → **AI Copilot** (or press **Ctrl+K** anywhere, type a question, hit Enter — it routes to the copilot).
2. Ask: *"Which equipment had the worst GR&R this week?"* and *"Summarize active alerts."*
   - ✅ Expect: answers referencing your real studies/alerts (requires `GEMINI_API_KEY` on the backend).
3. Test the message actions: copy, 👍/👎, regenerate.

## Scenario 6 — Failure behavior (what evaluators always probe)

1. Stop the backend. ✅ Sidebar flips to **"Backend unreachable"** (red) within a minute; pages show retry buttons, not blank screens; the copilot returns a graceful connection-error message pointing to Settings.
2. Restart the backend, click **Refresh** on Overview → data returns without a full reload.
3. In **Settings**, enter a wrong API key → requests fail with a visible toast (not silent corruption); restore the key.

---

## Bug-report template

| Field | Example |
| --- | --- |
| Scenario / step | 2.4 |
| Expected | Violation badge + red dots |
| Actual | Chart re-rendered without violation |
| Console/network | screenshot or copied error |
| Build | git SHA + browser |
