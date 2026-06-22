"""
Gemini API Integration for Quality Analysis

Provides LLM-powered analysis using Google's Gemini API for:
- GR&R narrative generation
- SPC interpretation
- Predictive quality insights
- Conversational quality engineering
"""

import logging
from typing import Any
import google.generativeai as genai

from core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini API
import os as _os
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
    MODEL_NAME = _os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    logger.info("Gemini API configured successfully")
else:
    logger.warning("GEMINI_API_KEY not configured. AI features will be limited.")
    MODEL_NAME = None


class GeminiAnalyzer:
    """Wrapper for Gemini API calls for quality analysis"""

    @staticmethod
    def generate_grr_narrative(
        grr_pct: float,
        ndc: int,
        repeatability: float,
        reproducibility: float,
        part_variation: float,
        equipment_id: str,
        characteristic_name: str,
    ) -> dict[str, Any]:
        """Generate AI narrative for GR&R study results"""
        if not MODEL_NAME:
            return _fallback_grr_narrative(
                grr_pct, ndc, equipment_id, characteristic_name
            )

        try:
            prompt = f"""
Analyze this GR&R study for a manufacturing quality team:

Equipment: {equipment_id}
Characteristic: {characteristic_name}
%GR&R: {grr_pct:.1f}%
NDC: {ndc}
Equipment Variation (EV): {repeatability:.6f}
Appraiser Variation (AV): {reproducibility:.6f}
Part Variation (PV): {part_variation:.6f}

Provide:
1. Summary of measurement system capability
2. Root cause analysis of any issues
3. Specific recommendations for improvement
4. Risk assessment for production use
5. Confidence level (0-100%)

Format as JSON with fields: summary, root_cause_analysis, recommendations, risk_assessment, confidence
"""

            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            
            # Parse response (assume JSON-like format)
            text = response.text
            logger.info(f"Generated GR&R narrative for {equipment_id}")
            
            return {
                "summary": _extract_section(text, "Summary"),
                "root_cause_analysis": _extract_section(text, "Root cause analysis"),
                "recommendations": _extract_section(text, "Recommendations").split("\n"),
                "risk_assessment": _extract_section(text, "Risk assessment"),
                "confidence": 85,  # Placeholder
            }
        except Exception as e:
            logger.error(f"Gemini API error in GR&R narrative: {e}")
            return _fallback_grr_narrative(
                grr_pct, ndc, equipment_id, characteristic_name
            )

    @staticmethod
    def interpret_spc_violations(
        chart_type: str,
        violated_rules: dict[str, list[int]],
        ucl: float,
        cl: float,
        lcl: float,
        recent_values: list[float],
        part_number: str = "UNKNOWN",
        characteristic_name: str = "UNKNOWN",
    ) -> dict[str, Any]:
        """Interpret SPC violations and predict causes"""
        if not MODEL_NAME:
            return _fallback_spc_interpretation(violated_rules)

        try:
            prompt = f"""
Analyze these SPC control chart violations for a manufacturing process:

Chart Type: {chart_type}
Part Number: {part_number}
Characteristic: {characteristic_name}
UCL: {ucl:.4f}, CL: {cl:.4f}, LCL: {lcl:.4f}
Recent Values: {recent_values[-10:]}
Violated Rules: {violated_rules}

Provide:
1. Pattern description of the violations
2. Manufacturing significance (why this matters)
3. List of likely causes (e.g., tool wear, temperature drift, operator change)
4. Urgency level (critical, high, medium, low)
5. Recommended actions to take

Format as JSON with fields: pattern_description, manufacturing_significance, likely_causes, urgency, recommended_actions
"""

            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            text = response.text
            
            logger.info(
                f"Generated SPC interpretation for {part_number}/{characteristic_name}"
            )
            
            return {
                "pattern_description": _extract_section(text, "Pattern description"),
                "manufacturing_significance": _extract_section(text, "Manufacturing significance"),
                "likely_causes": _extract_section(text, "Likely causes").split("\n"),
                "urgency": _extract_section(text, "Urgency level").lower(),
                "recommended_actions": _extract_section(text, "Recommended actions").split("\n"),
            }
        except Exception as e:
            logger.error(f"Gemini API error in SPC interpretation: {e}")
            return _fallback_spc_interpretation(violated_rules)

    @staticmethod
    def predict_quality_violations(
        part_number: str,
        characteristic_name: str,
        values_history: list[float],
        ucl: float,
        cl: float,
        lcl: float,
        recent_grr_pct: float = None,
    ) -> dict[str, Any]:
        """Predict future quality violations before they occur"""
        if not MODEL_NAME:
            return _fallback_prediction()

        try:
            # Simple trend analysis
            recent_trend = "increasing" if values_history[-1] > values_history[-5] else "decreasing"
            distance_to_limit = abs(ucl - values_history[-1])
            
            prompt = f"""
Predict upcoming quality violations for a manufacturing process:

Part: {part_number}
Characteristic: {characteristic_name}
Values (last 20): {values_history[-20:]}
Control Limits: UCL={ucl:.4f}, CL={cl:.4f}, LCL={lcl:.4f}
Recent GR&R: {recent_grr_pct}%
Current Trend: {recent_trend}

Provide:
1. Trend summary (direction and rate of change)
2. Predicted violation risk (percentage chance within 24 hours)
3. Time to action (when to intervene)
4. Leading indicators to watch for
5. Preventive actions recommended

Format as JSON with fields: trend_summary, predicted_violation_risk, time_to_action, leading_indicators, preventive_actions
"""

            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            text = response.text
            
            logger.info(f"Generated prediction for {part_number}/{characteristic_name}")
            
            return {
                "trend_summary": _extract_section(text, "Trend summary"),
                "predicted_violation_risk": _extract_section(text, "Predicted violation risk"),
                "time_to_action": _extract_section(text, "Time to action"),
                "leading_indicators": _extract_section(text, "Leading indicators").split("\n"),
                "preventive_actions": _extract_section(text, "Preventive actions").split("\n"),
            }
        except Exception as e:
            logger.error(f"Gemini API error in prediction: {e}")
            return _fallback_prediction()

    @staticmethod
    def chat_quality_question(
        question: str,
        context: dict[str, Any],
        conversation_history: list[dict[str, str]],
    ) -> tuple[str, list[str]]:
        """Answer quality engineering questions conversationally"""
        if not MODEL_NAME:
            return _fallback_chat_answer(question)

        try:
            # Build context injection
            context_text = _build_context_text(context)
            
            # Build conversation history
            history_text = "\n".join(
                [f"{msg['role']}: {msg['content']}" for msg in conversation_history[-10:]]
            )

            prompt = f"""
You are a quality engineering expert helping a manufacturing team.

Current System Context:
{context_text}

Conversation History:
{history_text}

User Question: {question}

Provide a helpful, specific answer based on the quality data and context.
Mention which data sources you used: context_used = [source1, source2, ...]
"""

            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            answer = response.text
            
            # Extract used sources
            context_used = [k for k in context.keys() if k != "error"]
            
            logger.info(f"Generated chat response for quality question")
            return answer, context_used

        except Exception as e:
            logger.error(f"Gemini API error in chat: {e}")
            return _fallback_chat_answer(question)


