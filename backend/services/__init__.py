"""Backend service helpers.

This module exposes the stable service-level functions used by the rest of
the application. Where possible the implementation delegates to the
`spc` canonical modules. For functionality not yet ported (GRR ANOVA) we
fall back to the legacy `statisticalEngine` shim.
"""

from __future__ import annotations

from typing import Any

# GRR ANOVA currently only exists in the legacy shim — keep it available
from .statisticalEngine import calculateGRR

# Prefer canonical `spc` implementations for SPC / capability and rules
from spc import control_charts, capability as _capability, nelson_rules


def calculateProcessCapability(data: list[float], usl: float, lsl: float) -> dict[str, Any]:
	"""Wrapper around `spc.capability.capability_indices` to preserve
	the legacy dict-shaped return value expected by callers.
	"""
	result = _capability.capability_indices(data, usl, lsl)
	return {
		"cp": result.cp,
		"cpk": result.cpk,
		"sigma": result.sigma_within,
		"mean": result.mean,
		"verdict": result.verdict,
	}


def calculateXbarR(data: list[list[float]], subgroupSize: int) -> dict[str, Any]:
	"""Compute X̄-R chart limits using `spc.control_charts.xbar_r_chart` and
	return a backward-compatible dict structure.
	"""
	xbar_chart, r_chart = control_charts.xbar_r_chart(
		__import__("pandas").DataFrame(
			[ {"subgroup": i, "value": v} for i, grp in enumerate(data) for v in grp
			  ],
			columns=["subgroup", "value"],
		),
		subgroup_col="subgroup",
		value_col="value",
	)

	return {
		"xbar_ucl": xbar_chart.limits.ucl,
		"xbar_lcl": xbar_chart.limits.lcl,
		"xbar_centerline": xbar_chart.limits.cl,
		"r_ucl": r_chart.limits.ucl,
		"r_lcl": r_chart.limits.lcl,
		"r_centerline": r_chart.limits.cl,
		"sigma": xbar_chart.limits.sigma,
		"constants": {},
	}


def detectWesternElectricViolations(
	data: list[float], ucl: float, lcl: float, centerline: float, sigma: float
) -> list[dict[str, Any]]:
	"""Delegate special-cause detection to `spc.nelson_rules` and adapt the
	returned structure to the legacy caller expectation.
	"""
	import numpy as _np

	values = _np.asarray(data, dtype=float)
	results = nelson_rules.evaluate_all_rules(values, centerline, sigma)

	out: list[dict[str, Any]] = []
	for rule_key, indexes in results.items():
		if indexes:
			out.append({
				"rule": rule_key,
				"description": f"Violation for {rule_key}",
				"pointIndexes": indexes,
			})
	return out


__all__ = [
	"calculateGRR",
	"calculateProcessCapability",
	"calculateXbarR",
	"detectWesternElectricViolations",
]
