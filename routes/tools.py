"""Public lead-magnet tool routes: /tools/comparables, /tools/match, /tools/valuation.

Also serves /industries/<slug> pages and /tools/lead for lead capture.
"""
from __future__ import annotations

import json
import logging
import os

from fasthtml.common import *
from fasthtml.core import APIRouter
from starlette.responses import JSONResponse

from utils.parse import parse_amount

from components.tools import (
    tool_page, tool_hero, url_input_step, loading_animation,
    comps_financial_form, comps_results,
    buyer_match_financial_form, buyer_results,
    valuation_financial_form, valuation_results,
    lead_capture_form, lead_success,
    company_profile_card,
    industry_hero, industry_description, industry_sub_sectors,
    industry_advisor_ctas, industry_find_buyers_widget, industry_faqs,
)
from components.landing import landing_page, BG, BG_ELEV, INK, INK_MUTED, CTA, LINE
from utils.i18n import get_lang

log = logging.getLogger(__name__)
ar = APIRouter()


# ───── Sector multiples loader ────────────────────────────────────────

_SECTOR_MAP = {
    "technology": "Software (System & Application)",
    "technology & saas": "Software (System & Application)",
    "software": "Software (System & Application)",
    "saas": "Software (System & Application)",
    "it services": "Computer Services",
    "healthcare": "Healthcare Products",
    "healthtech": "Heathcare Information and Technology",
    "manufacturing": "Machinery",
    "industrial": "Machinery",
    "business services": "Business & Consumer Services",
    "professional services": "Business & Consumer Services",
    "consulting": "Business & Consumer Services",
    "consumer": "Retail (General)",
    "e-commerce": "Retail (Online)",
    "retail": "Retail (General)",
    "financial services": "Financial Svcs. (Non-bank & Insurance)",
    "fintech": "Financial Svcs. (Non-bank & Insurance)",
    "energy": "Oil/Gas (Production and Exploration)",
    "real estate": "Real Estate (Development)",
    "food": "Food Processing",
    "food & beverage": "Food Processing",
    "construction": "Engineering/Construction",
    "education": "Education",
    "media": "Entertainment",
    "advertising": "Advertising",
    "telecom": "Telecom. Services",
    "automotive": "Auto & Truck",
    "pharmaceutical": "Drugs (Pharmaceutical)",
    "biotech": "Drugs (Biotechnology)",
    "other": "Business & Consumer Services",
}


def _get_sector_multiples(sector: str) -> dict:
    """Look up Damodaran multiples for a sector. Returns dict with ev_revenue, ev_ebitda, ev_ebit."""
    from valuation import _load_revenue_multiples, _load_ebitda_multiples

    rev_mults = _load_revenue_multiples()
    ebitda_mults = _load_ebitda_multiples()

    mapped = _SECTOR_MAP.get(sector.lower(), "")
    search_terms = [mapped.lower()] if mapped else []
    if sector and len(sector) > 3:
        search_terms.append(sector.lower())

    skip = {"total market", "total market (without financials)"}

    ev_revenue = 2.0
    for term in search_terms:
        for k, v in rev_mults.items():
            if k.lower() in skip:
                continue
            if term in k.lower() or k.lower() in term:
                ev_revenue = v
                break
        else:
            continue
        break

    ev_ebitda = 8.0
    ev_ebit = None
    for term in search_terms:
        for k, v in ebitda_mults.items():
            if k.lower() in skip:
                continue
            if term in k.lower() or k.lower() in term:
                if isinstance(v, dict):
                    ev_ebitda = v.get("ebitda", 8.0) or 8.0
                    ev_ebit = v.get("ebit")
                else:
                    ev_ebitda = v
                break
        else:
            continue
        break

    return {"ev_revenue": ev_revenue, "ev_ebitda": ev_ebitda, "ev_ebit": ev_ebit}


# ───── Comparables tool ──────────────────────────────────────────────

@ar("/tools/comparables")
def tools_comps(sess):
    lang = get_lang(sess)
    return tool_page(
        tool_hero(
            "Market Comparables",
            "See how your business compares to sector M&A benchmarks. Enter your company URL to get started."
        ),
        Div(
            url_input_step("comparables", "/tools/comparables/scrape"),
            id="tool-content",
            cls="max-w-3xl mx-auto px-6 pb-20",
        ),
        title="Market Comparables",
        lang=lang,
    )


@ar("/tools/comparables/scrape", methods=["POST"])
async def tools_comps_scrape(request):
    from utils.rate_limit import allow, client_key
    if not allow(client_key(request, "company-scrape")):
        return Div(P("Rate limit reached. Please try again later.", style="color:#EF4444"))
    form = await request.form()
    url = form.get("url", "").strip()
    if not url:
        return Div(P("Please enter a URL.", style="color:#EF4444"), url_input_step("comparables", "/tools/comparables/scrape"))

    from utils.company_scraper import scrape_company
    profile = await scrape_company(url)
    return comps_financial_form(profile.to_dict(), "/tools/comparables/results")


