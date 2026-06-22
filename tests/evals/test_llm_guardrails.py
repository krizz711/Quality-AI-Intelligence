"""
Eval: LLM guardrail behaviour — validates that:
1. _is_valid_llm_response rejects known error placeholders.
2. _parse_json_response returns a dict fallback on malformed JSON.
3. _sanitize_field strips injection characters.
4. _call_gemini returns an error placeholder when the API key is bad (mocked).
5. Prompt injection strings are sanitized before reaching Gemini.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agent.llm_analyst import (
    _is_valid_llm_response,
    _parse_json_response,
    _sanitize_field,
)


# ---------------------------------------------------------------------------
# _is_valid_llm_response
# ---------------------------------------------------------------------------

def test_valid_response_accepted():
    assert _is_valid_llm_response('{"summary": "Looks good."}') is True


def test_error_placeholder_rejected():
    assert _is_valid_llm_response("[AI analysis unavailable: HTTP 503]") is False


def test_partial_error_string_rejected():
    assert _is_valid_llm_response("[AI analysis unavailable: timeout]") is False


def test_empty_string_is_valid():
    # Empty string is not an error placeholder — caller should handle it separately
    assert _is_valid_llm_response("") is True


# ---------------------------------------------------------------------------
# _parse_json_response
# ---------------------------------------------------------------------------

def test_parse_valid_json():
    raw = '{"summary": "ok", "confidence": "high"}'
    result = _parse_json_response(raw)
    assert result["summary"] == "ok"
    assert result["confidence"] == "high"


def test_parse_json_with_surrounding_text():
    raw = 'Here is the result:\n{"summary": "ok"}\nEnd.'
    result = _parse_json_response(raw)
    assert result["summary"] == "ok"


def test_parse_invalid_json_returns_fallback():
    raw = "This is not JSON at all."
    result = _parse_json_response(raw, fallback_key="content")
    assert result == {"content": "This is not JSON at all."}


def test_parse_partial_json_returns_fallback():
    raw = '{"summary": "incomplete'
    result = _parse_json_response(raw, fallback_key="content")
    assert "content" in result


# ---------------------------------------------------------------------------
# _sanitize_field
# ---------------------------------------------------------------------------

def test_sanitize_removes_braces():
    assert "{injection}" not in _sanitize_field("equipment_{injection}")


def test_sanitize_removes_backticks():
    result = _sanitize_field("name`with`backticks")
    assert "`" not in result


def test_sanitize_removes_backslash():
    result = _sanitize_field(r"path\to\something")
    assert "\\" not in result


def test_sanitize_preserves_normal_text():
    normal = "CMM-001"
    assert _sanitize_field(normal) == normal


def test_sanitize_preserves_alphanumeric_and_dashes():
    text = "bore-diameter-v2"
    assert _sanitize_field(text) == text


# ---------------------------------------------------------------------------
# _call_gemini error handling (mocked HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_gemini_returns_placeholder_on_http_error():
    from agent.llm_analyst import _call_gemini

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "API key invalid"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=mock_response
    )

    with patch("agent.llm_analyst._call_gemini_inner", new_callable=AsyncMock) as mock_inner:
        mock_inner.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )
        result = await _call_gemini("test prompt", "bad-key")

    assert result.startswith("[AI analysis unavailable")
    assert "401" in result


@pytest.mark.asyncio
async def test_call_gemini_returns_placeholder_on_network_error():
    from agent.llm_analyst import _call_gemini

    with patch("agent.llm_analyst._call_gemini_inner", new_callable=AsyncMock) as mock_inner:
        mock_inner.side_effect = Exception("connection refused")
        result = await _call_gemini("test prompt", "any-key")

    assert result.startswith("[AI analysis unavailable")


@pytest.mark.asyncio
async def test_call_gemini_returns_text_on_success():
    from agent.llm_analyst import _call_gemini

    with patch("agent.llm_analyst._call_gemini_inner", new_callable=AsyncMock) as mock_inner:
        mock_inner.return_value = ('{"summary": "All good."}', 100, 50)
        result = await _call_gemini("test prompt", "valid-key")

    assert result == '{"summary": "All good."}'


# ---------------------------------------------------------------------------
# Prompt injection: sanitized fields don't appear raw in prompt text
# ---------------------------------------------------------------------------

def test_sanitized_equipment_id_has_no_template_chars():
    raw_id = "equip_{DROP TABLE users;}"
    sanitized = _sanitize_field(raw_id)
    assert "{" not in sanitized
    assert "}" not in sanitized
