"""
Eval: Token tracking — validates that:
1. _record_token_usage increments Prometheus counters correctly.
2. _call_gemini passes use_case to _record_token_usage.
3. Token counts of 0 are not recorded (avoids polluting metrics).
"""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# _record_token_usage directly
# ---------------------------------------------------------------------------

def test_record_token_usage_increments_counter():
    from agent.llm_analyst import _record_token_usage, _prometheus_available

    if not _prometheus_available:
        pytest.skip("prometheus_client not available")

    with patch("agent.llm_analyst._llm_tokens_total") as mock_counter:
        mock_labels = MagicMock()
        mock_counter.labels.return_value = mock_labels

        from agent.llm_analyst import _record_token_usage
        _record_token_usage("grr_narrative", 250, 120)

        # Should be called twice: once for input, once for output
        assert mock_counter.labels.call_count == 2
        calls = mock_counter.labels.call_args_list
        directions = {c.kwargs.get("direction") or c.args[-1] for c in calls}
        assert "input" in directions
        assert "output" in directions


def test_record_token_usage_skips_zero_counts():
    from agent.llm_analyst import _record_token_usage, _prometheus_available

    if not _prometheus_available:
        pytest.skip("prometheus_client not available")

    with patch("agent.llm_analyst._llm_tokens_total") as mock_counter:
        _record_token_usage("grr_narrative", 0, 0)
        mock_counter.labels.assert_not_called()


def test_record_token_usage_never_raises():
    from agent.llm_analyst import _record_token_usage, _prometheus_available

    if not _prometheus_available:
        pytest.skip("prometheus_client not available")

    with patch("agent.llm_analyst._llm_tokens_total") as mock_counter:
        mock_counter.labels.side_effect = RuntimeError("counter broken")
        # Must not raise — token tracking is best-effort
        _record_token_usage("chat", 100, 50)


# ---------------------------------------------------------------------------
# _call_gemini passes use_case tag
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_gemini_records_tokens_with_correct_use_case():
    from agent.llm_analyst import _call_gemini

    with patch("agent.llm_analyst._call_gemini_inner", new_callable=AsyncMock) as mock_inner, \
         patch("agent.llm_analyst._record_token_usage") as mock_record:

        mock_inner.return_value = ('{"summary": "ok"}', 300, 150)

        await _call_gemini("prompt text", "valid-key", use_case="grr_narrative")

        mock_record.assert_called_once_with("grr_narrative", 300, 150)


@pytest.mark.asyncio
async def test_call_gemini_default_use_case_is_general():
    from agent.llm_analyst import _call_gemini

    with patch("agent.llm_analyst._call_gemini_inner", new_callable=AsyncMock) as mock_inner, \
         patch("agent.llm_analyst._record_token_usage") as mock_record:

        mock_inner.return_value = ("response text", 100, 50)

        await _call_gemini("prompt", "key")

        mock_record.assert_called_once_with("general", 100, 50)


@pytest.mark.asyncio
async def test_call_gemini_does_not_record_on_failure():
    from agent.llm_analyst import _call_gemini
    import httpx

    with patch("agent.llm_analyst._call_gemini_inner", new_callable=AsyncMock) as mock_inner, \
         patch("agent.llm_analyst._record_token_usage") as mock_record:

        mock_inner.side_effect = Exception("network error")

        result = await _call_gemini("prompt", "key")

        mock_record.assert_not_called()
        assert result.startswith("[AI analysis unavailable")
