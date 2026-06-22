"""Gemini adapter — uses Google Gemini for experiment commentary and prediction insights."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from agent.adapters.base import MLToolAdapter

logger = logging.getLogger(__name__)


class GeminiAdapter(MLToolAdapter):
    """Gemini-based ML adapter.

    ``log_experiment`` generates an AI narrative and returns a reference.
    ``register_model`` is a no-op (Gemini is inference-only).
    ``get_prediction`` generates a quality prediction via prompting.
    """

    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        import os
        model_name = model_name or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is not None:
            return
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model_name)

    async def log_experiment(
        self,
        experiment_name: str,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        artifacts: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> str:
        """Generate an AI commentary on the experiment run."""
        try:
            self._ensure_model()
            prompt = (
                f"Summarize this quality experiment in 2-3 sentences for a manufacturing engineer.\n"
                f"Experiment: {experiment_name}, Run: {run_name}\n"
                f"Parameters: {json.dumps(params, default=str)}\n"
                f"Metrics: {json.dumps(metrics, default=str)}\n"
            )
            response = await asyncio.to_thread(self._model.generate_content, prompt)
            text = getattr(response, "text", "")
            logger.info("Gemini: logged experiment commentary for %s/%s", experiment_name, run_name)
            return f"gemini:{run_name}:{text[:80]}"
        except Exception:
            logger.exception("Gemini log_experiment failed")
            return ""

    async def register_model(
        self,
        model_name: str,
        model_artifact: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        logger.info("Gemini adapter: register_model is a no-op (inference-only platform)")
        return "n/a"

    async def get_prediction(
        self,
        model_name: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Use Gemini to predict quality outcomes from process data."""
        try:
            self._ensure_model()
            prompt = (
                f"Given these manufacturing process measurements, predict the likely quality outcome.\n"
                f"Model context: {model_name}\n"
                f"Data: {json.dumps(input_data, default=str)}\n"
                f"Return JSON with keys: prediction, confidence, reasoning\n"
            )
            response = await asyncio.to_thread(self._model.generate_content, prompt)
            text = getattr(response, "text", "{}")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"prediction": text, "confidence": 0.5, "reasoning": "raw LLM output"}
        except Exception:
            logger.exception("Gemini get_prediction failed")
            return {"error": "prediction failed"}
