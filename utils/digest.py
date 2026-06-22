"""Daily Deal Digest — Tavily-sourced LT/EE companies, LLM thesis per company,
yfinance for comps only, pick one for a featured deep dive."""

from __future__ import annotations

import json
import os
import re
import requests
from datetime import date
from typing import Optional

from utils.llm_factory import create_llm
from utils.config import config


def _llm(temperature: float = 0.7):
    """Create LLM with the provider that has a valid key."""
    provider = "xai" if config.xai_api_key else config.default_provider
    return create_llm(provider=provider, temperature=temperature)


# ── Tavily research ───────────────────────────────────────────────────


def _tavily_search(query: str, max_results: int = 10) -> list[dict]:
    """Synchronous Tavily search."""
    from tavily import TavilyClient
    client = TavilyClient(api_key=config.tavily_api_key)
    resp = client.search(query=query, search_depth="advanced", max_results=max_results)
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")[:600]}
        for r in resp.get("results", [])
    ]


def _research_companies() -> list[dict]:
    """Use Tavily to find real private LT/EE companies involved in M&A, funding, or deals."""
    queries = [
        "Lithuania Estonia startup acquisition funding 2024 2025",
        "Baltic private company M&A deal SME acquisition Lithuania Estonia",
        "Estonian Lithuanian startup raised investment seed series A B 2025",
        "Baltic fintech healthtech SaaS startup funding round",
    ]
    all_results = []
    for q in queries:
        try:
            results = _tavily_search(q, max_results=5)
            all_results.extend(results)
        except Exception:
            pass
    return all_results


# ── yfinance comps (secondary) ────────────────────────────────────────

BALTIC_COMPS = [
    "TAL1T.TL", "TKM1T.TL", "EEG1T.TL", "SFG1T.TL", "TSM1T.TL",
    "APG1L.VS", "GRG1L.VS", "PZV1L.VS", "TEL1L.VS", "RSU1L.VS",
    "VLP1L.VS", "NTU1L.VS", "INC1L.VS",
]


def _fetch_comps_summary() -> str:
    """Fetch a brief Baltic comps summary via yfinance for LLM context."""
    from utils.yfinance_util import YFinanceUtil
    yf = YFinanceUtil()
    lines = []
    for ticker in BALTIC_COMPS[:8]:
        try:
            p = yf.get_company_profile(ticker)
            f = yf.get_financials(ticker)
            if p.get("error"):
                continue
            mcap = p.get("market_cap", 0)
            ev_ebitda = f.get("ev_to_ebitda", 0)
            margin = f.get("ebitda_margins", 0)
            lines.append(
                f"- {p['name']} ({ticker}): MCap €{mcap/1e6:.0f}M, "
                f"EV/EBITDA {ev_ebitda:.1f}x, EBITDA margin {margin*100:.1f}%"
            )
        except Exception:
            pass
    return "\n".join(lines) if lines else "Baltic comps data unavailable."


# ── LLM prompts ───────────────────────────────────────────────────────


EXTRACT_SYSTEM = """You are a senior Baltic ECM / M&A analyst.

Given web research results about Lithuanian and Estonian companies and deals,
extract exactly 10 distinct real PRIVATE companies that are involved in or
suitable for M&A activity (acquisitions, divestitures, growth equity, buyouts).

For EACH company return a JSON object:
- name: company name
- country: "Lithuania" or "Estonia"
- sector: industry sector
- is_public: false (must be false — see rules)
- estimated_revenue_eur: estimated annual revenue in EUR (number), must be under 10000000
- description: what the company does (1 sentence)
- deal_context: what deal or M&A angle exists (announced deal, rumoured sale,
  PE-owned exit candidate, founder succession, consolidation target, etc.)
- deal_size_estimate: rough estimate if available, else "undisclosed"
- source: brief note on where this was found

RULES:
- ONLY PRIVATE companies. NO publicly listed companies (no Nasdaq Baltic, no
  stock exchange listings). Filter out Enefit Green, Ignitis, Tallink, Telia
  Lietuva, LHV Group, Šiaulių Bankas, and any other listed entity.
- Revenue / ARR must be UNDER €10M. Focus on early-stage, growth-stage, or
  small-cap private companies. No large enterprises.
- Only REAL companies. Do not invent.
- Prefer companies with a concrete deal angle (announced, rumoured, or logical).
- Good sources: Baltic startup ecosystem, PE/VC portfolio companies, founder-led
  SMEs, niche tech/SaaS, deep-tech, fintech, healthtech, agritech, logistics
  startups, craft manufacturers.
- If the research doesn't have 10, fill remaining slots with real LT/EE startups
  or SMEs that have a credible M&A angle.

Return ONLY a JSON array, no markdown fencing."""


