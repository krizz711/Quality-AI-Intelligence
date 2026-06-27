# Quality AI Intelligence

### An autonomous, multi‑agent quality engineer for the factory floor — it detects process drift, prices the impact in dollars, and drafts a human‑approved corrective action, in seconds instead of days.

**Track: Agents for Business** · **Code:** https://github.com/krizz711/Quality-AI-Intelligence · **Video:** _<add your YouTube link>_

---

## The problem: quality is slow, periodic, and reactive

Manufacturing quality is a multi‑trillion‑dollar concern, yet on most factory floors it still runs the way it did decades ago — slowly, periodically, and reactively. Three gaps cost real money every shift:

- **Measurement‑system studies are done by hand.** A Gage R&R study (the AIAG standard for deciding whether a gauge can even be trusted) takes a quality engineer hours of spreadsheet work. So it is done rarely, and bad gauges go unnoticed.
- **Control charts are checked once a shift, by whoever is watching.** Statistical Process Control (SPC) is the backbone of defect prevention, but a chart only helps when a human happens to look at it. A press that drifts out of control at 2 a.m. is discovered at 6 a.m. — four hours and a scrap bin later.
- **Nobody puts a dollar value on a violation.** Engineers see "a point crossed the limit." Plant managers need to hear "this event is worth $798 right now and $11,970 a year if we keep catching it late." Without that translation, quality loses every budget argument.

The cost of getting this wrong has a name in the industry: **Cost of Poor Quality (COPQ)** — scrap, rework, warranty, and recalls — and it routinely runs 15–20% of revenue. The opportunity is not a better chart. It is a system that **watches every process continuously, reasons about what it sees, prices the risk, and acts** — while a human stays in control of anything that leaves the building.

## Why agents — and why a *multi‑agent* system

This problem is a natural fit for agents, not a dashboard, because the work is a **chain of distinct judgments**, not a single prediction:

1. *Is this process statistically out of control?* — a deterministic question best answered by a rigorous statistics engine, not an LLM.
2. *What does that cost us?* — a business calculation grounded in scrap rates and inspection cadence.
3. *Why did it happen, and what's the one action to take now?* — open‑ended reasoning where an LLM genuinely helps.
4. *Who should hear about it, and through which channel?* — an action that touches real systems (Slack, Jira, email) and therefore needs a human gate.

Each step has a different "shape": some demand determinism and auditability, others demand language reasoning, one demands tool execution with guardrails. A **multi‑agent system** lets each specialist do exactly one job well, with a coordinator that plans the sequence and synthesizes the result. That separation is also what makes the system trustworthy: the numbers come from a tested statistics library, the LLM only *explains and recommends*, and nothing is dispatched without approval.

## The solution

**Quality AI Intelligence** ("Arad") is a self‑hosted platform with a Google ADK multi‑agent layer on top of a real production stack. In a single autonomous scan it will:

- **Detect** — run Individuals & Moving‑Range (I‑MR) control charts and screen every active series against all eight Nelson / Western‑Electric rules, every 30 seconds over a rolling window.
- **Price** — translate the violation into **COPQ in US dollars** for this event, plus the annualized savings of catching it autonomously instead of once‑per‑shift.
- **Explain** — produce a plain‑English root cause and the single corrective action to take right now.
- **Act — with a human in the loop** — draft a Slack message, an email, and a Jira ticket, and **send nothing** until an engineer approves. On approval it fans out to the real tools and logs every step to an immutable audit trail.

It also computes **AIAG Gage R&R** studies (X̄–R and ANOVA methods — %GRR, ndc, variance components) instantly, so the measurement system itself is validated, not assumed.

## Architecture

The whole system runs from **one `docker compose up`**. A FastAPI service is the brain: it serves the REST API and, in‑process, runs the autonomous monitor, the MES/QMS connector, and database migrations. The **Google ADK agent layer** runs alongside it and reads the platform's live data.

![Architecture](docs/assets/architecture.svg)

**The multi‑agent layer (`adk_agent/`):** a `quality_coordinator` root agent delegates to four specialists:

| Agent | Job | Grounded in |
|---|---|---|
| **Process Monitor** | Pull the live series, run SPC, flag special‑cause violations | the real `spc/` engine |
| **Business Analyst** | Compute Cost of Poor Quality and early‑detection savings | `business.py` |
| **Root‑Cause Reasoner** | Diagnose the likely assignable cause, recommend one action | Gemini (via ADK) |
| **Action Dispatcher** | Draft the alert and route it — behind a human gate | `dispatch.py` + guardrails |

