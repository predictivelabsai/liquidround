"""Daily Deals Scanner — queries the company database and fresh M&A news,
compiles into an HTML digest email.

Used by scripts/daily_deals.py and the /app/deals/send-test route.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)

DB_SCHEMA = os.getenv("COMPANY_DB_SCHEMA", "pehero")
BASE_URL = os.getenv("SERVICE_URL_LIQUIDROUND", "https://liquidround.com")


def scan_top_companies(limit: int = 10) -> list[dict]:
    """Pull top companies by EBITDA margin from the database.

    Computes margin from actual revenue/ebitda values, filters out
    sentinel values (999) and implausible margins (>90% or <1%).
    Only includes companies with revenue > €1M for relevance.
    """
    from utils.database import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT name, slug, hq_city, country, sector, sub_sector, "
                f"revenue_ltm, ebitda_ltm, "
                f"ROUND((ebitda_ltm::numeric / NULLIF(revenue_ltm, 0) * 100)::numeric, 1) AS ebitda_margin, "
                f"growth_rate, enterprise_value, ask_multiple, employees, description "
                f"FROM {DB_SCHEMA}.companies "
                f"WHERE revenue_ltm > 1000000 AND ebitda_ltm > 0 "
                f"  AND ebitda_ltm <= revenue_ltm "
                f"  AND (ebitda_margin IS NULL OR ebitda_margin < 900) "
                f"ORDER BY (ebitda_ltm::numeric / NULLIF(revenue_ltm, 0)) DESC NULLS LAST "
                f"LIMIT %s",
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def scan_recent_additions(limit: int = 5) -> list[dict]:
    """Pull most recently added companies."""
    from utils.database import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT name, slug, hq_city, country, sector, sub_sector, "
                f"revenue_ltm, ebitda_ltm, "
                f"ROUND((ebitda_ltm::numeric / NULLIF(revenue_ltm, 0) * 100)::numeric, 1) AS ebitda_margin, "
                f"growth_rate, enterprise_value, ask_multiple, employees, description "
                f"FROM {DB_SCHEMA}.companies "
                f"WHERE revenue_ltm > 0 "
                f"ORDER BY created_at DESC NULLS LAST "
                f"LIMIT %s",
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def fetch_ma_news(num_results: int = 8) -> list[dict]:
    """Fetch fresh M&A / ECM news via Tavily."""
    try:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            log.warning("TAVILY_API_KEY not set, skipping news")
            return []
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        resp = client.search(
            query="M&A deals acquisitions IPO ECM investment banking today",
            search_depth="basic",
            max_results=num_results,
        )
        items = []
        for r in resp.get("results", [])[:num_results]:
            items.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": (r.get("content") or "")[:200],
            })
        return items
    except Exception as e:
        log.warning(f"Tavily news fetch failed: {e}")
        return []


def _fmt_money(n) -> str:
    if not n:
        return "—"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    if abs(n) >= 1e9:
        return f"€{n/1e9:.1f}B"
    if abs(n) >= 1e6:
        return f"€{n/1e6:.1f}M"
    if abs(n) >= 1e3:
        return f"€{n/1e3:.0f}K"
    return f"€{n:,.0f}"


def build_digest_html(
    companies: list[dict],
    news: list[dict],
    recent: list[dict] | None = None,
) -> str:
    """Render the daily deals digest as an HTML email."""
    today = datetime.now().strftime("%A, %B %d, %Y")

    company_rows = ""
    for c in companies:
        sector = (c.get("sector") or "").replace("_", " ").title()
        margin = float(c["ebitda_margin"]) if c.get("ebitda_margin") else 0
        growth = float(c["growth_rate"]) if c.get("growth_rate") else 0
        multiple = float(c["ask_multiple"]) if c.get("ask_multiple") else 0
        slug = c.get("slug") or ""
        detail_url = f"{BASE_URL}/app/company/{slug}" if slug else "#"
        company_rows += f"""
        <tr>
            <td style="padding:8px 12px; border-bottom:1px solid #1E293B;">
                <a href="{detail_url}" style="color:#F59E0B; text-decoration:none; font-weight:600;">{c['name']}</a><br>
                <span style="font-size:12px; color:#94A3B8;">{c.get('hq_city') or ''} · {sector}</span>
            </td>
            <td style="padding:8px 12px; border-bottom:1px solid #1E293B; text-align:right; font-family:'Courier New',monospace;">
                {_fmt_money(c.get('revenue_ltm'))}
            </td>
            <td style="padding:8px 12px; border-bottom:1px solid #1E293B; text-align:right; font-family:'Courier New',monospace;">
                {_fmt_money(c.get('ebitda_ltm'))}
            </td>
            <td style="padding:8px 12px; border-bottom:1px solid #1E293B; text-align:right; font-family:'Courier New',monospace;">
                {margin:.1f}%
            </td>
            <td style="padding:8px 12px; border-bottom:1px solid #1E293B; text-align:right; font-family:'Courier New',monospace;">
                {growth:+.1f}%
            </td>
            <td style="padding:8px 12px; border-bottom:1px solid #1E293B; text-align:right; font-family:'Courier New',monospace;">
                {multiple:.1f}x
            </td>
        </tr>"""

    news_items = ""
    for n in news:
        news_items += f"""
        <tr>
            <td style="padding:10px 12px; border-bottom:1px solid #1E293B;">
                <a href="{n['url']}" style="color:#F59E0B; text-decoration:none; font-weight:600;">
                    {n['title']}
                </a><br>
                <span style="font-size:12px; color:#94A3B8; line-height:1.4;">
                    {n['snippet']}
                </span>
            </td>
        </tr>"""

    recent_section = ""
    if recent:
        recent_items = ""
        for c in recent:
            sector = (c.get("sector") or "").replace("_", " ").title()
            slug = c.get("slug") or ""
            detail_url = f"{BASE_URL}/app/company/{slug}" if slug else "#"
            recent_items += f"""
            <tr>
                <td style="padding:6px 12px; border-bottom:1px solid #1E293B;">
                    <a href="{detail_url}" style="color:#FBBF24; text-decoration:none; font-weight:600;">{c['name']}</a>
                    <span style="color:#64748B; font-size:12px;"> · {c.get('hq_city') or ''} · {sector} · {_fmt_money(c.get('revenue_ltm'))} rev</span>
                </td>
            </tr>"""
        recent_section = f"""
        <div style="margin-top:28px;">
            <h2 style="color:#E5E7EB; font-size:16px; font-weight:600; margin:0 0 12px; border-bottom:2px solid #F59E0B; padding-bottom:6px;">
                Recently Added
            </h2>
            <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px; color:#E5E7EB;">
                {recent_items}
            </table>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0; padding:0; background:#0B1220; font-family:'Inter','Helvetica Neue',Arial,sans-serif;">