THESIS_SYSTEM = """You are a senior Baltic ECM / M&A analyst.
Given a company and its context, write a concise 2-3 sentence investment thesis:
- Why this company is interesting from an M&A / strategic perspective RIGHT NOW
- What a potential acquirer or investor gains
- One key risk or consideration

Reference the Baltic comparable multiples provided for valuation context.
Be specific — no generic language. Keep it under 60 words."""


DEEP_DIVE_SYSTEM = """You are a senior Baltic ECM / M&A analyst writing a featured deal deep dive
for an institutional investor newsletter. The company is PRIVATE (not listed)
with revenue under €10M.

Given the company details and Baltic comparable multiples below, write a thorough
300-400 word analysis covering:

1. **Company Overview** — What they do, where they operate, approximate scale.
2. **Deal Context** — What's the M&A angle? PE interest, founder succession,
   strategic acquisition target, acqui-hire, or growth equity candidate? Who are
   the likely buyers or investors?
3. **Valuation Context** — How might this private company be valued? Reference
   Baltic listed peer multiples as a ceiling, then apply a private-company
   discount. What revenue or ARR multiple is realistic for the sector?
4. **Triage Verdict** — Your GO / NO-GO / REVIEW call with 3 supporting bullets:
   - Fit (size, sector, geography, growth, margin)
   - Red flags (key-man risk, customer concentration, limited track record)
   - Next step if GO (e.g. "approach founder", "request data room", "co-invest")
5. **Key Risk** — The one thing that could derail an investment thesis.

Write in a direct, analytical tone. Format with markdown headers (##).
End with a one-line bottom line."""


PICK_SYSTEM = """You are a senior Baltic ECM / M&A analyst selecting the most
interesting company for a featured deep dive in today's newsletter.

Given the list of companies, pick the ONE that is most compelling today. Consider:
- Concrete deal activity (announced > rumoured > candidate)
- Strategic interest (what would make a reader stop scrolling?)
- Sector dynamics and timeliness

Return ONLY a JSON object: {"name": "...", "reason": "one sentence why"}"""


# ── Core pipeline ─────────────────────────────────────────────────────


PUBLIC_BLOCKLIST = {
    "enefit green", "ignitis group", "ignitis", "tallink", "tallink grupp",
    "telia lietuva", "lhv group", "lhv", "šiaulių bankas", "siauliu bankas",
    "ekspress grupp", "tallinna sadam", "tkm grupp", "silvano fashion",
    "apranga", "grigeo", "pieno žvaigždės", "pieno zvaigzdes", "rokiskio suris",
    "vilkyškių pieninė", "vilkyskiu pienine", "novaturas", "invl technology",
    "bolt", "vinted", "wise", "transferwise",
}


def _is_public(c: dict) -> bool:
    name_lower = c.get("name", "").lower()
    if c.get("is_public") is True:
        return True
    return any(bl in name_lower for bl in PUBLIC_BLOCKLIST)


def _revenue_over_limit(c: dict, limit: int = 10_000_000) -> bool:
    rev = c.get("estimated_revenue_eur", 0)
    if isinstance(rev, (int, float)) and rev > limit:
        return True
    return False


def _extract_companies(research: list[dict]) -> list[dict]:
    """LLM extracts structured company list from research results."""
    llm = _llm(temperature=0.5)
    research_text = "\n\n".join(
        f"**{r['title']}**\n{r['content']}" for r in research
    )
    resp = llm.invoke(f"Web research results:\n\n{research_text}\n\n{EXTRACT_SYSTEM}")
    text = resp.content.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        companies = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        companies = json.loads(match.group()) if match else []

    filtered = [c for c in companies
                if not _is_public(c) and not _revenue_over_limit(c)]

    return filtered[:10]


