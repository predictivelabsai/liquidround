"""
Scoring Agent — scores buyer-target match across 7 synergy dimensions.
"""
import json
from typing import Dict, Any

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from utils.state import State


DIMENSION_WEIGHTS = {
    "revenue_synergies": 0.20,
    "cost_synergies": 0.20,
    "strategic_fit": 0.15,
    "cultural_fit": 0.10,
    "financial_health": 0.15,
    "integration_risk": 0.10,
    "market_timing": 0.10,
}


class ScoringAgent(BaseAgent):
    """Scores buyer-target matches across synergy dimensions (0-10 each, 0-100 composite)."""

    def __init__(self):
        super().__init__("scoring", prompt_file="scoring.md")

    async def _execute_logic(self, state: State) -> Dict[str, Any]:
        context = self._extract_context_from_state(state)

        # Include document data if available
        doc_data = state.get("context", {}).get("document_text", "")
        research_data = state.get("context", {}).get("research_summary", "")

        prompt = f"""Analyze the following M&A opportunity and score it across 7 dimensions (0-10 each).

User Query: {context['user_query']}
Company/Target: {context.get('company_name', 'Not specified')}
Industry: {context.get('industry', 'Not specified')}

Previous Agent Results:
{json.dumps(context.get('previous_results', {}), indent=2, default=str)[:3000]}

{"Document Data:" + doc_data[:2000] if doc_data else ""}
{"Research Data:" + research_data[:2000] if research_data else ""}

Return your analysis as a JSON object with this exact structure:
{{
    "buyer": "<buyer company or criteria>",
    "target": "<target company>",
    "composite_score": <0-100>,
    "dimensions": {{
        "revenue_synergies": {{"score": <0-10>, "reasoning": "<specific reasoning>"}},
        "cost_synergies": {{"score": <0-10>, "reasoning": "<specific reasoning>"}},
        "strategic_fit": {{"score": <0-10>, "reasoning": "<specific reasoning>"}},
        "cultural_fit": {{"score": <0-10>, "reasoning": "<specific reasoning>"}},
        "financial_health": {{"score": <0-10>, "reasoning": "<specific reasoning>"}},
        "integration_risk": {{"score": <0-10>, "reasoning": "<inverted — 10 means LOW risk>"}},
        "market_timing": {{"score": <0-10>, "reasoning": "<specific reasoning>"}}
    }},
    "recommendation": "<STRONG BUY | PROCEED | CAUTIOUS | PASS>",
    "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
    "next_steps": ["<step 1>", "<step 2>", "<step 3>"]
}}

IMPORTANT: Return ONLY the JSON object, no markdown fences or extra text."""

        messages = self._create_messages(prompt, context)
        response = await self._call_llm(messages)

        # Parse JSON from response
        try:
            # Strip markdown fences if present
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            if text.startswith("json"):
                text = text[4:].strip()
            score_data = json.loads(text)
        except json.JSONDecodeError:
            # Fallback: extract JSON from response
            score_data = self._fallback_parse(response)

        # Recalculate composite score from weights
        composite = 0
        dims = score_data.get("dimensions", {})
        for dim_name, weight in DIMENSION_WEIGHTS.items():
            dim = dims.get(dim_name, {})
            s = dim.get("score", 5) if isinstance(dim, dict) else 5
            composite += s * weight * 10
        score_data["composite_score"] = round(composite)

        return score_data

    def _fallback_parse(self, text: str) -> dict:
        """Attempt to extract JSON from LLM response that may have extra text."""
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {
            "buyer": "Unknown",
            "target": "Unknown",
            "composite_score": 50,
            "dimensions": {k: {"score": 5, "reasoning": "Unable to parse LLM response"} for k in DIMENSION_WEIGHTS},
            "recommendation": "CAUTIOUS",
            "key_risks": ["Unable to fully parse scoring response"],
            "next_steps": ["Re-run scoring with more specific query"],
        }
