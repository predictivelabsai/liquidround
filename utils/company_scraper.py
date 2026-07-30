"""Scrape company info from a URL using Tavily + direct fetch + LLM extraction.

Returns a CompanyProfile dict with name, description, products, end_markets,
sector classification, and NACE code — used by all three lead-magnet tools.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from utils.llm_factory import create_llm
from utils.research_tools import ResearchTools

log = logging.getLogger(__name__)
_research = ResearchTools()

EXTRACTION_PROMPT = """\
You are a business analyst. Given content from a company's website,
extract structured company information.

Website content:
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
    source_text: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


async def _fetch_website_text(url: str) -> str:
    """Fetch a website URL and extract visible text from HTML."""
    import httpx

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; LiquidRound/1.0; +https://liquidround.ai)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en,et,lt,lv;q=0.5",
    }
    try:
        from utils.security import validate_public_url, validate_redirect_url
        current = validate_public_url(url)
        async with httpx.AsyncClient(follow_redirects=False, timeout=15.0) as client:
            for _ in range(5):
                resp = await client.get(current, headers=headers)
                if resp.is_redirect:
                    current = validate_redirect_url(current, resp.headers.get("location", ""))
                    continue
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "").lower()
                if "html" not in content_type and "text/" not in content_type:
                    raise ValueError("URL did not return an HTML page")
                html = resp.text
                break
            else:
                raise ValueError("Too many redirects")
    except Exception as e:
        log.warning("Direct fetch failed for %s: %s", url, e)
        return ""

    text = _html_to_text(html)
    return text[:6000]


def _html_to_text(html: str) -> str:
    """Extract visible text from HTML, stripping tags and scripts."""
    html = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<nav[^>]*>.*?</nav>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<footer[^>]*>.*?</footer>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', ' ', html, flags=re.DOTALL)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'&[a-z]+;', ' ', html)
    html = re.sub(r'\s+', ' ', html)
    return html.strip()


async def scrape_company(url: str) -> CompanyProfile:
    """Scrape a company URL via Tavily search + direct fetch + LLM extraction.

    Strategy: try Tavily first; if no results, fall back to direct HTTP fetch.
    Both paths feed content to the LLM for structured extraction.
    """
    from utils.security import validate_public_url
    url = validate_public_url(url).rstrip("/")

    domain = url.split("//")[-1].split("/")[0]

    # --- Strategy 1: Tavily search ---
    search_text = ""
    queries = [
        f"{domain} company about products services",
        f"site:{domain}",
    ]
    for query in queries:
        try:
            result = await _research.tavily_search(query, search_depth="advanced")
            for r in result.get("results", [])[:5]:
                search_text += f"URL: {r.get('url', '')}\n"
                search_text += f"Title: {r.get('title', '')}\n"
                search_text += f"Content: {r.get('content', '')}\n\n"
        except Exception as e:
            log.warning("Tavily search failed for %s: %s", query, e)
        if len(search_text.strip()) > 200:
            break

    # --- Strategy 2: Direct fetch if Tavily found nothing ---
    source_text = ""
    if len(search_text.strip()) < 200:
        log.info("Tavily returned thin results for %s, trying direct fetch", domain)
        page_text = await _fetch_website_text(url)
        if page_text:
            source_text = page_text[:2000]
            search_text = f"URL: {url}\nDirect website content:\n{page_text}\n"

    if not search_text.strip():
        return CompanyProfile(url=url, name=domain, sector="Technology")

    llm = create_llm(temperature=0.1)
    prompt = EXTRACTION_PROMPT.format(search_results=search_text[:6000])

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
        return CompanyProfile(url=url, name=domain, sector="Technology")

    return CompanyProfile(
        url=url,
        name=data.get("name") or domain,
        description=data.get("description") or "",
        products=data.get("products") or [],
        end_markets=data.get("end_markets") or [],
        sector=data.get("sector") or "Technology",
        sub_sector=data.get("sub_sector") or "",
        nace_code=data.get("nace_code") or "",
        country=data.get("country") or "",
        employees_estimate=data.get("employees_estimate"),
        source_text=source_text,
    )
