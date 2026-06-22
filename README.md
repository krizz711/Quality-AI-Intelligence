<div align="center">

# Arad Quality Intelligence

### An autonomous, multi‑agent quality‑control system for manufacturing — GR&R, SPC, and 24/7 alerting, done in seconds instead of days.

**Arad detects process drift, prices the impact in dollars, and drafts a human‑approved corrective action in under a second.**

<p>
  <img alt="Python"        src="https://img.shields.io/badge/Python%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="FastAPI"       src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white">
  <img alt="Next.js"       src="https://img.shields.io/badge/Next.js%2016-000000?style=for-the-badge&logo=nextdotjs&logoColor=white">
  <img alt="Google ADK"    src="https://img.shields.io/badge/Google%20ADK-4285F4?style=for-the-badge&logo=google&logoColor=white">
  <img alt="TimescaleDB"   src="https://img.shields.io/badge/TimescaleDB-FDB515?style=for-the-badge&logo=timescale&logoColor=black">
  <img alt="Apache Kafka"  src="https://img.shields.io/badge/Apache%20Kafka-231F20?style=for-the-badge&logo=apachekafka&logoColor=white">
  <img alt="Docker"        src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white">
</p>

<p>
  <img alt="Gemini"    src="https://img.shields.io/badge/Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white">
  <img alt="MCP"       src="https://img.shields.io/badge/MCP-000000?style=flat-square&logo=modelcontextprotocol&logoColor=white">
  <img alt="Slack"     src="https://img.shields.io/badge/Slack-4A154B?style=flat-square&logo=slack&logoColor=white">
  <img alt="JIRA"      src="https://img.shields.io/badge/Jira-0052CC?style=flat-square&logo=jira&logoColor=white">
  <img alt="Twilio"    src="https://img.shields.io/badge/Twilio-F22F46?style=flat-square&logo=twilio&logoColor=white">
  <img alt="Grafana"   src="https://img.shields.io/badge/Grafana-F46800?style=flat-square&logo=grafana&logoColor=white">
  <img alt="Prometheus" src="https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white">
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-22c55e?style=flat-square">
</p>

</div>

---

## 60‑second demo (no API key, no Docker)

The single loop that defines the product — run it offline in one command:

```bash
make demo            # or, with no make:  python -m adk_agent.demo
```

You'll watch a live process drift out of control → the **process monitor** agent flag the
SPC/Nelson violations → the **business analyst** agent price the event in dollars (COPQ) →
the **action dispatch** agent draft a Slack/JIRA alert → **a human approve before anything
is sent**. The run is saved to the agent's persistent memory (inspect with
`python -m adk_agent.state`).

