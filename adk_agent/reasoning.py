"""LLM reasoning for the autonomous scan.

Detection and cost are deterministic (real SPC + COPQ math). This module adds the
part where an LLM genuinely helps: a concise root-cause hypothesis and a specific
corrective action, generated live by the AI provider chosen on the Connections page
(Gemini / Claude / OpenAI, via LiteLLM). Falls back to a sensible deterministic
message if no key is configured or the model isn't reachable, so the scan never breaks.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_FALLBACK = (
    "Root-cause analysis unavailable (LLM not reachable). Based on the SPC pattern, the most "
    "likely causes are progressive tool wear, fixture slippage, or a material/lot change. "
    "Recommended action: stop the line, verify gage calibration, and inspect the tool and "
    "fixture before resuming; quarantine parts produced since the last in-control point."
)


def root_cause_analysis(
    process: str,
    spc_summary: str,
    total_copq: float = 0.0,
    savings: float = 0.0,
) -> str:
    """Return a 3-4 sentence root cause + corrective action from the active provider
    (Gemini / Claude / OpenAI), or a deterministic fallback."""
    try:
        from adk_agent import llm

        cfg = llm.resolve()
        if not cfg.configured:
            return _FALLBACK

        import litellm

        prompt = (
            "You are a senior manufacturing quality engineer. A process just went out of "
            "statistical control. Using ONLY the facts below, respond in 3-4 sentences with "
            "(1) the single most likely root cause and (2) one specific, actionable corrective "
            "step to take now. No preamble, no markdown, no headings.\n\n"
            f"Process: {process}\n"
            f"SPC finding: {spc_summary}\n"
            f"Estimated cost of this event: ${total_copq:,.0f}; "
            f"early detection saved ${savings:,.0f} versus once-per-shift inspection."
        )
        # resolve() already exported the key to the env var LiteLLM expects.
        resp = litellm.completion(
            model=llm.litellm_model(cfg),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            timeout=20,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or _FALLBACK
    except Exception as exc:  # no key / quota / network — stay graceful
        logger.warning("root_cause_analysis fell back: %s", exc)
        return _FALLBACK