# ─── Fallback Functions ─────────────────────────────────────────────────────

def _fallback_grr_narrative(
    grr_pct: float, ndc: int, equipment_id: str, characteristic_name: str
) -> dict[str, Any]:
    """Fallback GR&R narrative when Gemini API is unavailable"""
    if grr_pct <= 10:
        verdict = "excellent"
        confidence = 95
    elif grr_pct <= 30:
        verdict = "acceptable but conditional"
        confidence = 85
    else:
        verdict = "not acceptable"
        confidence = 90

    return {
        "summary": f"{equipment_id} ({characteristic_name}) shows {verdict} measurement system capability at {grr_pct:.1f}% GR&R.",
        "root_cause_analysis": "Unable to generate AI analysis. Review measurement data for operator technique, equipment setup, and environmental factors.",
        "recommendations": [
            "Verify equipment calibration status",
            "Review operator training and technique",
            "Check environmental conditions (temperature, humidity)",
            "Consider fixture design improvements",
        ],
        "risk_assessment": "Moderate risk. Consider acceptance with monitoring." if grr_pct <= 30 else "High risk. Do not use for production.",
        "confidence": confidence,
    }


def _fallback_spc_interpretation(violated_rules: dict[str, list[int]]) -> dict[str, Any]:
    """Fallback SPC interpretation when Gemini API is unavailable"""
    rule_count = sum(len(v) for v in violated_rules.values())
    
    return {
        "pattern_description": f"Detected {rule_count} SPC rule violations indicating process out-of-control condition.",
        "manufacturing_significance": "Out-of-control process may be producing non-conforming parts.",
        "likely_causes": [
            "Tool wear or breakage",
            "Environmental condition change",
            "Operator error or change",
            "Raw material variation",
            "Equipment calibration drift",
        ],
        "urgency": "critical" if rule_count > 3 else "high",
        "recommended_actions": [
            "Stop production immediately",
            "Inspect recent parts for non-conformances",
            "Check equipment settings and calibration",
            "Review operator actions",
            "Identify and correct root cause before resuming",
        ],
    }


def _fallback_prediction() -> dict[str, Any]:
    """Fallback prediction when Gemini API is unavailable"""
    return {
        "trend_summary": "Unable to generate AI prediction. Monitor process trends manually.",
        "predicted_violation_risk": "Unknown - refer to control limits",
        "time_to_action": "Monitor continuously",
        "leading_indicators": [
            "Values approaching control limits",
            "Consistent upward or downward trend",
            "Increased variation",
        ],
        "preventive_actions": [
            "Increase sampling frequency",
            "Review process parameters",
            "Check equipment maintenance schedule",
        ],
    }


def _fallback_chat_answer(question: str) -> tuple[str, list[str]]:
    """Fallback chat answer when Gemini API is unavailable"""
    return (
        "I'm unable to process your question at this time as the AI analysis service is unavailable. "
        "Please contact your quality engineering team for assistance.",
        [],
    )


# ─── Helper Functions ───────────────────────────────────────────────────────

def _extract_section(text: str, section_name: str) -> str:
    """Extract a section from response text"""
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if section_name.lower() in line.lower():
            start = i + 1
            break
    
    if start is None:
        return ""
    
    result = []
    for line in lines[start:]:
        if line.startswith("#") or line.startswith("-"):
            break
        if line.strip():
            result.append(line.strip())
    
    return " ".join(result) or section_name


def _build_context_text(context: dict[str, Any]) -> str:
    """Build human-readable context from system data"""
    lines = []
    
    if recent_studies := context.get("recent_grr_studies"):
        lines.append(f"Recent GR&R Studies: {len(recent_studies)} studies")
        for study in recent_studies[:3]:
            lines.append(f"  - {study.get('equipment_id')}: {study.get('grr_pct', 'N/A')}%")
    
    if open_violations := context.get("open_violations"):
        lines.append(f"Open Quality Violations: {len(open_violations)} active")
        for v in open_violations[:3]:
            lines.append(f"  - {v.get('violation_type')}: {v.get('severity')}")
    
    if pending_reviews := context.get("pending_reviews"):
        lines.append(f"Pending Reviews: {len(pending_reviews)} studies awaiting approval")
    
    return "\n".join(lines) or "No specific context available"