@ar("/tools/comparables/results", methods=["POST"])
async def tools_comps_results(request):
    form = await request.form()
    company_data = json.loads(form.get("company_data", "{}"))
    financials = {
        "revenue": parse_amount(form.get("revenue", 0)),
        "pretax_profit": parse_amount(form.get("pretax_profit", 0)),
        "owner_salary": parse_amount(form.get("owner_salary", 0)),
    }
    sector = company_data.get("sector") or "Technology"
    company_data["sector"] = sector
    sector_data = _get_sector_multiples(sector)
    return comps_results(company_data, financials, sector_data)


# ───── Find Buyers tool ──────────────────────────────────────────────

@ar("/tools/match")
def tools_match(sess):
    lang = get_lang(sess)
    return tool_page(
        tool_hero(
            "Find Buyers",
            "Discover potential acquirers for your business using our Baltic & European buyer database."
        ),
        Div(
            url_input_step("match", "/tools/match/scrape"),
            id="tool-content",
            cls="max-w-3xl mx-auto px-6 pb-20",
        ),
        title="Find Buyers",
        lang=lang,
    )


@ar("/tools/match/scrape", methods=["POST"])
async def tools_match_scrape(request):
    from utils.rate_limit import allow, client_key
    if not allow(client_key(request, "company-scrape")):
        return Div(P("Rate limit reached. Please try again later.", style="color:#EF4444"))
    form = await request.form()
    url = form.get("url", "").strip()
    if not url:
        return Div(P("Please enter a URL.", style="color:#EF4444"), url_input_step("match", "/tools/match/scrape"))

    from utils.company_scraper import scrape_company
    profile = await scrape_company(url)
    return buyer_match_financial_form(profile.to_dict(), "/tools/match/results")


@ar("/tools/match/results", methods=["POST"])
async def tools_match_results(request):
    form = await request.form()
    company_data = json.loads(form.get("company_data", "{}"))
    revenue_range = form.get("revenue_range", "1000000-5000000")
    profit_range = form.get("profit_range", "100000-500000")

    from utils.buyer_matcher import find_buyers
    buyers = await find_buyers(
        company_name=company_data.get("name", ""),
        sector=company_data.get("sector", "Technology"),
        sub_sector=company_data.get("sub_sector", ""),
        description=company_data.get("description", ""),
        count=5,
    )
    buyer_dicts = [b.to_dict() for b in buyers]
    return buyer_results(company_data, buyer_dicts, total_count=len(buyer_dicts))


# ───── Valuation tool ────────────────────────────────────────────────

@ar("/tools/valuation")
def tools_valuation(sess):
    lang = get_lang(sess)
    return tool_page(
        tool_hero(
            "Business Valuation",
            "Get an indicative valuation range based on sector benchmarks and your financials."
        ),
        Div(
            url_input_step("valuation", "/tools/valuation/scrape"),
            id="tool-content",
            cls="max-w-3xl mx-auto px-6 pb-20",
        ),
        title="Business Valuation",
        lang=lang,
    )


@ar("/tools/valuation/scrape", methods=["POST"])
async def tools_valuation_scrape(request):
    from utils.rate_limit import allow, client_key
    if not allow(client_key(request, "company-scrape")):
        return Div(P("Rate limit reached. Please try again later.", style="color:#EF4444"))
    form = await request.form()
    url = form.get("url", "").strip()
    if not url:
        return Div(P("Please enter a URL.", style="color:#EF4444"), url_input_step("valuation", "/tools/valuation/scrape"))

    from utils.company_scraper import scrape_company
    profile = await scrape_company(url)
    return valuation_financial_form(profile.to_dict(), "/tools/valuation/results")


@ar("/tools/valuation/results", methods=["POST"])
async def tools_valuation_results(request):
    form = await request.form()
    company_data = json.loads(form.get("company_data", "{}"))
    financials = {
        "revenue": parse_amount(form.get("revenue", 0)),
        "pretax_profit": parse_amount(form.get("pretax_profit", 0)),
        "owner_salary": parse_amount(form.get("owner_salary", 0)),
    }
    sector = company_data.get("sector") or "Technology"
    company_data["sector"] = sector
    sector_data = _get_sector_multiples(sector)

    value_drivers = await _generate_value_drivers(company_data)

    return valuation_results(company_data, financials, sector_data, value_drivers)


