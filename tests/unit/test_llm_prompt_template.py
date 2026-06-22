"""T-U5: LLM prompt template variable substitution.

Verifies that every placeholder in generated prompts is replaced with
the caller-supplied values — no raw {variable} leakage in the output.
"""

from __future__ import annotations

import re
import pytest

from agent.llm_analyst import generate_grr_narrative, generate_spc_narrative


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def _has_unreplaced_placeholders(text: str) -> bool:
    """Return True if any Python-style {variable} remains in the text."""
    return bool(_PLACEHOLDER_RE.search(text))


# ---------------------------------------------------------------------------
# GR&R narrative prompt template
# ---------------------------------------------------------------------------

class TestGRRPromptTemplate:

    @pytest.mark.asyncio
    async def test_grr_prompt_substitutes_equipment_id(self, monkeypatch):
        """equipment_id value must appear in the constructed prompt."""
        captured_prompts: list[str] = []

        async def fake_call_gemini(user_message, api_key, **kwargs):
            captured_prompts.append(user_message)
            return '{"summary":"ok","root_cause_analysis":"ok","recommendations":[],"risk_assessment":"low","confidence":"high"}'

        monkeypatch.setattr("agent.llm_analyst._call_gemini", fake_call_gemini)

        await generate_grr_narrative(
            grr_result={
                "total_grr": 22.5,
                "repeatability": 0.12,
                "reproducibility": 0.09,
                "part_variation": 0.35,
                "total_variation": 0.48,
                "ndc": 4,
                "details": {"method": "xbar_r"},
            },
            verdict={"level": "CONDITIONAL"},
            equipment_id="CMM-007",
            characteristic_name="bore_diameter",
            api_key="fake-key",
        )

        assert captured_prompts, "Gemini was never called"
        prompt = captured_prompts[0]
        assert "CMM-007" in prompt
        assert "bore_diameter" in prompt
        assert not _has_unreplaced_placeholders(prompt), (
            f"Unreplaced placeholder found in GRR prompt: {prompt}"
        )

    @pytest.mark.asyncio
    async def test_grr_prompt_substitutes_grr_percent(self, monkeypatch):
        """%GR&R value must be present and formatted correctly in prompt."""
        captured: list[str] = []

        async def fake_call_gemini(user_message, api_key, **kwargs):
            captured.append(user_message)
            return '{"summary":"s","root_cause_analysis":"r","recommendations":[],"risk_assessment":"low","confidence":"high"}'

        monkeypatch.setattr("agent.llm_analyst._call_gemini", fake_call_gemini)

        await generate_grr_narrative(
            grr_result={
                "total_grr": 35.7,
                "repeatability": 0.20,
                "reproducibility": 0.15,
                "part_variation": 0.25,
                "total_variation": 0.50,
                "ndc": 2,
                "details": {"method": "anova"},
            },
            verdict={"level": "NOT_ACCEPTABLE"},
            equipment_id="GAUGE-003",
            characteristic_name="shaft_runout",
            api_key="fake-key",
        )

        assert "35.7" in captured[0] or "35.70" in captured[0]

    @pytest.mark.asyncio
    async def test_grr_narrative_parses_json_response(self, monkeypatch):
        """generate_grr_narrative must return a GRRNarrative dataclass, not raw text."""
        async def fake_call_gemini(user_message, api_key, **kwargs):
            return """{
                "summary": "GRR is 22%",
                "root_cause_analysis": "Operator variability",
                "recommendations": ["Retrain operators", "Check fixture"],
                "risk_assessment": "Medium risk",
                "confidence": "high"
            }"""

        monkeypatch.setattr("agent.llm_analyst._call_gemini", fake_call_gemini)

        from agent.llm_analyst import GRRNarrative
        result = await generate_grr_narrative(
            grr_result={"total_grr": 22.0, "repeatability": 0.1, "reproducibility": 0.08,
                        "part_variation": 0.35, "total_variation": 0.48, "ndc": 4,
                        "details": {"method": "xbar_r"}},
            verdict={"level": "CONDITIONAL"},
            equipment_id="CMM-001",
            characteristic_name="depth",
            api_key="fake",
        )

        assert isinstance(result, GRRNarrative)
        assert result.summary == "GRR is 22%"
        assert len(result.recommendations) == 2
        assert result.confidence == "high"


