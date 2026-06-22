"""Gemini service helpers for quality analysis.

This module provides async-compatible Gemini wrappers for GR&R analysis,
SPC anomaly analysis, and full quality report generation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any, Callable, TypeVar

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Lazy-initialized Gemini models. Do not crash on import when GEMINI_API_KEY is
# absent — initialize at call time to allow running the API without AI keys.
_models: dict[str, Any] = {}
_configured = False
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# Quota and availability differ per model; walk this chain before giving up.
_MODEL_CHAIN = [MODEL_NAME, "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-flash-latest"]

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


class AIGenerationError(RuntimeError):
    """All Gemini models failed; callers should fall back to deterministic text."""


def _ensure_configured() -> None:
    """Configure the Gemini SDK. Raises ValueError if the API key is missing."""
    global _configured
    if _configured:
        return
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set; Gemini calls are disabled")
    genai.configure(api_key=api_key)
    _configured = True


def _get_model(name: str):
    model = _models.get(name)
    if model is None:
        model = genai.GenerativeModel(name)
        _models[name] = model
    return model

_T = TypeVar("_T")


def _data_to_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def _build_prompt(task_name: str, payload: dict[str, Any], instructions: str) -> str:
    return (
        f"You are a manufacturing quality analysis assistant.\n\n"
        f"Task: {task_name}\n\n"
        f"Instructions:\n{instructions}\n\n"
        f"Input data (JSON):\n{_data_to_json(payload)}\n"
    )


# Hard cap per Gemini call. When the key is over its free-tier quota the SDK retries
# with long internal backoff, which used to block API requests (slow SPC charts, slow
# alerts). Abandoning the call after a few seconds lets the deterministic fallback run.
_GEMINI_CALL_TIMEOUT_S = 8.0


async def _generate_gemini(prompt: str) -> str:
    """Call Gemini in a background thread, walking the model chain on failure."""

    _ensure_model()

    last_exc: Exception | None = None
    seen: set[str] = set()
    for name in _MODEL_CHAIN:
        if not name or name in seen:
            continue
        seen.add(name)
        logger.info("Calling Gemini model %s", name)
        try:
            model = _get_model(name)
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=_GEMINI_CALL_TIMEOUT_S,
            )
            text = getattr(response, "text", None)
            if text:
                return text
            last_exc = RuntimeError(f"Gemini model {name} returned an empty response")
        except asyncio.TimeoutError as exc:
            # A timeout almost always means the shared free-tier quota is exhausted and
            # the SDK is backing off — the other models would hit the same wall. Stop
            # walking the chain and fall back fast instead of stacking timeouts.
            logger.warning("Gemini model %s timed out after %ss; abandoning chain", name, _GEMINI_CALL_TIMEOUT_S)
            last_exc = exc
            break
        except Exception as exc:  # quota, availability, network — try the next model
            logger.warning("Gemini model %s failed: %s", name, exc)
            last_exc = exc

    logger.error("All Gemini models failed; falling back to deterministic analysis")
    raise AIGenerationError(str(last_exc) if last_exc else "unknown Gemini failure")


# ── Provider routing ──────────────────────────────────────────────────────────
# AI summaries can come from Gemini (default), Anthropic Claude, or OpenAI. The
# active provider is chosen in Connections → "AI summaries" and applied to the
# environment by core.settings_store. All providers share one hard timeout so a
# slow or over-quota key degrades to the deterministic fallback instead of hanging.
_LLM_CALL_TIMEOUT_S = 8.0
_ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _active_provider() -> str:
    return (os.environ.get("LLM_PROVIDER") or "gemini").strip().lower()


async def _generate_claude(prompt: str) -> str:
    """Generate text with the Anthropic Claude API (provider == 'claude')."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIGenerationError("ANTHROPIC_API_KEY is not set; Claude calls are disabled")
    try:
        from anthropic import AsyncAnthropic
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise AIGenerationError("anthropic SDK is not installed") from exc

    client = AsyncAnthropic(api_key=api_key)
    try:
        message = await asyncio.wait_for(
            client.messages.create(
                model=_ANTHROPIC_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=_LLM_CALL_TIMEOUT_S,
        )
    except asyncio.TimeoutError as exc:
        raise AIGenerationError(f"Claude call timed out after {_LLM_CALL_TIMEOUT_S}s") from exc
    except Exception as exc:  # quota, auth, network
        raise AIGenerationError(f"Claude call failed: {exc}") from exc

    text = "".join(
        getattr(block, "text", "")
        for block in message.content
        if getattr(block, "type", "") == "text"
    )
    if not text.strip():
        raise AIGenerationError("Claude returned an empty response")
    return text


async def _generate_openai(prompt: str) -> str:
    """Generate text with the OpenAI API (provider == 'openai')."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise AIGenerationError("OPENAI_API_KEY is not set; OpenAI calls are disabled")
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise AIGenerationError("openai SDK is not installed") from exc

    client = AsyncOpenAI(api_key=api_key)
    try:
        completion = await asyncio.wait_for(
            client.chat.completions.create(
                model=_OPENAI_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=_LLM_CALL_TIMEOUT_S,
        )
    except asyncio.TimeoutError as exc:
        raise AIGenerationError(f"OpenAI call timed out after {_LLM_CALL_TIMEOUT_S}s") from exc
    except Exception as exc:  # quota, auth, network
        raise AIGenerationError(f"OpenAI call failed: {exc}") from exc

    text = completion.choices[0].message.content if completion.choices else ""
    if not (text or "").strip():
        raise AIGenerationError("OpenAI returned an empty response")
    return text


async def _generate_text(prompt: str) -> str:
    """Route a prompt to the configured AI provider (Gemini by default)."""
    provider = _active_provider()
    if provider in ("claude", "anthropic"):
        return await _generate_claude(prompt)
    if provider in ("openai", "gpt"):
        return await _generate_openai(prompt)
    return await _generate_gemini(prompt)


def _ensure_model() -> None:
    """Backwards-compatible alias kept for tests; configures the SDK."""
    _ensure_configured()


def _grr_fallback_summary(data: dict[str, Any]) -> str:
    """Deterministic AIAG-style GR&R interpretation used when Gemini is unavailable."""
    grr = data.get("grr_percent")
    ndc = data.get("ndc") or data.get("number_of_distinct_categories")
    ev = data.get("repeatability")
    av = data.get("reproducibility")

    lines = ["**Automated statistical review** (AI commentary temporarily unavailable)", ""]

    if isinstance(grr, (int, float)):
        if grr < 10:
            lines.append(
                f"Total GR&R of {grr:.1f}% is **acceptable** (AIAG: below 10%). The measurement "
                "system contributes a small share of variation and may be released for use."
            )
        elif grr <= 30:
            lines.append(
                f"Total GR&R of {grr:.1f}% is **conditional** (AIAG: 10–30%). Approve only for "
                "non-critical characteristics; schedule improvement actions and re-study."
            )
        else:
            lines.append(
                f"Total GR&R of {grr:.1f}% is **unacceptable** (AIAG: above 30%). Do not use this "
                "measurement system for product acceptance until it is repaired and re-qualified."
            )

    if isinstance(ev, (int, float)) and isinstance(av, (int, float)) and (ev or av):
        if ev >= av:
            lines.append(
                f"Repeatability (EV {ev:.4g}) dominates reproducibility (AV {av:.4g}): focus on "
                "the gauge — wear, fixturing rigidity, resolution, and measurement procedure."
            )
        else:
            lines.append(
                f"Reproducibility (AV {av:.4g}) dominates repeatability (EV {ev:.4g}): focus on "
                "operator technique — alignment, handling, and training consistency."
            )

    if isinstance(ndc, (int, float)):
        if ndc >= 5:
            lines.append(
                f"Number of distinct categories is {ndc:.0f} (≥ 5), adequate to distinguish parts."
            )
        else:
            lines.append(
                f"Number of distinct categories is {ndc:.0f}, below the minimum of 5 — the system "
                "cannot reliably discriminate between parts at this variation level."
            )

    return "\n\n".join(lines)


async def analyze_grr(measurement_data: dict[str, Any]) -> str:
    """Analyze GR&R measurement data and return Gemini output text."""

    prompt = _build_prompt(
        "GR&R analysis",
        measurement_data,
        """
Analyze the GR&R measurement study in detail.
Focus on repeatability, reproducibility, part variation, total variation,
ndc, acceptance implications, and practical recommendations.
Return a concise but detailed manufacturing-quality explanation.
""".strip(),
    )
    try:
        return await _generate_text(prompt)
    except AIGenerationError:
        return _grr_fallback_summary(measurement_data)


async def analyzeGRR(measurement_data: dict[str, Any]) -> str:
    """CamelCase alias for analyze_grr."""

    return await analyze_grr(measurement_data)


def _spc_fallback_summary(data: dict[str, Any]) -> str:
    """Deterministic SPC interpretation used when Gemini is unavailable."""
    violations = data.get("violations") or data.get("violated_rules") or []
    ucl = data.get("ucl")
    lcl = data.get("lcl")
    mean = data.get("mean") or data.get("cl")

    lines = ["**Automated statistical review** (AI commentary temporarily unavailable)", ""]

    count = len(violations) if isinstance(violations, (list, dict)) else 0
    if count:
        lines.append(
            f"{count} control-rule violation{'s' if count != 1 else ''} detected. Treat these "
            "points as potential special-cause variation: quarantine affected output, review "
            "process inputs (tooling, material lot, setup) near the flagged samples, and document."
        )
    else:
        lines.append(
            "No control-rule violations detected in the submitted window. The process appears "
            "statistically stable; continue monitoring at the current sampling cadence."
        )

    if (
        isinstance(mean, (int, float))
        and isinstance(ucl, (int, float))
        and isinstance(lcl, (int, float))
    ):
        lines.append(f"Center line {mean:.4g} with control limits [{lcl:.4g}, {ucl:.4g}] (±3σ).")

    return "\n\n".join(lines)


async def analyze_spc_anomaly(chart_data: dict[str, Any]) -> str:
    """Analyze SPC anomaly data and return Gemini output text."""

    prompt = _build_prompt(
        "SPC anomaly analysis",
        chart_data,
        """
Analyze the SPC chart data for anomalies, control-limit violations,
Nelson rule patterns, process drift, special causes, and suggested actions.
Return a detailed explanation for a manufacturing quality engineer.
""".strip(),
    )
    try:
        return await _generate_text(prompt)
    except AIGenerationError:
        return _spc_fallback_summary(chart_data)


async def analyzeSPCAnomaly(chart_data: dict[str, Any]) -> str:
    """CamelCase alias for analyze_spc_anomaly."""

    return await analyze_spc_anomaly(chart_data)


async def generate_quality_report(all_data: dict[str, Any]) -> str:
    """Generate a combined quality report and return Gemini output text."""

    prompt = _build_prompt(
        "quality report generation",
        all_data,
        """
Create a detailed quality report covering GR&R results, SPC findings,
trend observations, risks, and recommended next steps.
Structure the response clearly and make it suitable for a quality review.
""".strip(),
    )
    try:
        return await _generate_text(prompt)
    except AIGenerationError:
        return (
            "**Automated summary** (AI commentary temporarily unavailable)\n\n"
            "Statistical results in this report were computed and validated locally. "
            "Narrative interpretation could not be generated — retry later for the full AI review."
        )


async def generateQualityReport(all_data: dict[str, Any]) -> str:
    """CamelCase alias for generate_quality_report."""

    return await generate_quality_report(all_data)


def analyze_grr_sync(measurement_data: dict[str, Any]) -> str:
    """Synchronous wrapper for analyze_grr."""

    return asyncio.run(analyze_grr(measurement_data))


def analyzeGRR_sync(measurement_data: dict[str, Any]) -> str:
    """CamelCase alias for analyze_grr_sync."""

    return analyze_grr_sync(measurement_data)


def analyze_spc_anomaly_sync(chart_data: dict[str, Any]) -> str:
    """Synchronous wrapper for analyze_spc_anomaly."""

    return asyncio.run(analyze_spc_anomaly(chart_data))


def analyzeSPCAnomaly_sync(chart_data: dict[str, Any]) -> str:
    """CamelCase alias for analyze_spc_anomaly_sync."""

    return analyze_spc_anomaly_sync(chart_data)


def generate_quality_report_sync(all_data: dict[str, Any]) -> str:
    """Synchronous wrapper for generate_quality_report."""

    return asyncio.run(generate_quality_report(all_data))


def generateQualityReport_sync(all_data: dict[str, Any]) -> str:
    """CamelCase alias for generate_quality_report_sync."""

    return generate_quality_report_sync(all_data)


if __name__ == "__main__":
    sample_mode = sys.argv[1] if len(sys.argv) > 1 else "report"

    sample_grr = {
        "equipment_id": "CMM-001",
        "characteristic_name": "bore_diameter",
        "grr_percent": 18.4,
        "ndc": 7,
        "repeatability": 0.12,
        "reproducibility": 0.08,
        "part_variation": 1.95,
        "measurements": [
            {"part": "P1", "operator": "A", "value": 10.01},
            {"part": "P1", "operator": "B", "value": 10.03},
        ],
    }
    sample_spc = {
        "chart_type": "i_mr",
        "ucl": 10.5,
        "cl": 10.0,
        "lcl": 9.5,
        "recent_values": [9.9, 10.0, 10.1, 10.3, 10.4, 10.45],
        "violated_rules": {"rule_1": [5], "rule_2": []},
    }
    sample_report = {
        "grr": sample_grr,
        "spc": sample_spc,
        "summary": {"shift": "A", "line": "Line 3", "status": "review"},
    }

    if sample_mode == "grr":
        result = analyze_grr_sync(sample_grr)
    elif sample_mode == "spc":
        result = analyze_spc_anomaly_sync(sample_spc)
    else:
        result = generate_quality_report_sync(sample_report)

    print(result)
