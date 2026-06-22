"""Autonomous quality monitor (ADK-layer demo).

Each cycle pulls the latest measurements, runs SPC, and when it finds special-cause
variation it computes the dollar impact (COPQ) and dispatches an alert. The
production streaming monitor lives in `agent/monitor.py`; this is the standalone,
agent-skills version for the capstone.

    python -m adk_agent.monitor                 # 5 cycles, DRY-RUN
    python -m adk_agent.monitor --send          # actually dispatch to Slack/JIRA
"""

from __future__ import annotations

import argparse
import time

from adk_agent import skills

PROCESS = "CNC-07 / bore_diameter"


def get_latest_series(cycle: int) -> list[float]:
    """Pluggable data source. Demo: in control early, then a shift appears."""
    scenario = "in_control" if cycle < 2 else "shift"
    return skills.generate_sample_series(n=40, scenario=scenario, seed=100 + cycle)["values"]


def run_cycle(cycle: int, *, send: bool) -> dict:
    spc = skills.analyze_spc_series(get_latest_series(cycle))
    if spc["in_control"]:
        print(f"[cycle {cycle}] {PROCESS}: in control ({spc['n_points']} pts) — OK")
        return {"cycle": cycle, "in_control": True}

    copq = skills.calculate_copq(
        units_per_hour=120, hours_out_of_control=0.5, baseline_defect_rate=0.01,
        out_of_control_defect_rate=0.15, scrap_cost_per_unit=45,
        escape_rate=0.10, escape_cost_per_unit=500, events_per_year=12)
    title = f"[Arad] SPC violation on {PROCESS}"
    message = (f"{spc['summary']} Estimated impact ${copq['total_copq']:,.0f} this event; "
               f"early detection saves ${copq['savings_from_early_detection']:,.0f}. "
               f"Recommend stopping the line and checking tool wear.")
    print(f"[cycle {cycle}] {PROCESS}: OUT OF CONTROL — {spc['violation_count']} violations, "
          f"COPQ ${copq['total_copq']:,.0f}")
    result = skills.dispatch_quality_alert(title=title, message=message, severity="critical", confirm=send)
    print(f"           dispatched -> {result.get('sent_to')}" if send
          else "           (dry-run) would alert Slack + JIRA; --send to dispatch")
    return {"cycle": cycle, "in_control": False, "violations": spc["violation_count"],
            "copq": copq["total_copq"], "dispatch": result["status"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Arad autonomous quality monitor")
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    print(f"Arad autonomous monitor — {args.cycles} cycles, "
          f"{'LIVE (sends alerts)' if args.send else 'DRY-RUN'}\n")
    for cycle in range(args.cycles):
        run_cycle(cycle, send=args.send)
        if cycle < args.cycles - 1:
            time.sleep(args.interval)
    print("\nMonitor finished.")


if __name__ == "__main__":
    main()
