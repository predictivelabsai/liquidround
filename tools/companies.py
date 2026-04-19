"""Company-lookup tools — wrap utils/yfinance_util as StructuredTools.

Consumed by:
  - company_profiler     (underwriting)
  - target_scanner       (sourcing)
  - buyer_scanner        (sourcing)
  - deal_triage          (sourcing)
  - comps_finder         (underwriting)
  - synergy_analyst      (underwriting)
"""
from __future__ import annotations

import json
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from utils.yfinance_util import yfinance_util
from tools.artifact import emit


# ────────────────────────────────────────────────────────────────────────
# get_company_profile
# ────────────────────────────────────────────────────────────────────────

class TickerArgs(BaseModel):
    ticker: str = Field(description="Exchange-qualified ticker (e.g. SAP.DE, NOVO-B.CO, AAPL, TAL1T.TL).")


def _get_company_profile(ticker: str) -> str:
    profile = yfinance_util.get_company_profile(ticker)
    if "error" in profile:
        return f"Lookup failed for {ticker}: {profile['error']}"

    fin = yfinance_util.get_financials(ticker)

    artifact_rows = [
        {"metric": "Sector",       "value": profile.get("sector") or "—"},
        {"metric": "Industry",     "value": profile.get("industry") or "—"},
        {"metric": "Country",      "value": profile.get("country") or "—"},
        {"metric": "Employees",    "value": profile.get("employees") or "—"},
        {"metric": "Market cap",   "value": _fmt_money(profile.get("market_cap"))},
        {"metric": "EV",           "value": _fmt_money(profile.get("enterprise_value"))},
        {"metric": "Revenue (LTM)","value": _fmt_money(fin.get("revenue"))},
        {"metric": "EBITDA (LTM)", "value": _fmt_money(fin.get("ebitda"))},
        {"metric": "EBITDA margin","value": _fmt_pct(fin.get("ebitda_margins"))},
        {"metric": "Revenue growth","value": _fmt_pct(fin.get("revenue_growth"))},
        {"metric": "EV / EBITDA",  "value": _fmt_num(fin.get("ev_to_ebitda"))},
    ]

    return emit(
        kind="table",
        title=f"{profile.get('name','?')} ({profile['ticker']})",
        subtitle=f"{profile.get('sector','')} · {profile.get('country','')}",
        columns=["metric", "value"],
        rows=artifact_rows,
        summary={"profile": profile, "financials": fin},
    )


get_company_profile = StructuredTool.from_function(
    func=_get_company_profile,
    name="get_company_profile",
    description=(
        "Fetch a listed company's profile from yfinance: business description, "
        "sector, country, market cap, EV, LTM revenue + EBITDA, and EV/EBITDA. "
        "Accepts exchange-qualified tickers (SAP.DE, NOVO-B.CO, AAPL, TAL1T.TL). "
        "Emits a table artifact."
    ),
    args_schema=TickerArgs,
)


# ────────────────────────────────────────────────────────────────────────
# get_financials
# ────────────────────────────────────────────────────────────────────────

def _get_financials(ticker: str) -> str:
    fin = yfinance_util.get_financials(ticker)
    if "error" in fin:
        return f"Lookup failed for {ticker}: {fin['error']}"
    return json.dumps(fin, default=str)


get_financials = StructuredTool.from_function(
    func=_get_financials,
    name="get_financials",
    description="Fetch LTM financials for a listed company: revenue, EBITDA, margins, growth, leverage, EV/EBITDA. Accepts exchange-qualified tickers.",
    args_schema=TickerArgs,
)


# ────────────────────────────────────────────────────────────────────────
# get_peer_companies (for comps finder)
# ────────────────────────────────────────────────────────────────────────

class PeersArgs(BaseModel):
    sector: str = Field(description="Yahoo sector name, e.g. 'Technology', 'Healthcare', 'Industrials'.")
    industry: Optional[str] = Field(default="", description="Optional narrower industry filter.")


def _get_peers(sector: str, industry: str = "") -> str:
    peers = yfinance_util.get_comparable_companies(sector, industry)
    if not peers:
        return f"No peer list available for sector={sector!r}."
    rows = [{"ticker": p["ticker"], "name": p["name"], "weight_%": round(100 * (p.get("weight") or 0), 2)} for p in peers]
    return emit(
        kind="table",
        title=f"Peers — {sector}",
        subtitle=f"Top {len(rows)} by index weight",
        columns=["ticker", "name", "weight_%"],
        rows=rows,
    )


get_peer_companies = StructuredTool.from_function(
    func=_get_peers,
    name="get_peer_companies",
    description="Return a peer set for a Yahoo sector (e.g. 'Technology') using the sector ETF's top holdings. Emits a table artifact.",
    args_schema=PeersArgs,
)


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────

def _fmt_money(n) -> str:
    if not n:
        return "—"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    for threshold, suffix in [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]:
        if abs(n) >= threshold:
            return f"${n/threshold:.1f}{suffix}"
    return f"${n:,.0f}"


def _fmt_pct(n) -> str:
    if n is None or n == "":
        return "—"
    try:
        return f"{float(n) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(n)


def _fmt_num(n) -> str:
    if n is None or n == "":
        return "—"
    try:
        return f"{float(n):.2f}x"
    except (TypeError, ValueError):
        return str(n)
