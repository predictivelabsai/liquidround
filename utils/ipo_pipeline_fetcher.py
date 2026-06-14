"""IPO Pipeline data — pre-IPO companies heading to public markets (US-focused).

Two streams feed ``liquidround.ipo_pipeline``:

1. **Private mega-caps** via Yahoo Finance ``.PVT`` tickers (OpenAI, Anthropic,
   Databricks, …). ``yf.Ticker("OPAI.PVT").info`` returns
   ``quoteType == "PRIVATE_COMPANY"`` with ``latestImpliedValuation``,
   ``latestShareClass``, ``latestFundingDate``, ``fundingToDate``,
   ``totalFundingRounds`` etc.
2. **Near-term IPOs** (upcoming / filed) from the NASDAQ calendar, via
   ``utils.ipo_scraper.fetch_nasdaq_pipeline``.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Curated US pre-IPO seed list. `name`/`sector` are fallbacks if yfinance is down.
PVT_SEED: List[Dict] = [
    {"pvt_ticker": "OPAI.PVT", "company_name": "OpenAI",        "sector": "Artificial Intelligence"},
    {"pvt_ticker": "ANTH.PVT", "company_name": "Anthropic",     "sector": "Artificial Intelligence"},
    {"pvt_ticker": "DATB.PVT", "company_name": "Databricks",    "sector": "Data & AI Infrastructure"},
    {"pvt_ticker": "GROQ.PVT", "company_name": "Groq",          "sector": "AI Hardware"},
    {"pvt_ticker": "ANIN.PVT", "company_name": "Anduril Industries", "sector": "Defense Technology"},
    {"pvt_ticker": "EPIR.PVT", "company_name": "Epirus",        "sector": "Defense Technology"},
    {"pvt_ticker": "AUAN.PVT", "company_name": "Automation Anywhere", "sector": "Software"},
    {"pvt_ticker": "APOL.PVT", "company_name": "Apollo.io",     "sector": "Software"},
    {"pvt_ticker": "SPAX.PVT",  "company_name": "SpaceX",       "sector": "Aerospace"},
    {"pvt_ticker": "STRI.PVT",  "company_name": "Stripe",       "sector": "Fintech"},
    {"pvt_ticker": "FANA.PVT",  "company_name": "Fanatics",     "sector": "Consumer / E-commerce"},
    {"pvt_ticker": "CHIM.PVT",  "company_name": "Chime",        "sector": "Fintech"},
    {"pvt_ticker": "FIGM.PVT",  "company_name": "Figma",        "sector": "Software"},
]


def _epoch_to_date(ts) -> Optional[str]:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
    except (ValueError, OSError, TypeError):
        return None


def _norm_country(c: Optional[str]) -> str:
    return "United States" if (c or "").upper() in ("US", "USA", "UNITED STATES") else (c or "United States")


def fetch_pvt_company(seed: Dict) -> Optional[Dict]:
    """Fetch one private company by `.PVT` ticker; fall back to seed metadata."""
    import yfinance as yf

    pvt = seed["pvt_ticker"]
    try:
        info = yf.Ticker(pvt).info or {}
    except Exception as e:  # noqa: BLE001
        logger.debug("yfinance .PVT failed for %s: %s", pvt, e)
        info = {}

    if info.get("quoteType") == "PRIVATE_COMPANY":
        return {
            "pipeline_key": f"pvt:{pvt}",
            "company_name": info.get("longName") or info.get("shortName") or seed["company_name"],
            "ticker": pvt,
            "kind": "private",
            "sector": info.get("sector") or seed.get("sector"),
            "industry": (info.get("industry") or "")[:300] or None,
            "country": _norm_country(info.get("country")),
            "last_valuation": info.get("latestImpliedValuation"),
            "last_round": info.get("latestShareClass"),
            "last_round_date": _epoch_to_date(info.get("latestFundingDate")),
            "last_amount_raised": info.get("latestAmountRaised"),
            "funding_to_date": info.get("fundingToDate"),
            "total_rounds": info.get("totalFundingRounds"),
            "employees": info.get("fullTimeEmployees"),
            "website": info.get("website"),
            "summary": (info.get("longBusinessSummary") or "")[:2000] or None,
            "status": "private",
            "source": "yfinance",
        }

    # fallback — keep the company visible even if Yahoo has no data
    logger.info("No .PVT data for %s; using seed fallback", pvt)
    return {
        "pipeline_key": f"pvt:{pvt}",
        "company_name": seed["company_name"],
        "ticker": pvt,
        "kind": "private",
        "sector": seed.get("sector"),
        "country": "United States",
        "status": "private",
        "source": "seed",
    }


def fetch_pvt_pipeline(sleep: float = 0.2) -> List[Dict]:
    out = []
    for seed in PVT_SEED:
        rec = fetch_pvt_company(seed)
        if rec:
            out.append(rec)
        time.sleep(sleep)
    return out


def fetch_upcoming_ipos(months: int = 4) -> List[Dict]:
    """Upcoming / filed US IPOs from the NASDAQ calendar (operating companies)."""
    from .ipo_scraper import fetch_nasdaq_pipeline

    out = []
    for rec in fetch_nasdaq_pipeline(months=months):
        out.append({
            "pipeline_key": f"nasdaq:{rec['ticker']}",
            "company_name": rec["company_name"],
            "ticker": rec["ticker"],
            "kind": rec.get("kind", "filed"),
            "exchange": rec.get("exchange"),
            "country": "United States",
            "proposed_price": rec.get("ipo_price"),
            "shares_offered": rec.get("shares_offered"),
            "deal_value": rec.get("deal_value"),
            "expected_date": rec.get("ipo_date"),
            "status": rec.get("kind", "filed"),
            "source": "nasdaq",
        })
    return out


def refresh_pipeline(include_upcoming: bool = True) -> int:
    """Refresh the whole pipeline (private + upcoming) and upsert to the DB."""
    from .database import db_service

    started = datetime.now().isoformat()
    records: List[Dict] = []
    try:
        records.extend(fetch_pvt_pipeline())
        if include_upcoming:
            records.extend(fetch_upcoming_ipos())
        n = db_service.upsert_pipeline_companies(records)
        db_service.log_ipo_refresh("IPO_PIPELINE_REFRESH", "SUCCESS", n, started_at=started)
        return n
    except Exception as e:  # noqa: BLE001
        logger.error("Pipeline refresh failed: %s", e)
        db_service.log_ipo_refresh("IPO_PIPELINE_REFRESH", "ERROR", 0,
                                   error_message=str(e), started_at=started)
        return 0