def _generate_thesis(company: dict, comps: str) -> str:
    """Generate a unique thesis for one company with comps context."""
    llm = _llm(temperature=0.7)
    data = json.dumps(company, indent=2, default=str)
    resp = llm.invoke(
        f"Company:\n{data}\n\nBaltic comparable companies:\n{comps}\n\n{THESIS_SYSTEM}"
    )
    return resp.content.strip()


def _pick_featured(companies: list[dict]) -> dict:
    """LLM picks the most interesting company for the deep dive."""
    llm = _llm(temperature=0.3)
    summaries = [
        {"name": c["name"], "country": c.get("country", ""),
         "sector": c.get("sector", ""), "deal_context": c.get("deal_context", ""),
         "thesis": c.get("thesis", "")}
        for c in companies
    ]
    resp = llm.invoke(f"Companies:\n{json.dumps(summaries, indent=2)}\n\n{PICK_SYSTEM}")
    text = resp.content.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        pick = json.loads(text)
        name = pick.get("name", "")
        for c in companies:
            if c["name"] == name:
                c["pick_reason"] = pick.get("reason", "")
                return c
    except (json.JSONDecodeError, KeyError):
        pass

    return companies[0]


def _generate_deep_dive(company: dict, comps: str) -> str:
    """Generate a thorough deep-dive analysis for the featured company."""
    llm = _llm(temperature=0.5)
    data = json.dumps(company, indent=2, default=str)
    resp = llm.invoke(
        f"Company:\n{data}\n\nBaltic comparable multiples:\n{comps}\n\n{DEEP_DIVE_SYSTEM}"
    )
    return resp.content.strip()


def build_digest(n_companies: int = 10) -> dict:
    """Build the full daily digest:
    1. Tavily researches real LT/EE deals
    2. LLM extracts 10 companies
    3. yfinance provides Baltic comps context
    4. LLM generates unique thesis per company
    5. LLM picks best company for deep dive
    6. LLM generates detailed triage analysis
    """
    research = _research_companies()

    companies = _extract_companies(research)
    if not companies:
        return {"companies": [], "deep_dive": "", "featured": None,
                "date": date.today().isoformat()}

    comps = _fetch_comps_summary()

    for c in companies[:n_companies]:
        c["thesis"] = _generate_thesis(c, comps)

    companies = companies[:n_companies]
    featured = _pick_featured(companies)
    deep_dive = _generate_deep_dive(featured, comps)

    return {
        "companies": companies,
        "featured": featured,
        "deep_dive": deep_dive,
        "date": date.today().isoformat(),
    }


# ── Email rendering ───────────────────────────────────────────────────


def _country_flag(country: str) -> str:
    flags = {"Estonia": "🇪🇪", "Lithuania": "🇱🇹", "Latvia": "🇱🇻"}
    return flags.get(country, "🌍")


def _deal_type_color(ctx: str) -> str:
    ctx_lower = (ctx or "").lower()
    if "announced" in ctx_lower or "acquired" in ctx_lower:
        return "#3B82F6"
    if "rumour" in ctx_lower:
        return "#F59E0B"
    if "ipo" in ctx_lower:
        return "#10B981"
    if "buyout" in ctx_lower or "pe" in ctx_lower:
        return "#8B5CF6"
    if "exit" in ctx_lower or "sale" in ctx_lower:
        return "#EC4899"
    return "#6B7280"


