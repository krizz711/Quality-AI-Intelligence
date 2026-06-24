"""Resolve the active AI provider + key for the ADK agent layer.

The AI Agent page must use the provider and key configured once on the platform's
**Connections page** (encrypted in the DB) — the same place every other integration
is set up — instead of a separately hand-edited ``.env``. Because the agent runs in
its own process, it fetches that config from the platform backend (see
:func:`adk_agent.backend_client.get_llm_config`) and falls back to environment
variables for standalone runs.

Provider routing:
  * **Gemini** is called natively by ADK — the model is a plain string and the SDK
    reads ``GOOGLE_API_KEY`` from the environment.
  * **Claude / OpenAI** go through ADK's ``LiteLlm`` wrapper, which reads
    ``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` from the environment.

So :func:`resolve` also exports the key it found into the environment under the name
the relevant SDK expects.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Per-provider model defaults (override via env). Gemini is decoupled from the
# platform's GEMINI_MODEL via ADK_GEMINI_MODEL — flash-lite is flaky at the
# multi-agent synthesis this layer does. Claude/OpenAI defaults mirror the platform's
# AI-summaries service (backend/services/gemini_service.py) for consistency.
_DEFAULT_MODELS = {
    "gemini": os.environ.get("ADK_GEMINI_MODEL") or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash",
    "claude": os.environ.get("ANTHROPIC_MODEL") or "claude-opus-4-8",
    "openai": os.environ.get("OPENAI_MODEL") or "gpt-4o-mini",
}

# LiteLLM provider prefixes for the non-native providers.
_LITELLM_PREFIX = {"gemini": "gemini", "claude": "anthropic", "openai": "openai"}

_ALIASES = {"anthropic": "claude", "gpt": "openai", "google": "gemini"}


@dataclass(frozen=True)
class LlmConfig:
    provider: str   # "gemini" | "claude" | "openai"
    api_key: str
    model: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def signature(self) -> str:
        """Stable id of the active config so the runner can rebuild when it changes.
        Uses only the key's last 6 chars — never the full secret (this is logged)."""
        tail = self.api_key[-6:] if self.api_key else ""
        return f"{self.provider}:{self.model}:{tail}"


def _normalize(provider: str | None) -> str:
    p = (provider or "gemini").strip().lower()
    return _ALIASES.get(p, p)


def _from_backend() -> tuple[str, str] | None:
    """(provider, key) from the platform's Connections settings, or None."""
    try:
        from adk_agent import backend_client

        cfg = backend_client.get_llm_config()
    except Exception as exc:  # import or network — fall back to env
        logger.info("LLM config from backend unavailable (%s); using env", exc)
        return None
    if cfg and cfg.get("api_key"):
        return _normalize(cfg.get("provider")), cfg["api_key"]
    return None


def _from_env() -> tuple[str, str]:
    """(provider, key) from environment variables — the standalone fallback."""
    provider = _normalize(os.environ.get("LLM_PROVIDER"))
    if provider == "claude":
        return "claude", os.environ.get("ANTHROPIC_API_KEY", "")
    if provider == "openai":
        return "openai", os.environ.get("OPENAI_API_KEY", "")
    return "gemini", os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")


def resolve() -> LlmConfig:
    """Active provider + key + model. Connections (backend) first, then env.

    Also exports the key into the environment under the variable the matching SDK
    reads, so ADK's native Gemini path and LiteLlm's Claude/OpenAI paths both pick it
    up without further wiring.
    """
    provider, key = _from_backend() or _from_env()
    if provider not in _DEFAULT_MODELS:
        provider = "gemini"
    if key:
        if provider == "gemini":
            os.environ["GEMINI_API_KEY"] = key
            os.environ["GOOGLE_API_KEY"] = key  # ADK's native genai path reads this
        elif provider == "claude":
            os.environ["ANTHROPIC_API_KEY"] = key
        elif provider == "openai":
            os.environ["OPENAI_API_KEY"] = key
    return LlmConfig(provider=provider, api_key=key, model=_DEFAULT_MODELS[provider])


def build_model(cfg: LlmConfig | None = None):
    """Return the value for an ADK ``Agent(model=...)``.

    A plain model-name string for Gemini (native), or a ``LiteLlm`` wrapper for
    Claude / OpenAI.
    """
    cfg = cfg or resolve()
    if cfg.provider == "gemini":
        return cfg.model
    from google.adk.models.lite_llm import LiteLlm

    return LiteLlm(model=f"{_LITELLM_PREFIX[cfg.provider]}/{cfg.model}")


def litellm_model(cfg: LlmConfig | None = None) -> str:
    """Provider-prefixed model id for a direct ``litellm.completion`` call (used by
    :mod:`adk_agent.reasoning` for the one-shot root-cause text)."""
    cfg = cfg or resolve()
    return f"{_LITELLM_PREFIX[cfg.provider]}/{cfg.model}"
