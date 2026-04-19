"""Research tools — wrap utils/research_tools as sync StructuredTools.

EXA = semantic search. TAVILY = web search with citations.

Consumed by:
  - research_analyst (portfolio)
  - deal_triage, seller_intent (sourcing)
  - integration_planner (portfolio)
  - ESG / legal reviewers for news / disclosure context
"""
from __future__ import annotations

import asyncio
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from utils.research_tools import research_tools
from tools.artifact import emit


class QueryArgs(BaseModel):
    query: str = Field(description="A focused research question or topic to search.")
    num_results: int = Field(default=8, ge=1, le=20)


def _exa_search(query: str, num_results: int = 8) -> str:
    res = asyncio.run(research_tools.exa_search(query, num_results=num_results))
    if res.get("error"):
        return f"EXA error: {res['error']}"
    items = [{
        "title": r.get("title") or "",
        "url": r.get("url") or "",
        "doc_type": "exa",
        "snippet": (r.get("snippet") or "")[:300],
        "score": round(float(r.get("score") or 0), 3),
    } for r in res.get("results", [])]
    if not items:
        return "No EXA results."
    return emit(
        kind="citations",
        title=f"EXA — {query}",
        subtitle=f"{len(items)} semantic matches",
        items=items,
    )


exa_search = StructuredTool.from_function(
    func=_exa_search,
    name="exa_search",
    description="Semantic web search via EXA. Use for deep-research style questions: industry trends, company analysis, thesis framing. Emits a citations artifact.",
    args_schema=QueryArgs,
)


def _tavily_search(query: str, num_results: int = 8) -> str:
    res = asyncio.run(research_tools.tavily_search(query))
    if res.get("error"):
        return f"Tavily error: {res['error']}"
    items = [{
        "title": r.get("title") or "",
        "url": r.get("url") or "",
        "doc_type": "tavily",
        "snippet": (r.get("content") or "")[:300],
        "score": round(float(r.get("score") or 0), 3),
    } for r in res.get("results", [])[:num_results]]
    if not items:
        return "No Tavily results."
    return emit(
        kind="citations",
        title=f"Tavily — {query}",
        subtitle=f"{len(items)} web results",
        items=items,
    )


tavily_search = StructuredTool.from_function(
    func=_tavily_search,
    name="tavily_search",
    description="Real-time web search via Tavily with high-quality citations. Use for fresh news, regulatory signals, announcements. Emits a citations artifact.",
    args_schema=QueryArgs,
)


def _deep_research(query: str, num_results: int = 8) -> str:
    """Parallel EXA + Tavily search with combined artifact."""
    res = asyncio.run(research_tools.deep_research(query))
    items: list[dict] = []
    for r in res.get("exa", {}).get("results", []):
        items.append({
            "title": r.get("title") or "",
            "url": r.get("url") or "",
            "doc_type": "exa",
            "snippet": (r.get("snippet") or "")[:300],
            "score": round(float(r.get("score") or 0), 3),
        })
    for r in res.get("tavily", {}).get("results", []):
        items.append({
            "title": r.get("title") or "",
            "url": r.get("url") or "",
            "doc_type": "tavily",
            "snippet": (r.get("content") or "")[:300],
            "score": round(float(r.get("score") or 0), 3),
        })
    if not items:
        return "No research results."
    return emit(
        kind="citations",
        title=f"Deep research — {query}",
        subtitle=f"{len(items)} combined results (EXA + Tavily)",
        items=items,
    )


deep_research = StructuredTool.from_function(
    func=_deep_research,
    name="deep_research",
    description="Run EXA + Tavily in parallel and combine into one citations artifact. Preferred when the question is broad.",
    args_schema=QueryArgs,
)