def render_email_html(digest: dict) -> str:
    """Render the digest as a styled HTML email."""
    today = date.today().strftime("%B %d, %Y")
    companies = digest.get("companies", [])
    featured = digest.get("featured", {})
    deep_dive_md = digest.get("deep_dive", "")

    company_cards = ""
    for i, c in enumerate(companies):
        is_featured = (c.get("name") == featured.get("name"))
        badge = (' <span style="background:#F59E0B;color:#fff;font-size:10px;'
                 'padding:1px 6px;border-radius:3px;font-weight:600;">DEEP DIVE</span>'
                 if is_featured else "")
        flag = _country_flag(c.get("country", ""))
        accent = _deal_type_color(c.get("deal_context", ""))
        deal_size = c.get("deal_size_estimate", "")
        size_text = f" &middot; {deal_size}" if deal_size and deal_size != "undisclosed" else ""

        company_cards += f"""
        <div style="border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:4px;">
            <div style="font-weight:600;color:#0f172a;font-size:14px;">
              {flag} {c.get('name', 'N/A')}{badge}
            </div>
          </div>
          <div style="font-size:11px;color:#64748b;margin-top:2px;">
            {c.get('sector', '')} &middot; {c.get('country', '')}{size_text}
          </div>
          <div style="font-size:12px;color:#475569;margin-top:4px;">
            {c.get('description', '')}
          </div>
          <div style="font-size:11px;color:#334155;margin-top:6px;padding:4px 8px;background:#e0f2fe;border-radius:4px;display:inline-block;">
            <strong>Deal angle:</strong> {c.get('deal_context', '')}
          </div>
          <div style="font-size:12px;color:#334155;line-height:1.5;background:#f1f5f9;padding:10px 12px;border-radius:6px;border-left:3px solid {accent};margin-top:6px;">
            <strong style="color:#0f172a;">Thesis:</strong> {c.get('thesis', '')}
          </div>
        </div>"""

    deep_dive_html = _markdown_to_email_html(deep_dive_md)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Inter','Helvetica Neue',Arial,sans-serif;-webkit-text-size-adjust:100%;">
  <div style="max-width:600px;margin:0 auto;padding:0 12px;">

    <!-- Header -->
    <div style="background:#0B1220;padding:20px 16px;text-align:center;border-radius:0 0 8px 8px;">
      <div style="font-size:22px;font-weight:700;color:#F59E0B;letter-spacing:-0.5px;">LiquidRound</div>
      <div style="font-size:12px;color:#94a3b8;margin-top:4px;">Baltic ECM &amp; M&amp;A Daily Digest</div>
      <div style="font-size:11px;color:#64748b;margin-top:2px;">{today}</div>
    </div>

    <!-- Intro -->
    <div style="padding:16px 4px 8px;">
      <p style="font-size:13px;color:#334155;line-height:1.6;margin:0;">
        Today's digest covers {len(companies)} Lithuanian and Estonian
        companies with live M&amp;A angles, each with an AI-generated investment thesis
        and a featured deep dive.
      </p>
    </div>

    <!-- Company Cards -->
    <div style="padding:8px 0 12px;">
      <div style="background:#0B1220;border-radius:8px;padding:10px 12px;margin-bottom:8px;">
        <div style="font-size:12px;font-weight:600;color:#F59E0B;text-transform:uppercase;letter-spacing:0.5px;">
          Daily Company Scan &mdash; {len(companies)} Companies
        </div>
      </div>
      {company_cards}
    </div>

    <!-- Deep Dive Section -->
    <div style="padding:0 0 16px;">
      <div style="background:#0B1220;border-radius:8px;overflow:hidden;">
        <div style="padding:12px 16px;border-bottom:2px solid #F59E0B;">
          <div style="font-size:11px;font-weight:700;color:#F59E0B;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">
            Deep Dive
          </div>
          <div style="font-size:16px;font-weight:700;color:#e2e8f0;">
            {_country_flag(featured.get('country', ''))} {featured.get('name', 'N/A')}
          </div>
          <div style="font-size:11px;color:#94a3b8;margin-top:2px;">
            {featured.get('sector', '')} &middot; {featured.get('country', '')} &middot; {featured.get('deal_context', '')}
          </div>
        </div>
        <div style="padding:16px;color:#cbd5e1;font-size:13px;line-height:1.7;">
          {deep_dive_html}
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div style="text-align:center;padding:16px 0;border-top:1px solid #e2e8f0;margin-top:4px;">
      <p style="color:#6B7280;font-size:11px;margin:0 0 4px;">
        <a href="https://liquidround.com/app" style="color:#F59E0B;text-decoration:none;font-weight:600;">Open LiquidRound</a>
      </p>
      <p style="color:#94a3b8;font-size:10px;margin:0 0 2px;">
        Generated by LiquidRound AI &middot; Predictive Labs Ltd
      </p>
      <p style="color:#cbd5e1;font-size:10px;margin:0;">
        AI-generated analysis for informational purposes only. Not investment advice.
      </p>
      <p style="margin:8px 0 0;">
        <a href="https://liquidround.ai/profile" style="color:#94a3b8;font-size:10px;text-decoration:underline;">Unsubscribe</a>
      </p>
    </div>

  </div>