> Full setup — the offline agent, the whole Docker platform, and the integrated live
> system — is in [Running it](#running-it).

---

## Table of contents

1. [What is Arad Quality Intelligence?](#what-is-arad-quality-intelligence)
2. [The problem — quality work that eats days](#the-problem--quality-work-that-eats-days)
3. [The solution — an agent that never sleeps](#the-solution--an-agent-that-never-sleeps)
4. [The AI agent layer (Google ADK)](#the-ai-agent-layer-google-adk)
   - [Multi‑agent architecture](#multi-agent-architecture)
   - [How the agent connects to the system](#how-the-agent-connects-to-the-system)
   - [Human‑in‑the‑loop (HITL)](#human-in-the-loop-hitl)
   - [Context engineering — state in TimescaleDB](#context-engineering--state-in-timescaledb)
   - [Capstone concepts demonstrated](#capstone-concepts-demonstrated)
5. [Key features & advantages](#key-features--advantages)
6. [Technology stack](#technology-stack)
7. [Architecture](#architecture)
8. [Workflows (flowcharts)](#workflows)
9. [Running it](#running-it)
   - [Option A — the agent, offline (minimal)](#option-a--the-agent-offline-minimal)
   - [Option B — the full platform (Docker)](#option-b--the-full-platform-docker)
   - [Option C — the integrated live system](#option-c--the-integrated-live-system)
10. [Configuration & keys](#configuration--keys)
11. [Service URLs](#service-urls)
12. [Testing & evidence](#testing--evidence)
13. [Project layout](#project-layout)

---

## What is Arad Quality Intelligence?

**Arad Quality Intelligence** is a self‑hosted platform that automates the daily statistical
work of a manufacturing quality engineer, with a **Google ADK multi‑agent system** on top
that turns raw measurements into a priced, human‑approved action:

- **GR&R** — Gauge Repeatability & Reproducibility studies (AIAG **X̄‑R** and ANOVA) computed and interpreted instantly.
- **SPC** — Statistical Process Control charts (I‑MR) with **Nelson / Western Electric** rule detection.
- **An autonomous monitor** that watches every active measurement series **around the clock** and raises proactive alerts the moment a process drifts out of control.
- **A multi‑agent layer (ADK)** — specialist agents for measurement analysis, process monitoring, business‑cost analysis, and action dispatch, coordinated by a root agent and grounded in the **real** statistics engine.
- **Multi‑channel alerting** — Slack, Email, SMS (Twilio), and JIRA tickets — each carrying an **AI‑written explanation, a dollar impact, and a recommended action**.

It is built for **quality engineers, not developers**: data comes in automatically, the math
is AIAG‑correct, and every integration is configured from a point‑and‑click dashboard.

> Built for the **Kaggle × Google "Agents for Business"** capstone — the submission *is* the
> real product, made ADK‑compliant rather than a throwaway demo.

---

## The problem — quality work that eats days

In a typical plant, keeping a process "in control" is a **manual, reactive, after‑the‑fact** grind:

```text
  Measure parts ─▶ type into Excel/Minitab ─▶ run GR&R by hand ─▶ build SPC charts
        ─▶ eyeball them for violations ─▶ write a report ─▶ email whoever needs to know
```

| Pain point | What it actually costs |
| --- | --- |
| **GR&R studies done by hand** | Collecting parts × operators × trials, keying it in, running the ANOVA/X̄‑R math, and interpreting %GR&R / ndc takes **hours per study** — and reports are often **batched a day or more** behind. |
| **SPC charts are periodic** | Charts get refreshed per shift. Anything that goes wrong **between** manual checks is caught **late — after scrap is already on the floor.** |
| **Alerting is "did someone notice?"** | A human has to spot the violation and tell people. Latency is measured in **hours**, and it depends on who is paying attention. |
| **No dollar context** | "Is this violation a big deal?" — nobody translates a control‑chart breach into the money it costs, so triage is guesswork. |
| **Tribal interpretation & no audit trail** | "Is 18% GR&R okay?" lives in people's heads; "who reviewed this, and when?" is scattered across emails and spreadsheets. |

The net effect: quality is **slow, periodic, reactive, and inconsistent** — exactly the
opposite of what a control system should be.

---

## The solution — an agent that never sleeps

Arad flips every one of those problems:

| Before (manual) | After (Arad) |
| --- | --- |
| Pull data into spreadsheets by hand | **Data flows in automatically** — CSV/Excel upload, a timed MES/QMS pull, a Kafka stream, or a REST push |
| GR&R math by hand, hours per study | **Instant AIAG X̄‑R / ANOVA** with EV/AV/%GR&R/ndc + a written verdict |
| SPC charts checked per shift | **Continuous monitor** re‑analyses every active series **every 30 seconds** |
| Humans spot violations | **Nelson / Western Electric rules** fire automatically, de‑duplicated so you aren't spammed |
| "Is it a big deal?" is a guess | **Cost of Poor Quality (COPQ)** turns the event into **dollars** automatically |
| Someone emails around | **Slack / Email / SMS / JIRA** dispatched in seconds, **after a human approves** |
| No record of who reviewed what | **Audit log** + persistent agent memory of every study, scan, and decision |

**How much work it removes:** the loop of **detect → analyse → price → explain → notify**
goes from *hours‑to‑days and manual* to **seconds and automatic**, and monitoring goes from
*periodic* to *always‑on*.

| Task | Manual workflow | With Arad |
| --- | --- | --- |
| Run & interpret a GR&R study | **Hours** | **~10–15 seconds** after the data lands |
| Detect an out‑of‑control point | **Next manual SPC check** (per shift) | **≤ 30 s** after it happens |
| Price the business impact | Rarely done | **Instant COPQ in dollars** |
| Notify the right people | **Hours**, depends on who's watching | **Seconds**, automatic & multi‑channel, human‑approved |

---

## The AI agent layer (Google ADK)

The platform above is the proven engine. The **`adk_agent/`** package is a **Google Agent
Development Kit** multi‑agent system built *on that engine* — it reuses the exact `grr` / `spc`
math and the same Slack/JIRA integrations, so the agents' numbers are identical to the
dashboard's, and it runs **standalone** (just `numpy/pandas/scipy + google-adk + mcp`) without
needing Kafka/Postgres.

### Multi‑agent architecture

A root coordinator delegates to four specialists, each with its own tools, instructions, and
guardrails:

```mermaid
flowchart TD
    U(["Plant-manager question"]) --> C["quality_coordinator<br/>root agent"]
    C -->|delegates| MA["measurement_analyst<br/>AIAG GR&R / MSA"]
    C -->|delegates| PM["process_monitor<br/>SPC · Nelson · forecast"]
    C -->|delegates| BA["business_analyst<br/>Cost of Poor Quality"]
    C -->|delegates| AD["action_dispatch<br/>Slack + JIRA · HITL"]
    MA --> ENG[("real engine<br/>grr · spc · business")]
    PM --> ENG
    BA --> ENG
    AD --> SK["skills.py = MCP server<br/>(8 tools)"]
    C -. guardrails .-> GUARD["refuse · allowlist · audit"]
    classDef root fill:#2563eb,color:#ffffff,stroke:#1e40af,stroke-width:2px;
    classDef spec fill:#93c5fd,color:#0b1324,stroke:#3b82f6;
    classDef eng fill:#111827,color:#ffffff,stroke:#374151;
    classDef guard fill:#f59e0b,color:#0b1324,stroke:#b45309;
    class C root;
    class MA,PM,BA,AD spec;
    class ENG,SK eng;
    class GUARD guard;
```

- **Coordinator** ([`adk_agent/agents.py`](adk_agent/agents.py)) — routes plant‑manager
  questions to the right specialist; never invents numbers.
- **Specialists** write their findings into shared session state (see
  [Context engineering](#context-engineering--state-in-timescaledb)).
- **Skills** ([`adk_agent/skills.py`](adk_agent/skills.py)) are the one capability layer,
  exposed both as ADK function‑tools and as **MCP tools**
  ([`adk_agent/mcp_server.py`](adk_agent/mcp_server.py)) — one implementation, identical
  numbers everywhere.

### How the agent connects to the system

The agent is **not a separate chatbot** — it reads the *same live measurement series* the
dashboard's SPC monitor shows, and dispatches through the *same* configured channels:

```mermaid
sequenceDiagram
    autonumber
    participant D as Dashboard AI Agent
    participant A as ADK Agent Service
    participant API as Platform API
    participant DB as TimescaleDB
    participant CH as Slack / JIRA
    D->>A: Run Autonomous Scan (/agent/scan)
    A->>API: GET /spc/processes + /spc/history
    API->>DB: read live measurement series
    DB-->>API: series
    API-->>A: live SPC data
    Note over A: process_monitor: SPC + Nelson rules<br/>business_analyst: COPQ in $
    A->>DB: persist session.state (findings)
    A-->>D: draft alert + steps (nothing sent)
    alt human approves
        D->>A: Approve & Send
        A->>API: POST /alerts/trigger
        API->>CH: dispatch to configured channels
        CH-->>D: delivered
    else human rejects
        D-->>D: nothing sent
    end
```

- [`adk_agent/backend_client.py`](adk_agent/backend_client.py) pulls the real series from the
  platform API; if the backend is down it falls back to a representative sample so the agent
  still runs standalone (the dashboard badge shows **🟢 Live data** vs sample).
- The dashboard's **AI Agent** page
  ([`dashboard/src/components/pages/AIAgentPage.tsx`](dashboard/src/components/pages/AIAgentPage.tsx))
  animates `process_monitor → business_analyst → action_dispatch`, with a live SPC mini‑chart,
  the COPQ, and an **Approve & Send** button.
- Dispatch routes through the platform's alert pipeline so it uses the channels you configured
  once on the **Connections** page; only if the platform is unreachable does it fall back to
  direct Slack/JIRA from the agent's own env.

### Human‑in‑the‑loop (HITL)

No alert is ever sent autonomously. `dispatch_quality_alert(confirm=False)` (the default)
returns a **preview** and sends nothing; only an explicit `confirm=True` — issued after a human
clicks **Approve & Send** in the dashboard, or passes `--send` on the CLI — actually dispatches.
The dispatch agent's instructions make the preview → approve → confirm sequence mandatory, and
every tool call is written to an audit log.

### Context engineering — state in TimescaleDB

The multi‑agent system has **persistent memory**. ADK sessions (conversation history + working
state) are stored through `DatabaseSessionService` in **TimescaleDB** — the same instance the
platform uses for measurements — so context survives across turns *and* process restarts.
Resolution is automatic and graceful:

```text
ADK_SESSION_DB_URL  ▶  DATABASE_URL (TimescaleDB)  ▶  logs/adk_sessions.db (SQLite)  ▶  in‑memory
```

Each specialist writes its finding into `session.state` via an `output_key`
(`last_gage_study`, `last_spc_scan`, `last_copq`), and the coordinator reads them back as
*Working memory* — so *"what did that line cost us again?"* is answered from state, not by
recomputing. See [`adk_agent/state.py`](adk_agent/state.py); run `python -m adk_agent.state` to
see the active backend and stored sessions.

### Capstone concepts demonstrated

| Concept | Where |
|---------|-------|
| **Multi‑agent system (ADK)** | [`adk_agent/agents.py`](adk_agent/agents.py) — `quality_coordinator` + 4 specialists |
| **Context engineering (state)** | [`adk_agent/state.py`](adk_agent/state.py) — ADK sessions persisted in **TimescaleDB** (SQLite fallback); `output_key` state |
| **MCP server** | [`adk_agent/mcp_server.py`](adk_agent/mcp_server.py) — 8 tools over stdio |
| **Agent skills** | [`adk_agent/skills.py`](adk_agent/skills.py) — wraps the **real** `grr`/`spc` engine |
| **Security / guardrails** | [`adk_agent/guardrails.py`](adk_agent/guardrails.py) — input refusal + tool allowlist + audit; HITL dispatch |
| **Deployability** | [`adk_agent/web.py`](adk_agent/web.py) + the Docker stack (`adk deploy`‑ready) |
| **Evaluation** | [`adk_agent/tests/`](adk_agent/tests/) — **35 tests**, no API key required |

The business differentiator is **Cost of Poor Quality**
([`adk_agent/business.py`](adk_agent/business.py)): it reports impact in dollars and the savings
from early autonomous detection vs once‑per‑shift inspection.

---

## Key features & advantages

- **Autonomous monitor** — scans active series every 30 s over a rolling 180‑minute window; I‑MR limits + Nelson/Western‑Electric rules; 1‑hour duplicate suppression so one drift = one alert.
- **AIAG‑correct statistics** — the `grr/` and `spc/` engines are held to **100 % test coverage**; the numbers match AIAG reference tables exactly.
- **Multi‑agent reasoning + dollars** — ADK specialists turn a violation into a priced, explained, human‑approved action (COPQ in USD).
- **Four ways in, zero custom code** — CSV/Excel upload, MES/QMS auto‑connector (timed pull), Kafka stream, or REST push.
- **Multi‑channel alerting** — Slack, Email (SMTP), SMS (Twilio), JIRA — with per‑part de‑duplication and a human‑in‑the‑loop gate.
- **Pluggable AI, no lock‑in** — pick **Gemini / Claude / OpenAI** from the UI; an 8‑second timeout guarantees a fast **deterministic AIAG fallback** so summaries never hang — even with no AI key.
- **Built for quality engineers** — no API jargon in the UI; connections are tested with one click and stored **encrypted** (Fernet); a first‑run getting‑started guide and inline help.
- **Secure & self‑hosted** — API‑key‑protected business endpoints, JWT dashboard auth, encrypted integration secrets, audit log, agent tool allowlist.
- **Observability included** — Prometheus metrics, Grafana dashboards, MLflow tracking, Kafka UI, and pgAdmin ship in the stack.

---

## Technology stack

| Layer | Technology |
| --- | --- |
| **Backend / API** | <img src="https://img.shields.io/badge/-Python%203.12-3776AB?logo=python&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-FastAPI-009688?logo=fastapi&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-Pydantic-E92063?logo=pydantic&logoColor=white"> |
| **Agents** | <img src="https://img.shields.io/badge/-Google%20ADK-4285F4?logo=google&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-MCP-000000?logo=modelcontextprotocol&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-Gemini-8E75B2?logo=googlegemini&logoColor=white"> |
| **Statistics / ML** | <img src="https://img.shields.io/badge/-NumPy-013243?logo=numpy&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-pandas-150458?logo=pandas&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-SciPy-8CAAE6?logo=scipy&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-scikit--learn-F7931E?logo=scikitlearn&logoColor=white"> |
| **Frontend** | <img src="https://img.shields.io/badge/-Next.js%2016-000000?logo=nextdotjs&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-React-61DAFB?logo=react&logoColor=black"> &nbsp; <img src="https://img.shields.io/badge/-TypeScript-3178C6?logo=typescript&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-Tailwind%20CSS-06B6D4?logo=tailwindcss&logoColor=white"> |
| **Data & streaming** | <img src="https://img.shields.io/badge/-TimescaleDB-FDB515?logo=timescale&logoColor=black"> &nbsp; <img src="https://img.shields.io/badge/-PostgreSQL-4169E1?logo=postgresql&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-Apache%20Kafka-231F20?logo=apachekafka&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-Redis-DC382D?logo=redis&logoColor=white"> |
| **Alerting** | <img src="https://img.shields.io/badge/-Slack-4A154B?logo=slack&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-Jira-0052CC?logo=jira&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-Twilio-F22F46?logo=twilio&logoColor=white"> &nbsp; SMTP |
| **Ops & observability** | <img src="https://img.shields.io/badge/-Docker-2496ED?logo=docker&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-Prometheus-E6522C?logo=prometheus&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-Grafana-F46800?logo=grafana&logoColor=white"> &nbsp; <img src="https://img.shields.io/badge/-MLflow-0194E2?logo=mlflow&logoColor=white"> |

---

## Architecture

The stack is one Docker Compose deployment. The **API service** is the brain — it serves the
REST API *and* runs the autonomous monitor, the MES connector, and startup migrations
in‑process. The **ADK agent service** runs alongside it and reads the API's live data.

<p align="center">
  <img src="docs/assets/architecture.svg" width="100%"
       alt="Arad Quality Intelligence system architecture — data ingress (Apache Kafka, CSV/Excel, MES/QMS pull, REST push) flows into the FastAPI service (GR&R engine, SPC engine, autonomous monitor, and an AI summary router for Gemini/Claude/OpenAI), persists to TimescaleDB and Redis, fans out alerts to Slack/Email/Twilio/JIRA, with a Next.js dashboard and Prometheus/Grafana/MLflow observability — all orchestrated by Docker Compose.">
</p>

| Component | Package | Responsibility |
| --- | --- | --- |
| **REST API** | `api/` | FastAPI endpoints (`/api/v1/*`), auth, rate‑limiting, settings store |
| **GR&R engine** | `grr/` | AIAG X̄‑R / ANOVA calculations & acceptance verdicts (100 % covered) |
| **SPC engine** | `spc/` | I‑MR control charts + Nelson / Western Electric rules (100 % covered) |
| **ADK agent layer** | `adk_agent/` | Coordinator + 4 specialists, MCP server, guardrails, COPQ, persistent state |
| **Platform agent** | `agent/` | Autonomous monitor, alert engine/manager, Kafka consumer, AI helpers |
| **AI router** | `backend/services/` | Routes summaries to Gemini/Claude/OpenAI with timeout + deterministic fallback |
| **Settings store** | `core/` | Fernet‑encrypted, UI‑managed integration credentials applied to the live runtime |
| **Persistence** | `db/`, `alembic/` | SQLAlchemy models + migrations (TimescaleDB hypertables) |
| **Dashboard** | `dashboard/` | Next.js UI; talks to the API through a same‑origin proxy (API key stays server‑side) |

---

## Workflows

### 1. Autonomous monitoring loop

```mermaid
flowchart LR
    A(["Tick · every 30s"]) --> B["List active series"]
    B --> C["Pull last 180 min<br/>per series"]
    C --> D["Compute I-MR limits"]
    D --> E{"Nelson / Western<br/>Electric rule hit?"}
    E -->|no| A
    E -->|yes| F{"Seen in the<br/>last hour?"}
    F -->|"yes · dedup"| A
    F -->|no| G["Alert engine"]
    G --> H["AI explanation<br/>+ fallback"]
    H --> I["Dispatch"]
    I --> A
    classDef start fill:#2563eb,color:#ffffff,stroke:#1e40af,stroke-width:2px;
    classDef proc fill:#93c5fd,color:#0b1324,stroke:#3b82f6;
    classDef warn fill:#f59e0b,color:#0b1324,stroke:#b45309;
    class A start;
    class B,C,D,G,H,I proc;
    class E,F warn;
```

### 2. The agent loop (detect → price → approve)

```mermaid
flowchart TD
    S(["Live series · platform API"]) --> P["process_monitor<br/>SPC + Nelson rules"]
    P --> Q{"Out of control?"}
    Q -->|in control| Z["In control · stop"]
    Q -->|violation| B["business_analyst<br/>COPQ in $"]
    B --> D["action_dispatch<br/>draft Slack + JIRA"]
    D --> H{"Human approves?"}
    H -->|no| Z2["Nothing sent"]
    H -->|yes| X["Dispatch via platform pipeline"]
    P -.-> M[("session.state<br/>TimescaleDB")]
    B -.-> M
    D -.-> M
    classDef start fill:#2563eb,color:#ffffff,stroke:#1e40af,stroke-width:2px;
    classDef proc fill:#93c5fd,color:#0b1324,stroke:#3b82f6;
    classDef warn fill:#f59e0b,color:#0b1324,stroke:#b45309;
    classDef good fill:#22c55e,color:#06210f,stroke:#15803d;
    classDef bad fill:#ef4444,color:#ffffff,stroke:#b91c1c;
    classDef store fill:#111827,color:#ffffff,stroke:#374151;
    class S start;
    class P,B proc;
    class D warn;
    class X,Z good;
    class Z2 bad;
    class M store;
```

### 3. GR&R study

```mermaid
flowchart TD
    A["Upload study<br/>parts × operators × trials"] --> B["X-bar R / ANOVA<br/>EV · AV · GRR% · ndc"]
    B --> C{"%GRR verdict"}
    C -->|"under 10%"| D["Acceptable"]
    C -->|"10 to 30%"| E["Conditional"]
    C -->|"over 30%"| F["Unacceptable"]
    D --> G["Plain-English interpretation"]
    E --> G
    F --> G
    G --> H["Saved to history + audit log"]
    classDef good fill:#22c55e,color:#06210f,stroke:#15803d;
    classDef warn fill:#f59e0b,color:#0b1324,stroke:#b45309;
    classDef bad fill:#ef4444,color:#ffffff,stroke:#b91c1c;
    classDef step fill:#93c5fd,color:#0b1324,stroke:#3b82f6;
    class A,B,G,H step;
    class D good;
    class E warn;
    class F bad;
```

### 4. Alert dispatch fan‑out

```mermaid
flowchart LR
    V["Violation /<br/>failed study"] --> AE["Alert engine<br/>per-part dedup"]
    AE --> S["Slack webhook"]
    AE --> M["SMTP email"]
    AE --> X["Twilio SMS"]
    AE --> J["JIRA ticket"]
    classDef src fill:#f59e0b,color:#0b1324,stroke:#b45309;
    classDef hub fill:#2563eb,color:#ffffff,stroke:#1e40af;
    classDef ch fill:#93c5fd,color:#0b1324,stroke:#3b82f6;
    class V src;
    class AE hub;
    class S,M,X,J ch;
```

> Each destination only fires when it has been **configured and verified** on the Connections
> page — a wrong key stays blocked rather than failing silently.

---

## Running it

There are three ways to run Arad, smallest first. **Option A needs nothing but Python.**

### Option A — the agent, offline (minimal)

The lean ADK layer runs without Kafka/Postgres/MLflow and without an API key.

```bash
# 1 ▸ Lean install (one venv, standalone)
python -m venv .venv-adk && . .venv-adk/Scripts/activate   # (Linux/macOS: source .venv-adk/bin/activate)
pip install google-adk mcp python-dotenv requests numpy pandas scipy pytest pytest-asyncio \
    matplotlib nbformat "sqlalchemy[asyncio]" asyncpg aiosqlite
# (or: poetry install --with adk   ·   or: make adk-install)

# 2 ▸ The one-command demo — detect → price → draft → human gate (nothing is sent)
python -m adk_agent.demo            # or: make demo   ·   add --send to dispatch after approval

# 3 ▸ Run the tests (no API key) and inspect the agent's persisted memory
python -m pytest adk_agent/tests -q   # 35 tests   ·   or: make adk-test
python -m adk_agent.state             # shows the active state backend + stored sessions

# 4 ▸ Chat with the multi-agent system (needs a Gemini key in GEMINI_API_KEY / GOOGLE_API_KEY)
python -m adk_agent.run "A CNC line drifted out of control for 30 min — what did it cost us?"

# 5 ▸ ADK web UI + REST API
uvicorn adk_agent.web:app --port 8090            # http://localhost:8090
```

The Gemini key is read from the environment or a gitignored `adk_agent/.env`; the layer bridges
`GEMINI_API_KEY → GOOGLE_API_KEY` so it reuses the app's key. To persist agent state in
**TimescaleDB** instead of the SQLite fallback, bring the DB up first (`docker compose up -d
timescaledb`) or run `make demo-timescale`.

### Option B — the full platform (Docker)

> **Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
> and [Git](https://git-scm.com/). No local Python or Node required to run the stack.

```powershell
# 1 ▸ Clone
git clone https://github.com/krizz711/Quality-Control-GR-R-Analysis-Agent.git
cd Quality-Control-GR-R-Analysis-Agent

# 2 ▸ Create your secrets file from the template
Copy-Item .env.example .env          # macOS/Linux: cp .env.example .env

# 3 ▸ Edit .env and set AT LEAST these four (strong random strings):
#       API_AUTH_KEY, JWT_SECRET, POSTGRES_PASSWORD, ADMIN_PASSWORD
#     (every other integration is optional and can be set later in the UI)
notepad .env

# 4 ▸ Build and start the entire stack
docker compose up -d --build

# 5 ▸ Watch it come up healthy
docker compose ps
docker compose logs -f api      # wait for "Application startup complete", then Ctrl+C

# 6 ▸ Open the dashboard and sign in with ADMIN_USERNAME / ADMIN_PASSWORD
start http://localhost:3000     # macOS: open …   ·   Linux: xdg-open …
```

On **first boot** the API container is idempotent and automatically runs database migrations
(`alembic upgrade head`), seeds the dashboard login from `ADMIN_USERNAME` / `ADMIN_PASSWORD`,
creates MLflow experiments and Kafka topics, and starts the autonomous monitor.

```powershell
# Day-to-day
docker compose up -d --build api dashboard   # rebuild just the app after code changes
docker compose ps                            # health of every service
docker compose logs -f api                   # follow API logs
docker compose down                          # stop the stack (keeps data volumes)
docker compose down -v                       # stop AND wipe data (fresh start)
```

> **Troubleshooting** — *"Docker pipe / cannot connect"* → start Docker Desktop. *Kafka stuck
> after an abrupt stop* → `docker compose down` then `up -d`. *Stale dashboard after a rebuild*
> → hard‑refresh (Ctrl+Shift+R). Deeper ops detail lives in
> [DEPLOYMENT.md](DEPLOYMENT.md) and [RUNBOOK.md](RUNBOOK.md).

### Option C — the integrated live system

Run the platform, the agent service, and the dashboard together so the **AI Agent** page reads
live data (three terminals):

```bash
# Terminal 1 — infra + main backend (seeded data)
docker compose up -d timescaledb redis kafka
.venv/Scripts/python -m uvicorn api.main:app --port 8000

# Terminal 2 — the ADK agent service (reads live data from :8000, samples if it's down)
.venv-adk/Scripts/python -m uvicorn adk_agent.web:app --port 8090

# Terminal 3 — the dashboard (point its AI Agent page at the agent service)
cd dashboard && set AGENT_URL=http://127.0.0.1:8090 && npm run dev   # http://localhost:3000
```

Open the dashboard → **AI Agent** → **Run Autonomous Scan**: the agent pulls a real series,
flags violations on a live SPC chart, computes the dollar cost, and drafts a Slack/JIRA alert
for your approval. A step‑by‑step manual walkthrough is in [TEST_GUIDE.md](TEST_GUIDE.md).

---

## Configuration & keys

There are **two layers** of configuration, and it matters which goes where:

1. **`.env`** — *infrastructure & security secrets* (database, auth keys, admin login, Kafka). Set once at install; requires a container recreate to change.
2. **Connections page (UI)** — *integration & AI keys* (Slack, Email, SMS, JIRA, QMS, AI provider). Stored **encrypted** in the database, applied to the live runtime instantly, and **testable with one click**. No restart, no file edits.

### `.env` — minimal setup

You only need the first block to boot; everything else is optional and can be set in the UI.
Full template in [`.env.example`](.env.example).

```dotenv
# --- Runtime & security (REQUIRED — use strong random values) -------------------
ENVIRONMENT=development
API_AUTH_KEY=replace-with-a-strong-random-secret-min-32-chars
JWT_SECRET=replace-with-a-strong-jwt-secret-min-32-chars
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3002
ALLOW_MOCK_DATA=false

# --- First-run dashboard admin (seeded once on boot) ----------------------------
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-with-a-strong-admin-password
SEED_DEMO_DATA=false                 # seed a small demo series for a first look

# --- Database (TimescaleDB; also backs ADK agent session state) -----------------
POSTGRES_DB=arad_quality
POSTGRES_USER=arad
POSTGRES_PASSWORD=replace-with-a-strong-db-password
DATABASE_URL=postgresql+asyncpg://arad:replace-with-a-strong-db-password@localhost:5433/arad_quality

# --- Streaming ------------------------------------------------------------------
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MEASUREMENTS_TOPIC=quality.measurements
MEASUREMENTS_DLQ_TOPIC=quality.measurements.dlq

# --- Autonomous monitoring ------------------------------------------------------
ENABLE_AUTONOMOUS_MONITOR=true
MONITOR_INTERVAL_SECONDS=30

# --- AI summaries (optional — deterministic fallback if absent) -----------------
# Best set in the UI (Connections → AI summaries); these are an optional bootstrap.
LLM_PROVIDER=gemini                  # gemini | claude | openai
GEMINI_API_KEY=                      # also used by the ADK agent (bridged to GOOGLE_API_KEY)
ANTHROPIC_API_KEY=                   # Claude (default model: claude-opus-4-8)
OPENAI_API_KEY=                      # OpenAI (default model: gpt-4o-mini)

# --- Notifications (optional — all settable in the UI instead) ------------------
SLACK_WEBHOOK_URL=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_ADDRESS=
ALERT_EMAIL_RECIPIENTS=
JIRA_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
JIRA_PROJECT_KEY=QUAL

# --- ADK agent session store (optional override) --------------------------------
# Defaults to DATABASE_URL (TimescaleDB) → logs/adk_sessions.db (SQLite) → in-memory.
# ADK_SESSION_DB_URL=
# ADK_SESSION_BACKEND=                # set to "sqlite" or "memory" to override
```

> **Never commit a real `.env`.** It is gitignored. In production, rotate every secret, set
> `ENVIRONMENT=production`, and use a managed secret store.

### Connections — keys you set in the UI

Open **Connections** in the dashboard, fill in only what you use, click **Send test**, then
**Save**. Each key is stored encrypted.

| Connection | Field(s) | What it does | Where to get it |
| --- | --- | --- | --- |
| **Slack** | Webhook URL | Posts quality alerts to a Slack channel | Slack → *Incoming Webhooks* |
| **Email** | SMTP host, port, user, password, from, recipients | Emails the team when an alert needs a closer look | Your mail provider's SMTP settings |
| **SMS** | Twilio URL, auth token, from #, to #s | Texts a few people for critical alerts | [Twilio Console](https://console.twilio.com) |
| **JIRA** | URL, account email, API token, project key | Opens a ticket when a study fails or a problem repeats | Atlassian → *API tokens* (a `read:project`‑scoped token works) |
| **QMS / MES feed** | Events/API URL, token, field map, poll interval | Pushes/pulls quality events on a schedule | Your QMS/MES API endpoint |
| **AI summaries** | Provider (Gemini/Claude/OpenAI) + that provider's key | Plain‑English write‑ups on GR&R results and alerts | [Gemini](https://aistudio.google.com/apikey) · [Claude](https://console.anthropic.com) · [OpenAI](https://platform.openai.com/api-keys) |

---

## Service URLs

After `docker compose up`, these are available on `localhost`:

| Service | URL | Notes |
| --- | --- | --- |
| **Dashboard** | http://localhost:3000 | Sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD` |
| **API** | http://localhost:8000 | REST API (`/api/v1/*`) |
| **API health** | http://localhost:8000/health | Liveness/readiness |
| **ADK agent** | http://localhost:8090 | Agent web UI + `/agent/*` REST (Option A/C) |
| **Grafana** | http://localhost:3002 | Dashboards (on 3002 so the app keeps 3000) |
| **Prometheus** | http://localhost:9090 | Metrics |
| **Kafka UI** | http://localhost:8080 | Topic browser |
| **pgAdmin** | http://localhost:5050 | Database admin |
| **MLflow** | http://localhost:5000 | Experiment tracking |

---

## Testing & evidence

This build was taken through a **full from‑scratch installation and end‑to‑end validation**,
not just unit tests.

| Layer | Location | What it proves |
| --- | --- | --- |
| **Statistics core** | `tests/test_grr.py`, `tests/test_spc.py` | GR&R/SPC vs AIAG reference tables — **100 % coverage** on `grr/` + `spc/` |
| **ADK agent layer** | `adk_agent/tests/` | Skills, COPQ/forecast, guardrails, HITL, **and state persistence across restarts** — **35 tests**, no API key |
| **Unit** | `tests/unit/` | Alert generation, audit logging, LLM prompt templating, security (401/403) |
| **Integration** | `tests/integration/` | Kafka → TimescaleDB latency, Slack/Email/Jira dispatch via mock servers |
| **Contract** | `tests/contract/` | Every `/api/v1/` route against the OpenAPI spec (schemathesis) |
| **Performance / E2E** | `tests/performance/`, `tests/e2e/` | GR&R runtime ≤ 5 s, API p99 ≤ 1 s, fixture workflow + dashboard load (Playwright) |

**Verified success criteria**

- **GR&R analysis time** — target < 2 hours → **result ~10–15 s**, automatically.
- **Alert accuracy** — target > 95% → **validated** via the alert‑feedback loop + E2E simulation.
- Clean clone → `docker compose up --build` brings the whole stack healthy; all ingress paths
  (CSV upload, MES timed pull, autonomous monitor) and Slack delivery confirmed end‑to‑end.

Run the gates yourself:

```bash
make adk-test                    # ADK agent layer (35 tests, no API key)
make prod-check                  # lint + unit + dashboard production build
make test-docker                 # full suite inside the running Docker stack
docker compose up -d --build && python -m pytest -m integration -v   # live integration gate
```

More detail and step‑by‑step walkthroughs: [TESTING.md](TESTING.md),
[TEST_GUIDE.md](TEST_GUIDE.md), [USER_TESTING_GUIDE.md](USER_TESTING_GUIDE.md).

---

## Project layout

```text
Quality-Control-GR-R-Analysis-Agent/
├── adk_agent/        # Google ADK multi-agent layer: agents, skills, MCP server,
│                     #   guardrails, COPQ business logic, state (TimescaleDB), demo, tests
├── api/              # FastAPI REST API (api/quality_routes.py, ai_routes.py)
├── agent/            # Autonomous monitor, alert engine/manager, Kafka consumer, AI helpers
├── grr/              # GR&R (AIAG X̄-R / ANOVA) engine — 100% covered
├── spc/              # SPC (I-MR + Nelson rules) engine — 100% covered
├── backend/          # AI provider router (Gemini / Claude / OpenAI) + services
├── core/             # Config + Fernet-encrypted settings store
├── db/, alembic/     # SQLAlchemy models + migrations (TimescaleDB hypertables)
├── dashboard/        # Next.js 16 quality dashboard (incl. the live "AI Agent" page)
├── notebook/         # capstone_demo.ipynb — the agent story end to end with charts
├── docker/           # Service Dockerfiles
├── monitoring/       # Prometheus + Grafana provisioning
├── tests/            # Unit, integration, contract, performance, e2e
├── docker-compose.yml  ·  .env.example  ·  Makefile
├── DEPLOYMENT.md  RUNBOOK.md  TESTING.md  TEST_GUIDE.md  USER_TESTING_GUIDE.md
├── CONTRIBUTING.md  LICENSE
└── README.md         # ← you are here (the single source of truth)
```

---

<div align="center">

**Arad Quality Intelligence** — detect, price, explain, and notify, in seconds instead of days.

<sub>Self‑hosted · AIAG‑compliant · multi‑agent (ADK) · human‑in‑the‑loop · always‑on · MIT‑licensed</sub>

</div>
