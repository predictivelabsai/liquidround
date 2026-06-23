"""Sync deal candidate pool — Tavily research + LLM extraction.

Run daily (via scheduler or manually) to keep the pool fresh:

    python -m scripts.sync_deal_candidates
    python -m scripts.sync_deal_candidates --dry-run
"""
from __future__ import annotations

import json
import logging
import re
import sys

log = logging.getLogger(__name__)

QUERIES = [
    "Lithuania startup acquisition funding 2024 2025 2026",
    "Estonia startup acquired investment round 2025 2026",
    "Baltic private company M&A deal SME acquisition Lithuania",
    "Estonian Lithuanian startup raised investment seed series 2025",
    "Baltic fintech healthtech SaaS startup funding round",
    "Lithuania Estonia logistics agritech deeptech startup deal",
    "Baltic PE buyout growth equity portfolio company exit",
    "Lithuanian Estonian founder succession business sale",
]

EXTRACT_PROMPT = """You are a senior Baltic ECM / M&A analyst.

Given web research results about Lithuanian and Estonian companies and deals,
extract ALL distinct real PRIVATE companies that are involved in or suitable
for M&A activity (acquisitions, divestitures, growth equity, buyouts).

For EACH company return a JSON object:
- name: company name
- country: "Lithuania" or "Estonia"
- sector: industry sector
- description: what the company does (1 sentence)
- deal_context: what deal or M&A angle exists (announced deal, rumoured sale,
  PE-owned exit candidate, founder succession, consolidation target, etc.)
- deal_size_estimate: rough estimate if available, else "undisclosed"
- source: brief note on where this was found

RULES:
- ONLY PRIVATE companies. NO publicly listed companies.
- Only REAL companies. Do not invent.
- Include as many valid companies as the research supports (no cap).

Return ONLY a JSON array, no markdown fencing."""


def _search(query: str, max_results: int = 5) -> list[dict]:
    from utils.config import config
    from tavily import TavilyClient
    client = TavilyClient(api_key=config.tavily_api_key)
    resp = client.search(query=query, search_depth="advanced", max_results=max_results)
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""),
         "content": r.get("content", "")[:600]}
        for r in resp.get("results", [])
    ]


def _extract(research: list[dict]) -> list[dict]:
    from utils.config import config
    from utils.llm_factory import create_llm
    provider = "xai" if config.xai_api_key else config.default_provider
    llm = create_llm(provider=provider, temperature=0.5)
    text = "\n\n".join(f"**{r['title']}**\n{r['content']}" for r in research)
    resp = llm.invoke(f"Web research results:\n\n{text}\n\n{EXTRACT_PROMPT}")
    raw = resp.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        return json.loads(match.group()) if match else []


def _upsert(companies: list[dict], dry_run: bool = False) -> dict:
    from utils.database import get_conn
    inserted = 0
    updated = 0
    for c in companies:
        name = c.get("name", "").strip()
        country = c.get("country", "").strip()
        if not name or not country:
            continue
        if dry_run:
            log.info("[dry-run] %s (%s) — %s", name, country, c.get("sector", ""))
            inserted += 1
            continue
        try:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO liquidround.deal_candidates
                        (company_name, country, sector, description, deal_context,
                         deal_size_estimate, source, source_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_name, country) DO UPDATE SET
                        sector = EXCLUDED.sector,
                        description = EXCLUDED.description,
                        deal_context = EXCLUDED.deal_context,
                        deal_size_estimate = EXCLUDED.deal_size_estimate,
                        source = EXCLUDED.source,
                        source_url = EXCLUDED.source_url,
                        discovered_at = NOW()
                """, (name, country, c.get("sector", ""), c.get("description", ""),
                      c.get("deal_context", ""), c.get("deal_size_estimate", ""),
                      c.get("source", ""), c.get("source_url", "")))
                if cur.statusmessage.startswith("INSERT"):
                    inserted += 1
                else:
                    updated += 1
        except Exception:
            log.exception("Failed to upsert %s", name)

    return {"inserted": inserted, "updated": updated, "total": len(companies)}


def main(dry_run: bool = False) -> dict:
    all_research = []
    for q in QUERIES:
        try:
            results = _search(q, max_results=5)
            all_research.extend(results)
            log.info("Query '%s' → %d results", q[:40], len(results))
        except Exception:
            log.exception("Search failed for: %s", q[:40])

    if not all_research:
        log.warning("No research results — aborting")
        return {"inserted": 0, "updated": 0, "total": 0}

    companies = _extract(all_research)
    log.info("LLM extracted %d companies", len(companies))
    result = _upsert(companies, dry_run=dry_run)
    log.info("Upsert: inserted=%d updated=%d total=%d",
             result["inserted"], result["updated"], result["total"])
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    dry = "--dry-run" in sys.argv
    r = main(dry_run=dry)
    print(json.dumps(r, indent=2))
