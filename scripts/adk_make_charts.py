"""Generate figures for the ADK capstone notebook/README (notebook/).

    .venv-adk/Scripts/python scripts/adk_make_charts.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from adk_agent import skills

OUT = pathlib.Path(__file__).resolve().parent.parent / "notebook"
OUT.mkdir(exist_ok=True)
ACCENT, RED, GREEN = "#4e8cff", "#ef4444", "#22c55e"


def spc_chart() -> pathlib.Path:
    values = skills.generate_sample_series(scenario="shift", n=40, seed=11)["values"]
    rep = skills.analyze_spc_series(values)
    cl = rep["control_limits"]
    viol = {v["index"] for v in rep["violations"]}
    x = list(range(len(values)))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(x, values, "-", color=ACCENT, lw=1.5)
    ax.scatter([i for i in x if i not in viol], [values[i] for i in x if i not in viol], color=ACCENT, s=26)
    ax.scatter([i for i in x if i in viol], [values[i] for i in x if i in viol], color=RED, s=60,
               label="Nelson-rule violation", edgecolor="white", linewidth=0.6, zorder=4)
    ax.axhline(cl["ucl"], color=RED, ls="--", lw=1, label=f"UCL {cl['ucl']:.2f}")
    ax.axhline(cl["center_line"], color=GREEN, lw=1, label=f"CL {cl['center_line']:.2f}")
    ax.axhline(cl["lcl"], color=RED, ls="--", lw=1, label=f"LCL {cl['lcl']:.2f}")
    ax.set_title("SPC Individuals Chart — autonomous Nelson-rule detection", fontweight="bold")
    ax.set_xlabel("sample"); ax.set_ylabel("bore diameter")
    ax.legend(loc="upper left", fontsize=8); ax.grid(alpha=0.15)
    fig.tight_layout()
    path = OUT / "spc_control_chart.png"
    fig.savefig(path, dpi=130); plt.close(fig)
    return path


def copq_chart() -> pathlib.Path:
    c = skills.calculate_copq(units_per_hour=120, hours_out_of_control=0.5, baseline_defect_rate=0.01,
                              out_of_control_defect_rate=0.15, scrap_cost_per_unit=45,
                              escape_rate=0.10, escape_cost_per_unit=500, events_per_year=12)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(["Autonomous\n(~30 min)", "Manual\n(shift end)"],
                  [c["total_copq"], c["cost_if_caught_late"]], color=[GREEN, RED], width=0.55)
    for b, v in zip(bars, [c["total_copq"], c["cost_if_caught_late"]]):
        ax.text(b.get_x() + b.get_width() / 2, v, f"${v:,.0f}", ha="center", va="bottom", fontweight="bold")
    ax.set_title("Cost of Poor Quality per event", fontweight="bold"); ax.set_ylabel("USD lost")
    ax.annotate(f"Early detection saves ${c['savings_from_early_detection']:,.0f}/event\n"
                f"(${c['annualized_copq']:,.0f}/yr)", xy=(0, c["total_copq"]), xytext=(0.5, c["cost_if_caught_late"] * 0.6),
                ha="center", fontsize=10, bbox=dict(boxstyle="round", fc="#dff5e6", ec=GREEN))
    ax.grid(axis="y", alpha=0.15); fig.tight_layout()
    path = OUT / "copq_comparison.png"
    fig.savefig(path, dpi=130); plt.close(fig)
    return path


if __name__ == "__main__":
    print("wrote", spc_chart())
    print("wrote", copq_chart())
