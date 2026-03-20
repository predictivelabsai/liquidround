"""
Scoring Agent — scores buyer-target match across 7 synergy dimensions.
Supports: direct scoring, document-based buyer matching, research-enhanced scoring.
See agents/SKILLS.md for full capabilities.
"""
import json
from typing import Dict, Any, List, Optional

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
        doc_data = state.get("context", {}).get("document_text", "")
        research_data = state.get("context", {}).get("research_summary", "")

        prompt = f"""Analyze the following M&A opportunity and score it across 7 dimensions (0-10 each).

User Query: {context['user_query']}
Company/Target: {context.get('company_name', 'Not specified')}
Industry: {context.get('industry', 'Not specified')}

Previous Agent Results:
{json.dumps(context.get('previous_results', {}), indent=2, default=str)[:3000]}

{"Document Data:" + doc_data[:3000] if doc_data else ""}
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
        score_data = self._parse_json(response)
        score_data["composite_score"] = self._calc_composite(score_data)
        return score_data

    async def score_document_buyers(self, doc_text: str, filename: str = "") -> Dict[str, Any]:
        """
        Skill: Document-Based Buyer Matching.
        Reads a parsed document, extracts company profile, generates ideal buyer profiles,
        and scores each match across all 7 dimensions.
        """
        prompt = f"""You are an M&A advisor analyzing a company document to identify the best potential acquirers/buyers.

Document: {filename}
Content (first 4000 chars):
{doc_text[:4000]}

Based on this document, perform the following:

1. **Company Profile**: Extract the company name, sector, revenue/size, business model, geographic presence, and key strengths.

2. **Ideal Buyer Profiles**: Identify 5 likely buyer types (mix of strategic acquirers and financial sponsors/PE firms). For each buyer, explain WHY they would be interested.

3. **Buyer Scoring**: Score each buyer across 7 synergy dimensions (0-10 each):
   - revenue_synergies, cost_synergies, strategic_fit, cultural_fit, financial_health, integration_risk (10=LOW risk), market_timing

Return as JSON:
{{
    "company_profile": {{
        "name": "<extracted company name>",
        "sector": "<sector>",
        "revenue": "<if found>",
        "business_model": "<1-2 sentence summary>",
        "key_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"]
    }},
    "buyer_matches": [
        {{
            "buyer": "<buyer name or type>",
            "buyer_type": "<strategic | financial_sponsor | PE>",
            "rationale": "<why this buyer is a fit>",
            "composite_score": <0-100>,
            "dimensions": {{
                "revenue_synergies": {{"score": <0-10>, "reasoning": "<brief>"}},
                "cost_synergies": {{"score": <0-10>, "reasoning": "<brief>"}},
                "strategic_fit": {{"score": <0-10>, "reasoning": "<brief>"}},
                "cultural_fit": {{"score": <0-10>, "reasoning": "<brief>"}},
                "financial_health": {{"score": <0-10>, "reasoning": "<brief>"}},
                "integration_risk": {{"score": <0-10>, "reasoning": "<brief>"}},
                "market_timing": {{"score": <0-10>, "reasoning": "<brief>"}}
            }},
            "recommendation": "<STRONG BUY | PROCEED | CAUTIOUS | PASS>"
        }}
    ]
}}

Return ONLY valid JSON. Rank buyer_matches by composite_score descending."""

        messages = self._create_messages(prompt)
        response = await self._call_llm(messages)
        result = self._parse_json(response)

        # Recalculate composites for each buyer
        for match in result.get("buyer_matches", []):
            match["composite_score"] = self._calc_composite(match)

        # Sort by score
        result["buyer_matches"] = sorted(
            result.get("buyer_matches", []),
            key=lambda m: m.get("composite_score", 0),
            reverse=True,
        )
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _calc_composite(self, score_data: dict) -> int:
        composite = 0
        dims = score_data.get("dimensions", {})
        for dim_name, weight in DIMENSION_WEIGHTS.items():
            dim = dims.get(dim_name, {})
            s = dim.get("score", 5) if isinstance(dim, dict) else 5
            composite += s * weight * 10
        return round(composite)

    def _parse_json(self, response: str) -> dict:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            if text.startswith("json"):
                text = text[4:].strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return self._fallback_parse(response)

    def _fallback_parse(self, text: str) -> dict:
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {
            "buyer": "Unknown", "target": "Unknown", "composite_score": 50,
            "dimensions": {k: {"score": 5, "reasoning": "Unable to parse LLM response"} for k in DIMENSION_WEIGHTS},
            "recommendation": "CAUTIOUS",
            "key_risks": ["Unable to fully parse scoring response"],
            "next_steps": ["Re-run scoring with more specific query"],
        }
