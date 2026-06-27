"""Generate the Kaggle submission notebook (notebook/capstone_demo.ipynb).

    .venv-adk/Scripts/python scripts/adk_build_notebook.py
"""

from __future__ import annotations

import pathlib

import nbformat as nbf

OUT = pathlib.Path(__file__).resolve().parent.parent / "notebook" / "capstone_demo.ipynb"


def md(t): return nbf.v4.new_markdown_cell(t.strip("\n"))
def code(t): return nbf.v4.new_code_cell(t.strip("\n"))


cells = [
    md("""
# Quality AI Intelligence — Capstone (Agents for Business)

A **Google ADK multi-agent system** built *on top of a production manufacturing-quality
platform*. It reuses the platform's validated AIAG GR&R + SPC engine and its real
Slack/JIRA alerting, and adds the capstone concepts: ADK multi-agent orchestration,
an MCP server, agent skills, security guardrails — plus a **Cost-of-Poor-Quality**
business layer that reports impact in dollars.

> Concepts demonstrated (6): multi-agent ADK · MCP server · agent skills · security ·
> deployability · evaluation — plus real Slack/JIRA dispatch (human-in-the-loop) and an
> autonomous monitor. The agent layer (`adk_agent/`) runs standalone — no Kafka/Postgres needed.
"""),
    code("""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent))   # repo root
%matplotlib inline
import matplotlib.pyplot as plt
from adk_agent import skills
print("skills:", [f.__name__ for f in skills.ALL_SKILLS])
"""),
    md("## 1. Is the gage trustworthy? — AIAG Gage R&R (real engine: `grr`)"),
    code("""
gage = skills.run_sample_gage_study(quality="acceptable", seed=1)
print(f"%GR&R = {gage['grr_percent']}%   ndc = {gage['ndc']}   ->  {gage['verdict'].upper()}")
for r in gage['remarks']: print(" -", r)
"""),
    md("## 2. Is the process in control? — SPC + Nelson rules (real engine: `spc`)"),
    code("""
values = skills.generate_sample_series(scenario="shift", n=40, seed=11)["values"]
spc = skills.analyze_spc_series(values); cl = spc["control_limits"]
print(spc["summary"])
viol = {v["index"] for v in spc["violations"]}; x = range(len(values))
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.plot(x, values, "-", color="#4e8cff")
ax.scatter([i for i in x if i in viol], [values[i] for i in x if i in viol], color="#ef4444", s=55, zorder=4, label="violation")
ax.axhline(cl["ucl"], color="#ef4444", ls="--"); ax.axhline(cl["center_line"], color="#22c55e"); ax.axhline(cl["lcl"], color="#ef4444", ls="--")
ax.set_title("SPC Individuals chart"); ax.legend(fontsize=8); ax.grid(alpha=0.15); plt.show()
"""),
    md("## 3. Will a drift breach the limit? — forecasting"),
    code("""
drift = skills.generate_sample_series(scenario="drift_to_breach", n=30, seed=2)["values"]
print(skills.forecast_breach(drift)["summary"])
"""),
    md("## 4. What does it cost? — Cost of Poor Quality (the business layer)"),
    code("""
copq = skills.calculate_copq(units_per_hour=120, hours_out_of_control=0.5, baseline_defect_rate=0.01,
    out_of_control_defect_rate=0.15, scrap_cost_per_unit=45, escape_rate=0.10, escape_cost_per_unit=500, events_per_year=12)
print(copq["summary"])
fig, ax = plt.subplots(figsize=(6.5, 4))
bars = ax.bar(["Autonomous\\n(~30 min)", "Manual\\n(shift end)"], [copq["total_copq"], copq["cost_if_caught_late"]],
              color=["#22c55e", "#ef4444"], width=0.55)
for b, v in zip(bars, [copq["total_copq"], copq["cost_if_caught_late"]]):
    ax.text(b.get_x()+b.get_width()/2, v, f"${v:,.0f}", ha="center", va="bottom", fontweight="bold")
ax.set_title("Cost of Poor Quality per event"); ax.set_ylabel("USD lost"); ax.grid(axis="y", alpha=0.15); plt.show()
print(f"Saves ${copq['savings_from_early_detection']:,.0f}/event (${copq['annualized_copq']:,.0f}/yr).")
"""),
    md("""
## 5. The multi-agent system + how it ships

Root **`quality_coordinator`** delegates to `measurement_analyst`, `process_monitor`,
`business_analyst`, and `action_dispatch` (Slack/JIRA, human-in-the-loop). The same skills
are an **MCP server** (`python -m adk_agent.mcp_server`); **guardrails** refuse injection /
secret-exfiltration before the model runs; an **autonomous monitor**
(`python -m adk_agent.monitor`) runs detect → cost → notify.

```python
# With a Gemini key:
from adk_agent.run import run_query
await run_query("A CNC line drifted out of control for 30 min — what did it cost us, "
                "and draft a Slack alert for my approval.")
```

**Why it matters:** a trustworthy gage → autonomous drift detection in minutes →
**$11,970 saved per event** vs manual inspection — computed and explained by the agent,
on top of a real production platform. Reproduce: `pytest adk_agent/tests` (20 tests),
`python -m adk_agent.monitor` (no key).
"""),
]

nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
               "language_info": {"name": "python"}}
OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", encoding="utf-8") as fh:
    nbf.write(nb, fh)
print(f"wrote {OUT} ({len(cells)} cells)")
