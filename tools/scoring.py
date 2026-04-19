"""Match scoring tool — wraps the existing scoring_agent logic.

Emits a radar-style score artifact with 7 synergy dimensions.

Consumed by:
  - match_scorer (capital)
  - synergy_analyst (underwriting, secondary)
"""
from __future__ import annotations

import json
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from tools.artifact import emit


class ScoreArgs(BaseModel):
    buyer: str = Field(description="Buyer / acquirer name.")
    target: str = Field(description="Target company name.")
    buyer_profile: Optional[str] = Field(default="", description="Optional buyer context (sector, size, strategy).")
    target_profile: Optional[str] = Field(default="", description="Optional target context (sector, size, financials).")


def _score_match(buyer: str, target: str, buyer_profile: str = "", target_profile: str = "") -> str:
    """Invoke the legacy ScoringAgent to produce a 7-dimension match score.

    We call the existing LLM-backed scorer so we don't duplicate the prompt
    logic; it already returns a composite score + recommendation.
    """
    import asyncio
    from agents.scoring_agent import ScoringAgent
    from utils.state import create_initial_state, update_deal_info

    agent = ScoringAgent()
    query = (
        f"Score the M&A match between buyer={buyer!r} and target={target!r}. "
        f"Buyer profile: {buyer_profile or 'n/a'}. "
        f"Target profile: {target_profile or 'n/a'}. "
        "Return strict JSON with composite_score, recommendation, rationale, and dimensions (all 7)."
    )
    state = create_initial_state(user_query=query, mode="buyer_ma")
    state = update_deal_info(state, deal_type="buyer_ma", company_name=target, industry="")

    try:
        final_state = asyncio.run(agent.execute(state))
    except Exception as e:  # noqa: BLE001
        return f"Scoring failed: {e}"

    result = final_state.get("agent_results", {}).get("scoring", {}).get("result") or {}
    if not result:
        return "Scoring produced no result."

    dims = result.get("dimensions", {}) or {}
    rows = []
    for k in [
        "revenue_synergies", "cost_synergies", "strategic_fit", "cultural_fit",
        "financial_health", "integration_risk", "market_timing",
    ]:
        d = dims.get(k, {})
        score = d.get("score") if isinstance(d, dict) else d
        rows.append({
            "dimension": k.replace("_", " ").title(),
            "score_0_10": score if score is not None else "—",
            "rationale": (d.get("rationale", "") if isinstance(d, dict) else "")[:180],
        })

    composite = result.get("composite_score", "")
    rec = result.get("recommendation", "")
    subtitle = f"Composite {composite} · {rec}"

    return emit(
        kind="table",
        title=f"Match score — {buyer} + {target}",
        subtitle=subtitle,
        columns=["dimension", "score_0_10", "rationale"],
        rows=rows,
        summary={
            "buyer": buyer,
            "target": target,
            "composite_score": composite,
            "recommendation": rec,
            "overall_rationale": result.get("rationale", ""),
        },
    )


score_match = StructuredTool.from_function(
    func=_score_match,
    name="score_match",
    description="Score a specific buyer + target M&A match across 7 synergy dimensions. Returns a table artifact with per-dimension scores and an overall recommendation (STRONG BUY | PROCEED | CAUTIOUS | PASS).",
    args_schema=ScoreArgs,
)
