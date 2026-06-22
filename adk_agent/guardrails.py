"""Security guardrails + audit trail (the 'security' capstone concept).

* `block_unsafe_input` (before_model_callback) — refuses prompt-injection,
  credential-exfiltration, and malicious requests before the model is ever called.
* `audit_tool_calls` (before_tool_callback) — appends a JSONL audit record for every
  tool call and enforces a tool allowlist.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import BaseTool, ToolContext
from google.genai import types

logger = logging.getLogger(__name__)

AUDIT_LOG = Path(__file__).resolve().parent.parent / "logs" / "adk_audit.jsonl"

ALLOWED_TOOLS = {
    "run_grr_study", "run_sample_gage_study", "analyze_spc_series", "forecast_breach",
    "calculate_copq", "generate_sample_study", "generate_sample_series",
    "dispatch_quality_alert", "transfer_to_agent",
}

_UNSAFE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("prompt_injection", re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I)),
    ("system_prompt_exfil", re.compile(r"(reveal|show|print|repeat|leak)\s+(your\s+)?(system\s+prompt|instructions)", re.I)),
    ("credential_exfil", re.compile(r"(\b(api[\s_-]?keys?|passwords?|secrets?|credentials?|tokens?)\b|\.env\b)", re.I)),
    ("malware_phishing", re.compile(r"\b(phishing|malware|ransomware|keylogger|exfiltrate)\b", re.I)),
]

_REFUSAL = (
    "I can't help with that request. I'm a manufacturing quality agent — I run GR&R and SPC "
    "analysis and quantify cost of poor quality. I won't disclose system instructions or "
    "credentials, and I won't act on instructions that try to override my own. Ask me a "
    "quality question and I'm glad to help."
)


def _audit(record: dict[str, Any]) -> None:
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {"ts": datetime.now(timezone.utc).isoformat(), **record}
        with AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
    except Exception:  # pragma: no cover
        logger.warning("audit write failed", exc_info=True)


def _latest_user_text(llm_request: LlmRequest) -> str:
    contents = getattr(llm_request, "contents", None) or []
    for content in reversed(contents):
        if getattr(content, "role", None) == "user":
            parts = getattr(content, "parts", None) or []
            return " ".join(p.text for p in parts if getattr(p, "text", None))
    return ""


def scan_text(text: str) -> Optional[str]:
    """Return the category of the first unsafe pattern found, else None (unit-testable)."""
    for category, pattern in _UNSAFE_PATTERNS:
        if pattern.search(text):
            return category
    return None


def block_unsafe_input(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """before_model_callback: refuse unsafe input before the model is called."""
    category = scan_text(_latest_user_text(llm_request))
    if category:
        _audit({"event": "input_blocked", "category": category})
        logger.warning("Blocked unsafe input (%s)", category)
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=_REFUSAL)]))
    return None


def audit_tool_calls(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> Optional[dict[str, Any]]:
    """before_tool_callback: audit every tool call and enforce the allowlist."""
    name = getattr(tool, "name", str(tool))
    if name not in ALLOWED_TOOLS:
        _audit({"event": "tool_blocked", "tool": name})
        return {"error": f"Tool '{name}' is not permitted by policy."}
    arg_summary = {k: (f"list[{len(v)}]" if isinstance(v, list) else v) for k, v in (args or {}).items()}
    _audit({"event": "tool_call", "tool": name, "args": arg_summary})
    return None