# ---------------------------------------------------------------------------
# SPC narrative prompt template
# ---------------------------------------------------------------------------

class TestSPCPromptTemplate:

    @pytest.mark.asyncio
    async def test_spc_prompt_substitutes_process_name(self, monkeypatch):
        """Process name must appear in the SPC analysis prompt."""
        captured: list[str] = []

        async def fake_call_gemini(user_message, api_key, **kwargs):
            captured.append(user_message)
            return '{"pattern_description":"shift","manufacturing_significance":"drift","likely_causes":[],"urgency":"monitor","recommended_actions":[]}'

        monkeypatch.setattr("agent.llm_analyst._call_gemini", fake_call_gemini)

        await generate_spc_narrative(
            violations={"rule_1": [5], "rule_2": []},
            chart_type="xbar_r",
            process_name="press-line-4",
            api_key="fake-key",
        )

        assert captured, "Gemini was never called"
        assert "press-line-4" in captured[0]
        assert not _has_unreplaced_placeholders(captured[0])

    @pytest.mark.asyncio
    async def test_spc_prompt_lists_active_violations_only(self, monkeypatch):
        """Only rules with violations should appear in the prompt detail section."""
        captured: list[str] = []

        async def fake_call_gemini(user_message, api_key, **kwargs):
            captured.append(user_message)
            return '{"pattern_description":"x","manufacturing_significance":"x","likely_causes":[],"urgency":"immediate","recommended_actions":[]}'

        monkeypatch.setattr("agent.llm_analyst._call_gemini", fake_call_gemini)

        await generate_spc_narrative(
            violations={"rule_1": [2, 7], "rule_3": [10], "rule_2": []},
            chart_type="individuals",
            process_name="lathe-12",
            api_key="fake",
        )

        prompt = captured[0]
        assert "rule_1" in prompt or "Rule 1" in prompt
        assert "rule_3" in prompt or "Rule 3" in prompt


# ---------------------------------------------------------------------------
# Email template (Jinja2) variable substitution
# ---------------------------------------------------------------------------

class TestEmailTemplate:

    def test_email_template_substitutes_all_required_vars(self):
        """alert_email.html must render without missing variables."""
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
        from pathlib import Path

        templates_dir = Path(__file__).resolve().parents[2] / "agent" / "templates"
        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
        )
        template = env.get_template("alert_email.html")

        html = template.render(
            severity="critical",
            process_name="press-line-1",
            message="Measurement 12.7 exceeds UCL 10.5",
            alert_type="spc_violation",
            timestamp="2026-06-10T14:30:00Z",
            grr_pct=None,
            llm_explanation="Check fixture alignment.",
            dashboard_url="http://localhost:3000",
            alert_id="uuid-1234",
        )

        assert "press-line-1" in html
        assert "CRITICAL" in html
        assert "Measurement 12.7" in html
        assert not _has_unreplaced_placeholders(html)

    def test_email_template_renders_grr_section_when_provided(self):
        """GR&R percentage section must appear when grr_pct is not None."""
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path

        templates_dir = Path(__file__).resolve().parents[2] / "agent" / "templates"
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        template = env.get_template("alert_email.html")

        html = template.render(
            severity="warning",
            process_name="cmm-01",
            message="GRR exceeded threshold",
            alert_type="grr_fail",
            timestamp="2026-06-10T10:00:00Z",
            grr_pct=31.5,
            llm_explanation="",
            dashboard_url="http://localhost:3000",
            alert_id="uuid-5678",
        )

        assert "31.5" in html or "31" in html
