"""Hedge fund 13F tools — StructuredTool wrappers around utils/hedge_fund_db.

Consumed by the hedge_fund_analyst agent (public_markets category).
"""
from __future__ import annotations

from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from tools.artifact import emit


def _fmt_money(value) -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if abs(v) >= 1e12:
        return f"${v / 1e12:.2f}T"
    if abs(v) >= 1e9:
        return f"${v / 1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.2f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:.1f}K"
    return f"${v:,.0f}"


# ── get_market_overview ─────────────────────────────────────────────────

def _get_market_overview() -> str:
    from utils.hedge_fund_db import get_summary_stats
    stats = get_summary_stats()
    rows = [
        {"metric": "Total Funds", "value": f"{stats['total_funds']:,}"},
        {"metric": "Total Holdings", "value": f"{stats['total_holdings']:,}"},
        {"metric": "Total AUM", "value": _fmt_money(stats["total_aum"])},
        {"metric": "Unique Securities", "value": f"{stats['unique_securities']:,}"},
    ]
    return emit(
        kind="table",
        title="Hedge Fund Market Overview",
        subtitle="SEC Form 13F dataset",
        columns=["metric", "value"],
        rows=rows,
    )

get_market_overview = StructuredTool.from_function(
    func=_get_market_overview,
    name="get_market_overview",
    description="Return an overview of the SEC 13F dataset: total funds, holdings, AUM, unique securities. Emits a table artifact.",
)


# ── search_funds ────────────────────────────────────────────────────────

class SearchFundsArgs(BaseModel):
    query: str = Field(description="Fund name (partial match). E.g. 'Bridgewater', 'Citadel'.")
    limit: int = Field(default=15, description="Max results.")

def _search_funds(query: str, limit: int = 15) -> str:
    from utils.hedge_fund_db import search_funds
    results = search_funds(query, limit=limit)
    if not results:
        return f"No funds found matching '{query}'."
    rows = [
        {"fund": r["name"], "portfolio_value": _fmt_money(r["portfolio_value"]),
         "positions": str(r["positions"] or "—")}
        for r in results
    ]
    return emit(
        kind="table",
        title=f"Funds matching '{query}'",
        subtitle=f"{len(rows)} results",
        columns=["fund", "portfolio_value", "positions"],
        rows=rows,
    )

search_funds_tool = StructuredTool.from_function(
    func=_search_funds,
    name="search_funds",
    description="Search hedge funds by name (partial match). Returns fund name, portfolio value, and position count.",
    args_schema=SearchFundsArgs,
)


# ── get_top_funds ───────────────────────────────────────────────────────

class TopFundsArgs(BaseModel):
    top_n: int = Field(default=20, description="Number of top funds to return.")

def _get_top_funds(top_n: int = 20) -> str:
    from utils.hedge_fund_db import get_top_funds
    df = get_top_funds(top_n)
    if df.empty:
        return "No funds found."
    rows = [
        {"rank": str(i), "fund": r["Fund Name"],
         "portfolio_value": _fmt_money(r["Portfolio Value"]),
         "positions": str(int(r["Total Positions"]) if r["Total Positions"] else "—")}
        for i, (_, r) in enumerate(df.iterrows(), 1)
    ]
    return emit(
        kind="table",
        title=f"Top {len(rows)} Hedge Funds by AUM",
        subtitle="SEC Form 13F filings",
        columns=["rank", "fund", "portfolio_value", "positions"],
        rows=rows,
    )

get_top_funds_tool = StructuredTool.from_function(
    func=_get_top_funds,
    name="get_top_funds",
    description="Return the top N hedge funds ranked by portfolio value (AUM). Emits a table artifact.",
    args_schema=TopFundsArgs,
)


# ── get_fund_holdings ───────────────────────────────────────────────────

class FundHoldingsArgs(BaseModel):
    fund_name: str = Field(description="Exact or partial fund name. E.g. 'BERKSHIRE HATHAWAY'.")
    limit: int = Field(default=20, description="Max holdings to return.")

def _get_fund_holdings(fund_name: str, limit: int = 20) -> str:
    from utils.hedge_fund_db import get_fund_holdings, get_fund_names
    names = [n for n in get_fund_names() if fund_name.upper() in (n or "").upper()]
    resolved = names[0] if names else fund_name
    df = get_fund_holdings(resolved, limit=limit)
    if df.empty:
        return f"No holdings found for fund '{fund_name}' (resolved: '{resolved}')."
    rows = [
        {"rank": str(i), "security": r["NAMEOFISSUER"], "type": r["TITLEOFCLASS"],
         "value": _fmt_money(r["VALUE"]), "shares": f"{int(r['SSHPRNAMT']):,}",
         "pct": f"{float(r.get('portfolio_pct', 0)):.2f}%"}
        for i, (_, r) in enumerate(df.iterrows(), 1)
    ]
    return emit(
        kind="table",
        title=f"Holdings — {resolved}",
        subtitle=f"Top {len(rows)} positions",
        columns=["rank", "security", "type", "value", "shares", "pct"],
        rows=rows,
    )

get_fund_holdings_tool = StructuredTool.from_function(
    func=_get_fund_holdings,
    name="get_fund_holdings",
    description="Return top holdings for a named hedge fund. Fuzzy-matches the fund name. Emits a table artifact.",
    args_schema=FundHoldingsArgs,
)


# ── search_securities ───────────────────────────────────────────────────

class SearchSecuritiesArgs(BaseModel):
    query: str = Field(description="Security name or ticker to search. E.g. 'APPLE', 'NVDA'.")
    limit: int = Field(default=15, description="Max results.")