</body>
</html>"""


def _markdown_to_email_html(md: str) -> str:
    """Minimal markdown → inline-styled HTML for email clients."""
    lines = md.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            out.append(f'<div style="font-size:15px;font-weight:700;color:#F59E0B;margin:16px 0 6px;border-bottom:1px solid #1e293b;padding-bottom:4px;">{stripped[3:]}</div>')
        elif stripped.startswith("# "):
            out.append(f'<div style="font-size:17px;font-weight:700;color:#e2e8f0;margin:16px 0 8px;">{stripped[2:]}</div>')
        elif stripped.startswith("- "):
            text = _inline_md(stripped[2:])
            out.append(f'<div style="padding-left:16px;margin:3px 0;">&bull; {text}</div>')
        elif stripped.startswith("> "):
            text = _inline_md(stripped[2:])
            out.append(f'<div style="border-left:3px solid #F59E0B;padding:6px 12px;margin:8px 0;color:#e2e8f0;font-weight:600;font-size:14px;">{text}</div>')
        elif stripped == "":
            out.append('<div style="height:8px;"></div>')
        else:
            out.append(f'<div style="margin:4px 0;">{_inline_md(stripped)}</div>')
    return "\n".join(out)


def _inline_md(text: str) -> str:
    """Convert bold/italic markdown to inline HTML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong style='color:#e2e8f0;'>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`",
                  r"<code style='background:#1e293b;padding:1px 4px;border-radius:3px;font-size:12px;'>\1</code>",
                  text)
    return text


# ── Digest cache ─────────────────────────────────────────────────────

_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", ".digest_cache.json")


def cache_digest(digest: dict, html: str) -> None:
    """Persist the latest digest + rendered HTML to a JSON file."""
    import logging
    log = logging.getLogger(__name__)
    try:
        payload = {"digest": digest, "html": html, "cached_at": date.today().isoformat()}
        with open(_CACHE_PATH, "w") as f:
            json.dump(payload, f, default=str)
        log.info("Digest cached to %s", _CACHE_PATH)
    except Exception:
        log.exception("Failed to cache digest")


def get_cached_digest() -> dict | None:
    """Load the cached digest, or None if unavailable."""
    try:
        with open(_CACHE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ── Digest archive (DB persistence for blog) ────────────────────────

def _blog_title(digest_date: str) -> str:
    from datetime import datetime as _dt
    try:
        d = _dt.strptime(str(digest_date)[:10], "%Y-%m-%d")
        return f"Baltic Daily Digest — {d.strftime('%-d %b %Y')}"
    except (ValueError, TypeError):
        return f"Baltic Daily Digest — {digest_date}"


def _country_flag_tw(country: str) -> str:
    flags = {"Lithuania": "\U0001f1f1\U0001f1f9", "Estonia": "\U0001f1ea\U0001f1ea",
             "Latvia": "\U0001f1f1\U0001f1fb"}
    return flags.get(country, "")


def render_blog_html(digest: dict) -> str:
    """Render digest dict as Tailwind-styled blog HTML (not email HTML)."""
    import markdown2
    companies = digest.get("companies", [])
    featured = digest.get("featured", {})
    deep_dive_md = digest.get("deep_dive", "")

    cards_html = ""
    for c in companies:
        is_featured = c.get("name") == featured.get("name")
        badge = ('<span class="ml-2 text-[10px] px-1.5 py-0.5 rounded font-semibold" '
                 f'style="background:#F59E0B;color:#0B1220;">DEEP DIVE</span>'
                 if is_featured else "")
        flag = _country_flag_tw(c.get("country", ""))
        deal_size = c.get("deal_size_estimate", "")
        size_part = f" &middot; {deal_size}" if deal_size and deal_size != "undisclosed" else ""

        cards_html += f"""
        <div class="p-4 rounded-lg mb-3" style="background:#111A2E;border:1px solid #1E293B;">
          <div class="flex items-baseline justify-between flex-wrap gap-1">
            <span class="font-semibold text-sm" style="color:#E5E7EB;">
              {flag} {c.get('name', 'N/A')}{badge}
            </span>
          </div>
          <div class="text-xs mt-1" style="color:#94A3B8;">
            {c.get('sector', '')} &middot; {c.get('country', '')}{size_part}
          </div>
          <div class="text-sm mt-2" style="color:#CBD5E1;">
            {c.get('description', '')}
          </div>
          <div class="text-xs mt-2 inline-block px-2 py-1 rounded" style="background:#1E293B;color:#94A3B8;">
            <strong>Deal angle:</strong> {c.get('deal_context', '')}
          </div>
          <div class="text-sm mt-2 p-3 rounded" style="background:#0B1220;border-left:3px solid #F59E0B;color:#CBD5E1;line-height:1.6;">
            <strong style="color:#E5E7EB;">Thesis:</strong> {c.get('thesis', '')}
          </div>
        </div>"""

    deep_dive_html = markdown2.markdown(deep_dive_md, extras=["fenced-code-blocks", "tables"])

    return f"""
    <div class="mb-8">
      <div class="text-xs font-semibold uppercase tracking-wider mb-3" style="color:#F59E0B;">
        Daily Company Scan — {len(companies)} Companies
      </div>
      {cards_html}
    </div>

    <div class="rounded-lg overflow-hidden" style="background:#111A2E;border:1px solid #1E293B;">
      <div class="p-4" style="border-bottom:2px solid #F59E0B;">
        <div class="text-xs font-bold uppercase tracking-wider mb-1" style="color:#F59E0B;">
          Deep Dive
        </div>
        <div class="text-lg font-bold" style="color:#E5E7EB;">
          {_country_flag_tw(featured.get('country', ''))} {featured.get('name', 'N/A')}
        </div>
        <div class="text-xs mt-1" style="color:#94A3B8;">
          {featured.get('sector', '')} &middot; {featured.get('country', '')} &middot; {featured.get('deal_context', '')}
        </div>
      </div>
      <div class="p-5 blog-deep-dive" style="color:#CBD5E1;font-size:14px;line-height:1.7;">
        {deep_dive_html}
      </div>
    </div>"""


def archive_digest(digest: dict, blog_html: str) -> bool:
    import logging
    log = logging.getLogger(__name__)
    try:
        from utils.database import get_conn
        d = str(digest.get("date", date.today().isoformat()))[:10]
        title = _blog_title(d)
        featured = digest.get("featured", {})
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.digest_archive
                    (digest_date, slug, title, digest_json, blog_html, company_count,
                     featured_company, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (digest_date) DO UPDATE SET
                    title = EXCLUDED.title,
                    digest_json = EXCLUDED.digest_json,
                    blog_html = EXCLUDED.blog_html,
                    company_count = EXCLUDED.company_count,
                    featured_company = EXCLUDED.featured_company
            """, (d, d, title, json.dumps(digest, default=str),
                  blog_html, len(digest.get("companies", [])),
                  featured.get("name")))
        log.info("Digest archived for %s", d)
        return True
    except Exception:
        log.exception("Failed to archive digest")
        return False


def get_archived_digest(slug: str) -> dict | None:
    try:
        from utils.database import get_conn
        from psycopg2.extras import RealDictCursor
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT slug, title, digest_date, digest_json, blog_html,
                       company_count, featured_company, beehiiv_url, created_at
                FROM liquidround.digest_archive WHERE slug = %s
            """, (slug,))
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception:
        return None


def get_archived_digests(page: int = 1, per_page: int = 12) -> tuple[list[dict], int]:
    try:
        from utils.database import get_conn
        from psycopg2.extras import RealDictCursor
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT count(*) FROM liquidround.digest_archive")
            total = cur.fetchone()["count"]
            cur.execute("""
                SELECT slug, title, digest_date, company_count, featured_company, created_at
                FROM liquidround.digest_archive
                ORDER BY digest_date DESC
                LIMIT %s OFFSET %s
            """, (per_page, (page - 1) * per_page))
            return [dict(r) for r in cur.fetchall()], total
    except Exception:
        return [], 0


def update_beehiiv_info(slug: str, post_id: str, web_url: str) -> None:
    try:
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE liquidround.digest_archive
                SET beehiiv_post_id = %s, beehiiv_url = %s
                WHERE slug = %s
            """, (post_id, web_url, slug))
    except Exception:
        logging.getLogger(__name__).exception("Failed to update Beehiiv info")


def backfill_archive_from_cache() -> bool:
    cached = get_cached_digest()
    if not cached or not cached.get("digest"):
        return False
    digest = cached["digest"]
    blog_html = render_blog_html(digest)
    return archive_digest(digest, blog_html)


# ── Email sending ─────────────────────────────────────────────────────


def _acquire_digest_lock() -> bool:
    """Try to claim today's digest slot via DB advisory lock.
    Returns True if this process should send, False if another already did."""
    from datetime import date
    try:
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.workflows (user_query, workflow_type, status, created_at)
                SELECT %s, 'digest_lock', 'completed', NOW()
                WHERE NOT EXISTS (
                    SELECT 1 FROM liquidround.workflows
                    WHERE workflow_type = 'digest_lock'
                      AND user_query = %s
                )
            """, (str(date.today()), str(date.today())))
            return cur.rowcount > 0
    except Exception as e:
        logging.getLogger(__name__).warning("Digest lock check failed: %s", e)
        return True  # fail open — better to send twice than not at all


def send_digest_to_all() -> dict:
    """Build the digest once, then send to every opted-in user.
    Returns summary with counts and per-recipient results."""
    import logging
    log = logging.getLogger(__name__)

    if not _acquire_digest_lock():
        log.info("Daily digest: another instance already sent today, skipping")
        return {"ok": True, "sent": 0, "skipped": 0, "dedup": True, "recipients": []}

    from utils.preferences import get_digest_recipients

    recipients = get_digest_recipients()
    if not recipients:
        log.info("Daily digest: no opted-in recipients, skipping")
        return {"ok": True, "sent": 0, "skipped": 0, "recipients": []}

    log.info(f"Daily digest: building for {len(recipients)} recipient(s)")
    digest = build_digest(n_companies=10)
    html = render_email_html(digest)
    cache_digest(digest, html)

    # Archive to DB + render blog
    blog_html = render_blog_html(digest)
    archive_digest(digest, blog_html)

    # Beehiiv syndication (optional — skips if no API key)
    try:
        from utils.beehiiv import publish_to_beehiiv
        title = _blog_title(digest.get("date", ""))
        subtitle = f"{len(digest.get('companies', []))} Baltic M&A companies with investment theses"
        bh = publish_to_beehiiv(title, blog_html, subtitle=subtitle)
        if bh.get("ok"):
            update_beehiiv_info(digest.get("date", ""), bh["post_id"], bh["web_url"])
            log.info("Beehiiv published: %s", bh.get("web_url"))
        elif not bh.get("skipped"):
            log.warning("Beehiiv publish failed: %s", bh.get("error"))
    except Exception:
        log.exception("Beehiiv syndication error (non-fatal)")

    results = []
    sent = 0
    for r in recipients:
        email = r["email"]
        res = send_digest_email(html, to_email=email)
        results.append({"email": email, **res})
        if res.get("ok"):
            sent += 1
        else:
            log.warning(f"Digest send failed for {email}: {res.get('error')}")

    log.info(f"Daily digest: sent {sent}/{len(recipients)}")
    return {"ok": True, "sent": sent, "total": len(recipients), "results": results}


def send_digest_email(html: str, to_email: Optional[str] = None,
                      subject: Optional[str] = None) -> dict:
    """Send the digest via Postmark API. Defaults to TO_TEST_EMAIL."""
    token = os.getenv("POSTMARK_API_TOKEN")
    if not token:
        return {"ok": False, "error": "POSTMARK_API_TOKEN not set"}

    to = to_email or os.getenv("TO_TEST_EMAIL") or os.getenv("TO_EMAIL", "")
    if not to:
        return {"ok": False, "error": "No recipient email configured"}

    from_email = os.getenv("FROM_EMAIL", "info@liquidround.com")

    today = date.today().strftime("%d %b %Y")
    subj = subject or f"LiquidRound Baltic Daily Digest — {today}"

    resp = requests.post(
        "https://api.postmarkapp.com/email",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": token,
        },
        json={
            "From": from_email,
            "To": to,
            "Subject": subj,
            "HtmlBody": html,
            "MessageStream": "outbound",
        },
        timeout=15,
    )

    if resp.status_code == 200:
        data = resp.json()
        return {"ok": True, "message_id": data.get("MessageID", ""), "to": to}
    else:
        return {"ok": False, "error": f"Postmark {resp.status_code}: {resp.text[:200]}"}
