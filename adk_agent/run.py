"""Run the Arad Quality ADK agent from the command line.

    python -m adk_agent.run "Run a sample gage study and tell me if it's acceptable"
    python -m adk_agent.run            # interactive REPL

Needs a Gemini key (GOOGLE_API_KEY or GEMINI_API_KEY) in the environment / .env.
The guardrail (refusing unsafe input) works even without a key.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from google.genai import types

logger = logging.getLogger(__name__)

from adk_agent import llm, state
from adk_agent.agents import build_root_agent

APP_NAME = state.APP_NAME
USER_ID = "local_user"

# Built once per process and reused, so memory (session state + history) is shared
# across turns and persisted in the configured store (TimescaleDB / SQLite). The
# runner is keyed by the active LLM config: if the provider/key changes on the
# Connections page, the signature changes and we rebuild the agent on the chosen
# provider — no service restart needed.
_RUNNER = None
_RUNNER_SIG: str | None = None
_BACKEND_LABEL = ""


async def _ensure_runner():
    global _RUNNER, _RUNNER_SIG, _BACKEND_LABEL
    cfg = llm.resolve()
    if _RUNNER is None or cfg.signature() != _RUNNER_SIG:
        agent = build_root_agent(llm.build_model(cfg))
        service, _BACKEND_LABEL = await state.make_session_service()
        _RUNNER = state.build_runner(agent, service, app_name=APP_NAME)
        _RUNNER_SIG = cfg.signature()
    return _RUNNER


async def run_query(query: str, *, verbose: bool = True, session_id: str | None = None,
                    user_id: str = USER_ID) -> str:
    runner = await _ensure_runner()
    session_id = session_id or os.environ.get("ARAD_SESSION_ID") or "default"
    session = await state.get_or_create_session(
        runner.session_service, user_id=user_id, session_id=session_id, app_name=APP_NAME)
    if verbose:
        print(f"  · memory: {_BACKEND_LABEL} · session '{session.id}'")
    message = types.Content(role="user", parts=[types.Part(text=query)])

    coordinator = runner.agent.name
    final_text = ""
    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=message):
        if verbose:
            for call in event.get_function_calls():
                print(f"  → tool: {call.name}({dict(call.args)})")
            author = getattr(event, "author", None)
            if author and author != coordinator and event.content and event.content.parts:
                snippet = (event.content.parts[0].text or "").strip()
                if snippet:
                    print(f"  [{author}] {snippet[:120]}")
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""
    return final_text


async def stream_query(query: str, *, session_id: str | None = None, user_id: str = USER_ID):
    """Yield the agent's answer incrementally for the AI Agent chat.

    Mirrors :func:`run_query` but uses ADK's SSE streaming so the dashboard can render
    a live "typing" answer. Yields ``(kind, text)`` tuples where ``kind`` is:

      * ``"delta"`` — an incremental text fragment (append as it arrives), and
      * ``"final"`` — the authoritative complete answer (emitted exactly once, last).

    The final answer is the same value :func:`run_query` returns, so even if a model
    or provider doesn't emit partial chunks the client still gets the full reply.
    Never raises: a model/provider failure (quota, 503, network) is caught and turned
    into a friendly final message — mirroring the old Chat page's graceful degradation.
    """
    from google.adk.agents.run_config import RunConfig, StreamingMode

    runner = await _ensure_runner()
    session_id = session_id or os.environ.get("ARAD_SESSION_ID") or "default"
    session = await state.get_or_create_session(
        runner.session_service, user_id=user_id, session_id=session_id, app_name=APP_NAME)
    message = types.Content(role="user", parts=[types.Part(text=query)])

    final_text = ""
    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=message,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            if not (event.content and event.content.parts):
                continue
            piece = event.content.parts[0].text or ""
            if not piece:
                continue
            # The last full (non-partial) response is the authoritative answer.
            if event.is_final_response():
                final_text = piece
            # Partial chunks drive the live typing effect.
            if getattr(event, "partial", False):
                yield "delta", piece
    except Exception as exc:  # quota / 503 / network — degrade gracefully, never 500
        logger.warning("stream_query failed: %s", exc)
        if not final_text:
            final_text = (
                "I couldn't reach the AI model just now — it may be busy or rate-limited. "
                "Please try again in a moment."
            )

    yield "final", final_text


async def _repl() -> None:
    print("Arad Quality agent — type a question (Ctrl+C to exit).")
    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if query:
            print(f"\n{await run_query(query)}")


def main() -> None:
    if len(sys.argv) > 1:
        print(asyncio.run(run_query(" ".join(sys.argv[1:]))))
    else:
        asyncio.run(_repl())


if __name__ == "__main__":
    main()