def _search_securities(query: str, limit: int = 15) -> str:
    from utils.hedge_fund_db import search_securities
    sec_df, fund_df = search_securities(query, limit=limit)
    if sec_df.empty:
        return f"No securities found matching '{query}'."
    rows = [
        {"security": r["Security"], "type": r["Type"],
         "total_value": _fmt_money(r["Total Value"]),
         "fund_count": str(int(r["Fund Count"]))}
        for _, r in sec_df.iterrows()
    ]
    result = emit(
        kind="table",
        title=f"Securities matching '{query}'",
        subtitle=f"{len(rows)} matches",
        columns=["security", "type", "total_value", "fund_count"],
        rows=rows,
    )
    if not fund_df.empty:
        fund_rows = [
            {"fund": r["Fund Name"], "position_value": _fmt_money(r["Position Value"]),
             "shares": f"{int(r['Shares Held']):,}"}
            for _, r in fund_df.head(limit).iterrows()
        ]
        result += "\n" + emit(
            kind="table",
            title="Funds holding this security",
            subtitle=f"Top {len(fund_rows)} holders",
            columns=["fund", "position_value", "shares"],
            rows=fund_rows,
        )
    return result

search_securities_tool = StructuredTool.from_function(
    func=_search_securities,
    name="search_securities",
    description="Search which hedge funds hold a security by name/ticker. Returns aggregated positions and top holders.",
    args_schema=SearchSecuritiesArgs,
)


# ── get_popular_securities ──────────────────────────────────────────────

class PopularSecuritiesArgs(BaseModel):
    top_n: int = Field(default=20, description="Number of top securities to return.")

def _get_popular_securities(top_n: int = 20) -> str:
    from utils.hedge_fund_db import get_popular_securities
    df = get_popular_securities(top_n)
    if df.empty:
        return "No securities found."
    rows = [
        {"rank": str(i), "security": r["Security"], "type": r["Type"],
         "total_value": _fmt_money(r["Total Value"]),
         "fund_count": str(int(r["Fund Count"]))}
        for i, (_, r) in enumerate(df.iterrows(), 1)
    ]
    return emit(
        kind="table",
        title=f"Top {len(rows)} Most Popular Securities",
        subtitle="By total value across all funds",
        columns=["rank", "security", "type", "total_value", "fund_count"],
        rows=rows,
    )

get_popular_securities_tool = StructuredTool.from_function(
    func=_get_popular_securities,
    name="get_popular_securities",
    description="Return the most popular securities held across all hedge funds, ranked by total value. Emits a table artifact.",
    args_schema=PopularSecuritiesArgs,
)


# ── get_fund_concentration ──────────────────────────────────────────────

class FundConcentrationArgs(BaseModel):
    top_n: int = Field(default=15, description="Number of top funds.")

def _get_fund_concentration(top_n: int = 15) -> str:
    from utils.hedge_fund_db import get_fund_concentration
    df = get_fund_concentration(top_n)
    if df.empty:
        return "No concentration data."
    rows = [
        {"rank": str(i), "fund": r["FILINGMANAGER_NAME"],
         "portfolio_value": _fmt_money(r["TABLEVALUETOTAL"]),
         "positions": str(int(r["TABLEENTRYTOTAL"]) if r["TABLEENTRYTOTAL"] else "—")}
        for i, (_, r) in enumerate(df.iterrows(), 1)
    ]
    return emit(
        kind="table",
        title=f"Market Concentration — Top {len(rows)} Funds",
        subtitle="Portfolio value share",
        columns=["rank", "fund", "portfolio_value", "positions"],
        rows=rows,
    )

get_fund_concentration_tool = StructuredTool.from_function(
    func=_get_fund_concentration,
    name="get_fund_concentration",
    description="Show market concentration — the largest funds by portfolio value to illustrate AUM distribution.",
    args_schema=FundConcentrationArgs,
)


# ── get_recent_activist_filings ─────────────────────────────────────────

class ActivistFilingsArgs(BaseModel):
    days: int = Field(default=30, description="Look-back period in calendar days.")
    limit: int = Field(default=25, description="Max filings to return.")

def _get_recent_activist_filings(days: int = 30, limit: int = 25) -> str:
    from utils.hedge_fund_db import recent_activist_filings, activist_stats
    filings = recent_activist_filings(days=days, limit=limit, activist_only=False)
    stats = activist_stats(days=days)
    if not filings:
        return f"No activist filings (13D/13G) in the last {days} days."
    rows = [
        {"date": r["filing_date"].isoformat() if r["filing_date"] else "",
         "form": r["form_type"], "filer": (r["filer_name"] or "?")[:50],
         "link": r["filing_url"] or ""}
        for r in filings
    ]
    subtitle = (f"Last {days} days — 13D: {stats['cnt_13d']}+{stats['cnt_13d_a']}A, "
                f"13G: {stats['cnt_13g']}+{stats['cnt_13g_a']}A, "
                f"{stats['unique_filers']} unique filers")
    return emit(
        kind="table",
        title="Recent Activist / Beneficial-Ownership Filings",
        subtitle=subtitle,
        columns=["date", "form", "filer", "link"],
        rows=rows,
    )

get_recent_activist_filings_tool = StructuredTool.from_function(
    func=_get_recent_activist_filings,
    name="get_recent_activist_filings",
    description="Return recent SEC Schedule 13D/13G filings — activist and beneficial-ownership reports for >5% stakes.",
    args_schema=ActivistFilingsArgs,
)


# ── All tools list ──────────────────────────────────────────────────────

HEDGE_FUND_TOOLS = [
    get_market_overview,
    search_funds_tool,
    get_top_funds_tool,
    get_fund_holdings_tool,
    search_securities_tool,
    get_popular_securities_tool,
    get_fund_concentration_tool,
    get_recent_activist_filings_tool,
]