The agents reach the rest of the system through an **MCP server** (`adk_agent/mcp_server.py`) exposing eight tools over stdio — the Gage R&R engine, the SPC analyzer, COPQ pricing, MES ingest, and the Slack/Email/Jira dispatchers. **Agent skills** (`skills.py`) wrap the *same* tested statistics library the platform uses, so the agent and the product can never disagree on a number.

**State / context engineering:** ADK sessions are persisted in **TimescaleDB** (with a SQLite and in‑memory fallback), giving the agent working memory — "what did that line cost us last time?" is answered from state, not recomputed.

**Supporting stack:** Next.js dashboard, TimescaleDB hypertables for time‑series data, Kafka for streaming ingestion, Redis, and a full observability suite (Prometheus, Grafana, MLflow). Integration credentials are configured in the UI and stored **encrypted (Fernet)** — never in code.

## How a scan flows (detect → price → explain → act)

A press drifts. The autonomous monitor flags it within 30 seconds. The coordinator runs the chain: the Process Monitor confirms 40 special‑cause points across rules 1, 2, 3, 5, 6, 8; the Business Analyst prices it at **$798 this event / $11,970 saved per year** by early detection; the Root‑Cause Reasoner attributes it to progressive tool wear and recommends stopping the line and inspecting the fixture; the Action Dispatcher drafts a CRITICAL Slack/email/Jira alert and **waits**. An engineer clicks *Approve & Send* — and only then does the alert fan out for real (a live Slack message, an email, and Jira ticket KAN‑5), each written by the agent. That is **human‑in‑the‑loop by design**, not as an afterthought.

## The build, and the course concepts demonstrated

The project applies well beyond the required three course concepts:

| Concept | Where |
|---|---|
| **Multi‑agent system (ADK)** | `adk_agent/agents.py` — coordinator + 4 specialists |
| **MCP server** | `adk_agent/mcp_server.py` — 8 tools over stdio |
| **Agent skills** | `adk_agent/skills.py` — wrap the real GR&R / SPC engine |
| **Security / guardrails** | `adk_agent/guardrails.py` — input refusal, tool allowlist, audit log, encrypted secrets, human gate |
| **Context engineering (state)** | `adk_agent/state.py` — ADK sessions in TimescaleDB |
| **Deployability** | `adk_agent/web.py` + the one‑command Docker stack (`adk deploy`‑ready) |
| **Evaluation** | `adk_agent/tests/` — 35 tests, no API key required |

**Tools & technologies:** Google ADK, MCP, Gemini (with pluggable Claude/OpenAI and a deterministic AIAG fallback so summaries never hang — even with no AI key); FastAPI, SQLAlchemy, Pydantic; Next.js 16, React, TypeScript, Tailwind; NumPy/SciPy/pandas for the statistics engines; TimescaleDB, Kafka, Redis; Docker Compose, Prometheus, Grafana, MLflow. The `grr/` and `spc/` engines are held to **100% test coverage** and match the AIAG reference tables exactly — the rigor judges can verify, not just claim.

## Value and results

For the **Agents for Business** track, the headline is the money:

- **Speed:** detection in **seconds**, not a shift — every hour shaved off a drift is scrap avoided.
- **Dollars:** every violation is reported as **COPQ in USD** with annualized savings, so quality finally speaks the language of the plant budget — e.g., **$11,970/yr saved** on a single press by catching drift early instead of once‑per‑shift.
- **Labor:** Gage R&R studies that took hours of manual spreadsheet work return in seconds.
- **Trust & governance:** AIAG‑correct math, encrypted credentials, an API‑key‑protected backend, and a complete audit trail — enterprise‑ready, with a human approving every external action.

## Journey & challenges

The hardest design decision was **where to let the LLM near the numbers — and the answer was: nowhere**. Statistical verdicts and dollar figures are computed deterministically and only *described* by the model; this is what makes the output auditable and the demo reproducible. Keeping the agent and the product honest meant the agent's skills had to call the **exact same** tested engine the platform serves, not a re‑implementation. The fallback path mattered too: an 8‑second timeout guarantees a deterministic AIAG summary so the system is useful even with no AI key or a provider outage. Finally, making it *operable* — one Docker command, UI‑managed encrypted integrations, a first‑run getting‑started guide — turned a capstone prototype into something a quality engineer could actually run.

## What's next

Closing the loop further: feeding the relevant / false‑positive feedback (which already trains an on‑screen accuracy score) back into per‑process alert thresholds, adding predictive tool‑wear forecasting from the time‑series history, and a fleet view that ranks every process by this week's financial risk.

**Quality AI Intelligence** turns quality from a slow, reactive chore into an autonomous, multi‑agent system that detects, prices, explains, and acts — with a human in the loop, in seconds instead of days.