async def _generate_value_drivers(profile: dict) -> list[dict]:
    """Use LLM to generate value drivers based on company profile."""
    import asyncio
    from utils.llm_factory import create_llm

    prompt = f"""Analyze this company and identify value drivers for M&A valuation.

Company: {profile.get('name', '')}
Sector: {profile.get('sector', '')} / {profile.get('sub_sector', '')}
Description: {profile.get('description', '')}
Products: {', '.join(profile.get('products', []))}

Return valid JSON:
{{
  "drivers": [
    {{"label": "Strong recurring revenue model", "direction": "positive"}},
    {{"label": "Limited geographic diversification", "direction": "negative"}}
  ]
}}

Provide 3-4 positive and 2-3 negative drivers. Return JSON only."""

    try:
        llm = create_llm(temperature=0.3)
        resp = await asyncio.to_thread(lambda: llm.invoke(prompt).content)
        text = resp.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
        return data.get("drivers", [])
    except Exception as e:
        log.warning("Value driver generation failed: %s", e)
        return [
            {"label": "Established market position", "direction": "positive"},
            {"label": "Recurring revenue potential", "direction": "positive"},
            {"label": "Market-specific valuation data limited", "direction": "negative"},
        ]


# ───── Lead capture ──────────────────────────────────────────────────

@ar("/tools/lead", methods=["POST"])
async def tools_lead_capture(request):
    form = await request.form()
    full_name = form.get("full_name", "").strip()
    email = form.get("email", "").strip()
    phone = form.get("phone", "").strip()
    timeline = form.get("timeline", "")
    tool = form.get("tool", "")
    company_url = form.get("company_url", "")
    company_name = form.get("company_name", "")

    if not full_name or not email:
        return Div(P("Please provide your name and email.", style="color:#EF4444"))

    try:
        from utils.database import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO liquidround.leads
                       (full_name, email, phone, timeline, tool, company_url, company_name)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (full_name, email, phone, timeline, tool, company_url, company_name),
                )
    except Exception as e:
        log.warning("Failed to save lead: %s", e)

    try:
        from utils.email import send_email
        send_email(
            to=os.getenv("TO_EMAIL", "julian.kaljuvee@gmail.com"),
            subject=f"New lead from {tool} tool — {company_name or company_url}",
            html_body=(
                f"<h3>New Lead</h3>"
                f"<p><strong>Name:</strong> {full_name}</p>"
                f"<p><strong>Email:</strong> {email}</p>"
                f"<p><strong>Phone:</strong> {phone or 'N/A'}</p>"
                f"<p><strong>Timeline:</strong> {timeline or 'N/A'}</p>"
                f"<p><strong>Tool:</strong> {tool}</p>"
                f"<p><strong>Company:</strong> {company_name} ({company_url})</p>"
            ),
            tag="lead-capture",
        )
    except Exception as e:
        log.warning("Failed to send lead notification email: %s", e)

    return lead_success()


# ───── Industry pages ────────────────────────────────────────────────

@ar("/industries")
def industries_index(sess):
    lang = get_lang(sess)
    from data.industries import INDUSTRIES
    return tool_page(
        Div(
            Div(
                Span("◈ Industries", cls="mono text-xs tracking-widest mb-4 block", style=f"color:{CTA}"),
                H1("Industries We Serve",
                   cls="text-3xl sm:text-4xl md:text-5xl font-bold tightest mb-4",
                   style=f"color:{INK}"),
                P("Sector-specific M&A advisory across the Baltics and Nordics.",
                  cls="text-base", style=f"color:{INK_MUTED}"),
                cls="text-center max-w-3xl mx-auto",
            ),
            cls="px-6 pt-20 pb-8",
        ),
        Div(
            Div(
                *[A(
                    Div(
                        H3(ind["title"], cls="text-lg font-semibold tighter mb-2", style=f"color:{INK}"),
                        P(ind["description"][:120] + "…",
                          cls="text-xs leading-relaxed", style=f"color:{INK_MUTED}"),
                        Div(
                            *[Span(s["icon"] + " " + s["name"],
                                   cls="text-[10px] mr-2",
                                   style=f"color:{INK_MUTED}")
                              for s in ind["sub_sectors"][:3]],
                            cls="mt-3",
                        ),
                        cls="card rounded-lg p-6 h-full",
                    ),
                    href=f"/industries/{ind['slug']}",
                    cls="no-underline",
                ) for ind in INDUSTRIES],
                cls="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl mx-auto",
            ),
            cls="px-6 pb-20",
        ),
        title="Industries",
        lang=lang,
    )


@ar("/industries/{slug}")
def industry_page(slug: str, sess):
    lang = get_lang(sess)
    from data.industries import INDUSTRIES_BY_SLUG
    industry = INDUSTRIES_BY_SLUG.get(slug)
    if not industry:
        return tool_page(
            Div(P("Industry not found.", cls="text-center py-20", style=f"color:{INK_MUTED}")),
            title="Not Found",
            lang=lang,
        )
    return tool_page(
        industry_hero(industry),
        industry_description(industry),
        industry_sub_sectors(industry),
        industry_advisor_ctas(),
        industry_find_buyers_widget(),
        industry_faqs(industry),
        title=industry["title"],
        lang=lang,
    )
