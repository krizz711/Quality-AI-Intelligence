# Test Guide — Quality AI Intelligence (full integrated system)

A step-by-step checklist to verify **every integration, every UI page, and the AI
Agent** work together as one system. Tick each box as you go.

> Integrations are configured **once** on the **Connections** page (encrypted in the
> DB). The AI Agent dispatches **through the platform's alert pipeline**, so it uses
> those same channels — no separate setup.

---

## 0. Start the full stack (3 terminals)

```bash
# Terminal 1 — infra + main backend
docker compose up -d timescaledb redis kafka
.venv/Scripts/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
#   health: GET http://127.0.0.1:8000/health/ready  → db/redis/kafka all "ok"

# Terminal 2 — ADK agent service (reads live data from :8000; falls back to sample)
.venv-adk/Scripts/python -m uvicorn adk_agent.web:app --host 127.0.0.1 --port 8090
#   health: GET http://127.0.0.1:8090/agent/health  → {"ok": true, "agents":[...]}

# Terminal 3 — dashboard
cd dashboard
set AGENT_URL=http://127.0.0.1:8090
npm run dev          # http://localhost:3000
```

- [ ] `http://127.0.0.1:8000/health/ready` shows everything OK (no 502s on the dashboard)
- [ ] `http://127.0.0.1:8090/agent/health` returns the 4 agents
- [ ] `http://localhost:3000` loads the dashboard

> **Seed data:** set `SEED_DEMO_DATA=true` in `.env` before starting the backend, or
> push measurements (step 2) so the SPC Monitor and the agent have real series.

---

## 1. Connections page — configure & TEST every integration

Open **Connections** (sidebar → SETUP). For each channel, paste credentials and click its
**Test** button. A channel only counts as **Verified** when the live Test passes (a saved-
but-untested channel shows "Saved · not tested").

- [ ] **Slack** — paste the incoming webhook → **Test** → you get a real Slack message → badge = **Verified**
- [ ] **Email (SMTP)** — host/port/user/password/from → **Test** → test email arrives
- [ ] **Text message (SMS / Twilio)** — SID/token/from/to → **Test** → presence check passes
- [ ] **JIRA** — URL/email/API token/project key → **Test** → connection verified
- [ ] **AI summaries (Gemini)** — paste the Gemini key → **Test** → key accepted
- [ ] Edit any field → its badge clears back to "not tested" (proves validation is real)

> These credentials are stored **encrypted** and applied to the live app immediately — the
> autonomous monitor and the AI Agent both use them with no restart.

---

## 2. Get data in (any one path)

- [ ] **Upload** — Connections → upload a CSV/Excel of measurements (columns auto-detected), **or**
- [ ] **Simulate a feed** — `\.venv/Scripts/python scripts/synthetic_publisher.py --count 40 --equipment-id "CNC-LATHE-07"`, **or**
- [ ] **MES auto-connector** — set `MES_API_URL` etc. on the Connections page

---

## 3. Walk every dashboard page

- [ ] **Overview** — KPI cards load (active series, recent verdicts, monitor status, alerts) — no 502
- [ ] **SPC Monitor** — pick a process → I-MR chart with limits; click a flagged point → drill-down panel (rule + action + acknowledge)
- [ ] **GR&R Studies** — Setup → Data Entry (**Load sample**) → **Run GR&R Analysis** → gauge + verdict + AI commentary
- [ ] **Gage Registry** — add a gage; "Run study" prefills the GR&R wizard
- [ ] **Alert Inbox** — violations appear with severity + AI explanation
- [ ] **Review Queue** — approve/reject a result → audit entry created
- [ ] **Alert Rules** — a channel is only selectable when **Verified** (gated on the real Test)
- [ ] **Audit Trail** — every study/review/alert is logged with timestamp
- [ ] **AI Agent** — see step 4

---

## 4. AI Agent page — the integrated agent (the star)

Sidebar → **AI Agent**.

- [ ] **Process dropdown** lists your live processes (badge shows **🟢 Live data** vs Sample)
- [ ] **Run Autonomous Scan** → watch the agent steps appear in order:
  - [ ] *Process Monitor* — pulled N samples (source shown), found violations on the live SPC mini-chart
  - [ ] *Business Analyst* — Cost of Poor Quality in **dollars** (event / saved / annualized)
  - [ ] *Root-cause analysis* — a live **LLM** paragraph (real reasoning, e.g. "tool wear → replace the boring tool")
  - [ ] *Action Dispatch* — a **drafted alert** awaiting approval
- [ ] **Scan All** → fleet table ranks every process worst-first by violations + $ exposure; click a row to scan it
- [ ] **Approve & Send** → routes through the **platform alert pipeline** → confirm:
  - [ ] a new entry appears in **Alert Inbox** (the platform created it)
  - [ ] the real **Slack** message / **JIRA** ticket arrives (via the Connections-page channels)
  - [ ] the result reads **"via platform (Connections page)"**
- [ ] **Ask the agent** (chat) — e.g. *"A line drifted out of control for 30 min — what did it cost us?"* → the multi-agent system delegates and answers

---

## 5. Verify the alignment (one system, not a chatbot)

- [ ] The alert the **AI Agent** sent shows up in the **Alert Inbox** and the **Audit Trail**
- [ ] It used the **same Slack/JIRA** you configured on the **Connections page** (no separate setup)
- [ ] With the backend stopped, the agent still scans (sample data) and dispatch falls back to direct — proving it degrades gracefully

---

## 6. Automated tests

```bash
.venv-adk/Scripts/python -m pytest adk_agent/tests -q     # 29 agent-layer tests
.venv/Scripts/python    -m pytest -m "not integration" -q  # platform unit tests
```

- [ ] Agent-layer suite green (29 passed)
- [ ] Platform suite green (integration tests need the seeded DB up)

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Lots of **502** on dashboard pages | Main backend (`:8000`) isn't running — start Terminal 1 |
| AI Agent shows **"Sample data"** | Backend down or no seeded series — start `:8000` + seed/upload data |
| **Approve & Send** says "direct (.env fallback)" | Backend `:8000` unreachable — it sent via the agent's own env instead of the platform |
| Dispatch sends nothing | The channel isn't **Verified** on the Connections page (run its Test) |
| Agent service unreachable | Start Terminal 2; ensure the dashboard has `AGENT_URL=http://127.0.0.1:8090` |
