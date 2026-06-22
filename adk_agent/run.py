"""Run the Arad Quality ADK agent from the command line.

    python -m adk_agent.run "Run a sample gage study and tell me if it's acceptable"
    python -m adk_agent.run            # interactive REPL

Needs a Gemini key (GOOGLE_API_KEY or GEMINI_API_KEY) in the environment / .env.
The guardrail (refusing unsafe input) works even without a key.
"""

from __future__ import annotations

import asyncio
import os
import sys

from google.genai import types

from adk_agent import state
from adk_agent.agents import root_agent

APP_NAME = state.APP_NAME
USER_ID = "local_user"

# Built once per process and reused, so memory (session state + history) is shared
# across turns and persisted in the configured store (TimescaleDB / SQLite).
_RUNNER = None
_BACKEND_LABEL = ""


async def _ensure_runner():
    global _RUNNER, _BACKEND_LABEL
    if _RUNNER is None:
        service, _BACKEND_LABEL = await state.make_session_service()
        _RUNNER = state.build_runner(root_agent, service, app_name=APP_NAME)
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

    final_text = ""
    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=message):
        if verbose:
            for call in event.get_function_calls():
                print(f"  → tool: {call.name}({dict(call.args)})")
            author = getattr(event, "author", None)
            if author and author != root_agent.name and event.content and event.content.parts:
                snippet = (event.content.parts[0].text or "").strip()
                if snippet:
                    print(f"  [{author}] {snippet[:120]}")
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""
    return final_text


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
