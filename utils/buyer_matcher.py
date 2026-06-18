"""Hybrid buyer matching: Baltic company databases + Tavily web search.

Searches EE/LT/LV company registries by sector and enriches with
Tavily search for PE firms and strategic acquirers.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from utils.llm_factory import create_llm
from utils.research_tools import ResearchTools

log = logging.getLogger(__name__)
_research = ResearchTools()
DATA = Path(__file__).resolve().parent.parent / "data"

_BALTIC_CACHE: dict[str, list[dict]] = {}


def _load_baltic_companies(country: str) -> list[dict]:
    """Load and cache Baltic company data from JSON files."""
    if country in _BALTIC_CACHE:
        return _BALTIC_CACHE[country]
    fname = {"EE": "ee_companies.json", "LT": "lt_companies.json", "LV": "lv_companies.json"}
    path = DATA / fname.get(country, "")
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            companies = json.load(f)
        _BALTIC_CACHE[country] = companies
        log.info("Loaded %d %s companies", len(companies), country)
        return companies
    except Exception as e:
        log.warning("Failed to load %s companies: %s", country, e)
        return []


def _match_baltic_buyers(sector: str, sub_sector: str, limit: int = 10) -> list[dict]:
    """Find potential acquirers in Baltic databases by sector match."""
    sector_lower = sector.lower()
    sub_lower = sub_sector.lower() if sub_sector else ""
    matches = []

    for country in ("EE", "LT", "LV"):
        companies = _load_baltic_companies(country)
        for c in companies:
            c_sector = (c.get("sector") or "").lower()
            c_sub = (c.get("sub_sector") or "").lower()
            score = 0
            if c_sector and c_sector in sector_lower:
                score += 2
            if c_sub and sub_lower and c_sub in sub_lower:
                score += 3
            if score == 0:
                continue

            financials = c.get("financials", {})
            if isinstance(financials, list) and financials:
                financials = financials[0]
            elif not isinstance(financials, dict):
                financials = {}

            revenue = financials.get("sales_revenue", 0) or 0
            if revenue < 100000:
                continue

            matches.append({
                "name": c.get("name", ""),
                "country": country,
                "sector": c.get("sector", ""),
                "sub_sector": c.get("sub_sector", ""),
                "website": c.get("website", ""),
                "address": c.get("address", ""),
                "founded": c.get("founded", ""),
                "revenue": revenue,
                "source": "baltic_registry",
                "score": score,
            })

    matches.sort(key=lambda x: (-x["score"], -x.get("revenue", 0)))
    return matches[:limit]


async def _search_web_buyers(sector: str, sub_sector: str, company_name: str) -> list[dict]:
    """Search for PE firms and strategic acquirers via Tavily."""
    queries = [
        f"{sector} {sub_sector} acquisitions buyers Europe",
        f"{sector} private equity investors Baltic Nordic",
    ]
    web_buyers = []
    for q in queries:
        result = await _research.tavily_search(q, search_depth="basic")
        for r in result.get("results", [])[:5]:
            web_buyers.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:300],
            })
    return web_buyers


RATIONALE_PROMPT = """\
You are an M&A advisor. A company is looking for potential buyers/acquirers.

Target company: {company_name}
Target sector: {sector} / {sub_sector}
Target description: {description}

Below are potential buyers found from Baltic business registries and web search.

Baltic registry matches:
{baltic_matches}

Web search results:
{web_results}

For each of the top {count} most relevant buyers, provide:
{{
  "buyers": [
    {{
      "name": "Buyer company name",
      "country": "2-letter code",
      "type": "strategic | private_equity | family_office",
      "rationale": "2-3 sentences explaining WHY this buyer is a good match for the target",
      "website": "URL if known",
      "backed_by": "Investors/owners if known, else empty string"
    }}
  ]
}}

Return valid JSON only.
"""


@dataclass
class BuyerMatch:
    name: str = ""
    country: str = ""
    type: str = "strategic"
    rationale: str = ""
    website: str = ""
    backed_by: str = ""
    revenue: float = 0
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


async def find_buyers(
    company_name: str,
    sector: str,
    sub_sector: str,
    description: str,
    count: int = 5,
) -> list[BuyerMatch]:
    """Find potential buyers using Baltic DB + Tavily hybrid approach."""
    baltic_task = asyncio.to_thread(_match_baltic_buyers, sector, sub_sector, 15)
    web_task = _search_web_buyers(sector, sub_sector, company_name)
    baltic_matches, web_results = await asyncio.gather(baltic_task, web_task)

    baltic_text = "\n".join(
        f"- {m['name']} ({m['country']}) — {m['sector']}/{m['sub_sector']}, "
        f"revenue €{m['revenue']:,.0f}, website: {m.get('website', 'n/a')}"
        for m in baltic_matches[:10]
    ) or "No Baltic registry matches found."

    web_text = "\n".join(
        f"- {r['title']}: {r['content']}"
        for r in web_results[:8]
    ) or "No web results found."

    llm = create_llm(temperature=0.3)
    prompt = RATIONALE_PROMPT.format(
        company_name=company_name,
        sector=sector,
        sub_sector=sub_sector,
        description=description,
        baltic_matches=baltic_text,
        web_results=web_text,
        count=count,
    )

    try:
        resp = await asyncio.to_thread(lambda: llm.invoke(prompt).content)
        text = resp.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
        buyers_data = data.get("buyers", [])
    except Exception as e:
        log.warning("Buyer rationale generation failed: %s", e)
        buyers_data = [
            {"name": m["name"], "country": m["country"], "type": "strategic",
             "rationale": f"Operates in {m['sector']}/{m['sub_sector']} sector.",
             "website": m.get("website", ""), "backed_by": ""}
            for m in baltic_matches[:count]
        ]

    return [
        BuyerMatch(
            name=b.get("name", ""),
            country=b.get("country", ""),
            type=b.get("type", "strategic"),
            rationale=b.get("rationale", ""),
            website=b.get("website", ""),
            backed_by=b.get("backed_by", ""),
            source=b.get("source", "hybrid"),
        )
        for b in buyers_data[:count]
    ]
