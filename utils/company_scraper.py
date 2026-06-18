"""Scrape company info from a URL using Tavily + LLM extraction.

Returns a CompanyProfile dict with name, description, products, end_markets,
sector classification, and NACE code — used by all three lead-magnet tools.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from utils.llm_factory import create_llm
from utils.research_tools import ResearchTools

log = logging.getLogger(__name__)
_research = ResearchTools()

EXTRACTION_PROMPT = """\
You are a business analyst. Given web search results about a company website,
extract structured company information.

Search results:
{search_results}

Return valid JSON with these fields:
{{
  "name": "Company legal or brand name",
  "description": "2-3 sentence description of what the company does",
  "products": ["product/service 1", "product/service 2", ...],
  "end_markets": ["target market 1", "target market 2", ...],
  "sector": "One of: Technology, Healthcare, Manufacturing, Business Services, Consumer, Energy, Financial Services, Real Estate, Other",
  "sub_sector": "More specific classification within the sector",
  "nace_code": "Best-guess 4-digit NACE/EMTAK code or empty string",
  "country": "Country of HQ (2-letter ISO code) or empty string",
  "employees_estimate": "Estimated employee count or null"
}}

Only return the JSON object, nothing else.
"""


@dataclass
class CompanyProfile:
    url: str = ""
    name: str = ""
    description: str = ""
    products: list[str] = field(default_factory=list)
    end_markets: list[str] = field(default_factory=list)
    sector: str = ""
    sub_sector: str = ""
    nace_code: str = ""
    country: str = ""
    employees_estimate: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


async def scrape_company(url: str) -> CompanyProfile:
    """Scrape a company URL via Tavily search + LLM extraction.

    Handles multilingual sites by trying both English and local-language queries.
    """
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = f"https://{url}"

    domain = url.split("//")[-1].split("/")[0]

    queries = [
        f"{domain} company about products services",
        f"site:{domain}",
        f"{domain} ettevõte teenused tooted",  # Estonian
        f"{domain} įmonė paslaugos produktai",  # Lithuanian
        f"{domain} uzņēmums pakalpojumi produkti",  # Latvian
    ]

    search_text = ""
    for query in queries:
        result = await _research.tavily_search(query, search_depth="advanced")
        for r in result.get("results", [])[:5]:
            search_text += f"URL: {r.get('url', '')}\n"
            search_text += f"Title: {r.get('title', '')}\n"
            search_text += f"Content: {r.get('content', '')}\n\n"
        if len(search_text.strip()) > 200:
            break

    if not search_text.strip():
        return CompanyProfile(url=url, name=domain)

    llm = create_llm(temperature=0.1)
    prompt = EXTRACTION_PROMPT.format(search_results=search_text[:4000])

    try:
        resp = await asyncio.to_thread(
            lambda: llm.invoke(prompt).content
        )
        text = resp.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
    except Exception as e:
        log.warning("LLM extraction failed for %s: %s", url, e)
        return CompanyProfile(url=url, name=domain)

    return CompanyProfile(
        url=url,
        name=data.get("name", domain),
        description=data.get("description", ""),
        products=data.get("products", []),
        end_markets=data.get("end_markets", []),
        sector=data.get("sector", "Other"),
        sub_sector=data.get("sub_sector", ""),
        nace_code=data.get("nace_code", ""),
        country=data.get("country", ""),
        employees_estimate=data.get("employees_estimate"),
    )
