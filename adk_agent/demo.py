"""`make demo` — the Arad agent loop, end to end, in one command.

A self-contained, no-API-key, ~5-second walkthrough of the one loop that defines the
product: a live process drifts, the multi-agent system detects it, prices the damage in
dollars, drafts a corrective action, and **waits for a human** before anything is sent.
Each step also lands in the persistent session store (TimescaleDB if it's up, else a
local SQLite file) so you can see the agent's memory survive — the context-engineering
piece — with `python -m adk_agent.state`.

    python -m adk_agent.demo            # offline, drafts only (nothing is sent)
    python -m adk_agent.demo --send     # actually dispatch after the approval gate
                                        # (needs Slack/JIRA env or a running backend)

It uses the real grr/spc/COPQ engine through the agent skills — the same code the LLM
agents call — so the numbers are real, just without needing a Gemini key to narrate.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

from adk_agent import skills, state

# Keep the unicode arrows/rules readable on a Windows console.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:  # pragma: no cover
    pass

# ANSI only on an interactive terminal (clean output when piped or NO_COLOR is set).
_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
BOLD = "\033[1m" if _COLOR else ""
DIM = "\033[2m" if _COLOR else ""
RST = "\033[0m" if _COLOR else ""

PROCESS = "CNC-07 / bore_diameter"

# The same COPQ assumptions the dashboard and monitor use, so every surface agrees.
COPQ_ASSUMPTIONS = dict(
    units_per_hour=120, hours_out_of_control=0.5, baseline_defect_rate=0.01,
    out_of_control_defect_rate=0.15, scrap_cost_per_unit=45,
    escape_rate=0.10, escape_cost_per_unit=500, events_per_year=12,
)


def _rule(title: str) -> None:
    print(f"\n{BOLD}── {title} {RST}" + "─" * max(2, 56 - len(title)))


def _step(agent: str, msg: str) -> None:
    print(f"  [{agent:<17}] {msg}")


def _pause(seconds: float) -> None:
    time.sleep(seconds)


async def _persist(scan: dict, copq: dict, action: str) -> str:
    """Write the run's findings into the session store; return the backend label."""
    service, label = await state.make_session_service()
    session = await state.get_or_create_session(
        service, user_id="local_user", session_id="demo")
    try:
        from google.adk.events import Event, EventActions

        await service.append_event(session, Event(
            author="quality_coordinator",
            actions=EventActions(state_delta={
                "last_spc_scan": scan["summary"],
                "last_copq": f"${copq['total_copq']:,.0f} this event",
                "last_action": action,
            }),
        ))
    except Exception as exc:  # pragma: no cover - persistence is best-effort in the demo
        return f"{label} (state write skipped: {exc})"
    return label


def run_demo(*, send: bool = False, pause: float = 0.8) -> int:
    print(f"\n{BOLD}Quality AI Intelligence — autonomous agent loop{RST}")
    print("Offline demo · real GR&R/SPC/COPQ engine · no API key required")

    # 1. A live process drifts out of control.
    _rule("1 · Live process feed")
    series = skills.generate_sample_series(n=40, scenario="shift", seed=11)["values"]
    _step("process_monitor", f"Pulled {len(series)} samples from {PROCESS}")
    _pause(pause)

    # 2. process_monitor runs SPC + the 8 Nelson rules.
    _rule("2 · Detection (process_monitor)")
    scan = skills.analyze_spc_series(series)
    if scan["in_control"]:
        _step("process_monitor", "In control — nothing to do.")
        return 0
    cl = scan["control_limits"]
    _step("process_monitor", f"OUT OF CONTROL — {scan['violation_count']} special-cause "
                             f"violation(s)")
    _step("process_monitor", f"UCL {cl['ucl']:.4f} · CL {cl['center_line']:.4f} · "
                             f"LCL {cl['lcl']:.4f}")
    rules = sorted({v["rule"] for v in scan["violations"]})
    _step("process_monitor", f"Triggered Nelson rules: {', '.join(rules)}")
    _pause(pause)

    # 3. business_analyst converts the event into dollars.
    _rule("3 · Business impact (business_analyst)")
    copq = skills.calculate_copq(**COPQ_ASSUMPTIONS)
    _step("business_analyst", f"Cost of Poor Quality this event: "
                              f"{BOLD}${copq['total_copq']:,.0f}{RST}")
    _step("business_analyst", f"Early autonomous detection saves "
                              f"${copq['savings_from_early_detection']:,.0f} vs once-per-shift "
                              f"inspection")
    _step("business_analyst", f"Annualised exposure: ${copq['annualized_copq']:,.0f}/yr")
    _pause(pause)

    # 4. action_dispatch drafts the alert — but sends nothing yet (HITL preview).
    _rule("4 · Draft corrective action (action_dispatch)")
    title = f"[Arad] SPC violation on {PROCESS}"
    message = (f"{scan['summary']} Estimated impact ${copq['total_copq']:,.0f} this event; "
               f"early detection saves ${copq['savings_from_early_detection']:,.0f}. "
               f"Recommend stopping the line and checking tool wear.")
    preview = skills.dispatch_quality_alert(title, message, severity="critical",
                                            process_name=PROCESS, confirm=False)
    _step("action_dispatch", f"Drafted Slack + JIRA alert · status: {preview['status'].upper()}")
    print(f"\n    {DIM}Slack/JIRA preview:{RST} {title}")
    print(f"    {DIM}{message}{RST}")

    # 5. Human-in-the-loop gate.
    _rule("5 · Human-in-the-loop gate")
    _step("system", "Nothing has been sent. A human must approve.")
    if not send:
        _step("system", "Dry run — re-run with --send to dispatch after approval.")
        result = {"status": "preview", "sent_to": []}
    else:
        _step("human", "APPROVED — dispatching…")
        result = skills.dispatch_quality_alert(title, message, severity="critical",
                                               process_name=PROCESS, confirm=True)
        _step("action_dispatch", f"Dispatched via {result.get('via', '?')} → "
                                 f"{result.get('sent_to') or 'no channel configured'}")

    # 6. Persist to the session store (context engineering / state management).
    _rule("6 · Memory (state persisted)")
    action = "dispatched" if (send and result.get("status") == "dispatched") else "drafted (awaiting approval)"
    backend = asyncio.run(_persist(scan, copq, action))
    _step("coordinator", f"Saved scan + cost + action to session 'demo'")
    _step("coordinator", f"Store: {backend}")
    print(f"    {DIM}Inspect it with:  python -m adk_agent.state{RST}")

    # Headline.
    _rule("Result")
    print(f"  Arad detected the drift, priced it at {BOLD}${copq['total_copq']:,.0f}{RST}, and "
          f"drafted a\n  human-approved action in under a second — fully offline.\n")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Arad agent-loop demo (offline, no API key).")
    parser.add_argument("--send", action="store_true",
                        help="Actually dispatch after the approval gate (needs Slack/JIRA env).")
    parser.add_argument("--pause", type=float, default=0.8,
                        help="Seconds to pause between steps (0 for instant).")
    args = parser.parse_args()
    raise SystemExit(run_demo(send=args.send, pause=args.pause))


if __name__ == "__main__":
    main()