<div style="max-width:680px; margin:0 auto; padding:24px 16px;">

    <!-- Header -->
    <div style="text-align:center; padding:20px 0 24px;">
        <span style="color:#F59E0B; font-size:24px;">◆</span>
        <h1 style="color:#E5E7EB; font-size:22px; font-weight:600; margin:4px 0 0; letter-spacing:-0.02em;">
            LiquidRound <span style="color:#F59E0B;">Daily Deals</span>
        </h1>
        <p style="color:#64748B; font-size:13px; margin:6px 0 0;">{today}</p>
    </div>

    <!-- Top Companies -->
    <div style="background:#111A2E; border:1px solid #1E293B; border-radius:8px; padding:16px; margin-bottom:20px;">
        <h2 style="color:#E5E7EB; font-size:16px; font-weight:600; margin:0 0 12px; border-bottom:2px solid #F59E0B; padding-bottom:6px;">
            Top Deal Opportunities
        </h2>
        <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px; color:#E5E7EB;">
            <thead>
                <tr style="color:#64748B; font-size:11px; text-transform:uppercase; letter-spacing:0.08em;">
                    <th style="padding:6px 12px; text-align:left;">Company</th>
                    <th style="padding:6px 12px; text-align:right;">Revenue</th>
                    <th style="padding:6px 12px; text-align:right;">EBITDA</th>
                    <th style="padding:6px 12px; text-align:right;">Margin</th>
                    <th style="padding:6px 12px; text-align:right;">Growth</th>
                    <th style="padding:6px 12px; text-align:right;">Multiple</th>
                </tr>
            </thead>
            <tbody>
                {company_rows}
            </tbody>
        </table>
    </div>

    <!-- M&A News -->
    <div style="background:#111A2E; border:1px solid #1E293B; border-radius:8px; padding:16px; margin-bottom:20px;">
        <h2 style="color:#E5E7EB; font-size:16px; font-weight:600; margin:0 0 12px; border-bottom:2px solid #F59E0B; padding-bottom:6px;">
            M&A / ECM News
        </h2>
        <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px; color:#E5E7EB;">
            <tbody>
                {news_items if news_items else '<tr><td style="padding:10px 12px; color:#64748B;">No fresh news available.</td></tr>'}
            </tbody>
        </table>
    </div>

    {recent_section}

    <!-- Footer -->
    <div style="text-align:center; padding:20px 0; border-top:1px solid #1E293B; margin-top:12px;">
        <p style="color:#64748B; font-size:11px; margin:0;">
            <a href="https://liquidround.com/app" style="color:#F59E0B; text-decoration:none;">Open LiquidRound</a>
            &nbsp;·&nbsp;
            <span style="color:#475569;">Predictive Labs Ltd</span>
        </p>
    </div>

</div>
</body>
</html>"""


def build_digest_text(companies: list[dict], news: list[dict]) -> str:
    """Plain-text fallback."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    lines = [f"LiquidRound Daily Deals — {today}", "=" * 40, ""]

    lines.append("TOP DEAL OPPORTUNITIES")
    lines.append("-" * 40)
    for c in companies:
        sector = (c.get("sector") or "").replace("_", " ").title()
        lines.append(
            f"  {c['name']} ({c.get('hq_city') or ''}, {sector})"
            f"  Rev: {_fmt_money(c.get('revenue_ltm'))} | EBITDA: {_fmt_money(c.get('ebitda_ltm'))}"
        )
    lines.append("")

    lines.append("M&A / ECM NEWS")
    lines.append("-" * 40)
    for n in news:
        lines.append(f"  {n['title']}")
        lines.append(f"  {n['url']}")
        lines.append("")

    lines.append("---")
    lines.append("https://liquidround.com/app")
    return "\n".join(lines)
