"""Sync SPAC data from NASDAQ calendar + yfinance enrichment.

Usage:
    python -m scripts.sync_spacs              # default: 6 months of NASDAQ calendar
    python -m scripts.sync_spacs --months 12  # look back further
    python -m scripts.sync_spacs --enrich     # also fetch yfinance prices (slower)
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "LiquidRound/1.0 (info@liquidround.com)")
SEC_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"


def fetch_spacs_from_nasdaq(months: int = 6) -> list[dict]:
    """Get SPACs from the NASDAQ IPO calendar (filed + upcoming + priced)."""
    from utils.ipo_scraper import fetch_nasdaq_pipeline, is_spac, scrape_ipos

    records = []

    # 1. Pipeline (upcoming/filed) — flip exclude_spacs to get only SPACs
    pipeline = fetch_nasdaq_pipeline(months=months, exclude_spacs=False)
    for rec in pipeline:
        if not is_spac(rec.get("company_name", "")):
            continue
        records.append({
            "spac_key": f"nasdaq:{rec['ticker']}",
            "ticker": rec["ticker"],
            "company_name": rec["company_name"],
            "status": "searching",
            "exchange": rec.get("exchange"),
            "ipo_date": rec.get("ipo_date"),
            "ipo_size": rec.get("deal_value"),
            "country": "United States",
            "source": "nasdaq",
        })

    # 2. Priced (historical) — last 3 years
    current_year = datetime.now().year
    for year in range(current_year - 2, current_year + 1):
        try:
            priced = scrape_ipos(year=year)
            for rec in priced:
                if not is_spac(rec.get("company_name", "")):
                    continue
                key = f"nasdaq:{rec['ticker']}"
                if any(r["spac_key"] == key for r in records):
                    continue
                records.append({
                    "spac_key": key,
                    "ticker": rec["ticker"],
                    "company_name": rec["company_name"],
                    "status": "completed" if rec.get("ipo_date") else "searching",
                    "exchange": rec.get("exchange"),
                    "ipo_date": rec.get("ipo_date"),
                    "country": rec.get("country", "United States"),
                    "source": "nasdaq",
                })
            time.sleep(0.3)
        except Exception:
            logger.warning("Failed to scrape priced SPACs for %d", year, exc_info=True)

    logger.info("Found %d SPACs from NASDAQ calendar", len(records))
    return records


def fetch_spacs_from_edgar(max_results: int = 200) -> list[dict]:
    """Search SEC EDGAR full-text search for SPAC-related S-1 filings."""
    import requests

    headers = {"User-Agent": SEC_USER_AGENT, "Accept": "application/json"}
    params = {
        "q": '"blank check" OR "special purpose acquisition"',
        "forms": "S-1,S-1/A",
        "dateRange": "custom",
        "startdt": f"{datetime.now().year - 3}-01-01",
        "enddt": datetime.now().strftime("%Y-%m-%d"),
    }

    records = []
    seen_ciks: set[str] = set()
    try:
        url = "https://efts.sec.gov/LATEST/search-index"
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        hits = r.json().get("hits", {}).get("hits", [])
        for hit in hits[:max_results]:
            src = hit.get("_source", {})
            cik = str(src.get("entity_id", ""))
            if not cik or cik in seen_ciks:
                continue
            seen_ciks.add(cik)
            name = src.get("display_names", [""])[0] if src.get("display_names") else src.get("entity_name", "")
            if not name:
                continue
            ticker = ""
            tickers = src.get("tickers", [])
            if tickers:
                ticker = tickers[0].split(":")[0] if ":" in tickers[0] else tickers[0]
            records.append({
                "spac_key": f"edgar:{cik}",
                "ticker": ticker or None,
                "company_name": name,
                "status": "searching",
                "country": "United States",
                "source": "edgar",
            })
        logger.info("Found %d SPACs from EDGAR search", len(records))
    except Exception:
        logger.warning("EDGAR SPAC search failed", exc_info=True)

    return records


def enrich_with_yfinance(records: list[dict], sleep: float = 0.2) -> list[dict]:
    """Add price, market cap, and warrant data from yfinance."""
    import yfinance as yf

    for rec in records:
        ticker = rec.get("ticker")
        if not ticker or ticker.endswith(".PVT"):
            continue
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            rec["current_price"] = info.get("currentPrice") or info.get("regularMarketPrice")
            rec["trust_size"] = info.get("totalCashPerShare") and int(
                (info.get("totalCashPerShare", 0)) * (info.get("sharesOutstanding", 0))
            ) or info.get("totalCash")
            mc = info.get("marketCap")
            if mc and not rec.get("ipo_size"):
                rec["ipo_size"] = mc
        except Exception:
            logger.debug("yfinance failed for %s", ticker)

        # Try warrant tickers
        for suffix in ("WS", "-WT", ".WS"):
            wt = f"{ticker}{suffix}"
            try:
                winfo = yf.Ticker(wt).info or {}
                if winfo.get("regularMarketPrice"):
                    rec["warrant_ticker"] = wt
                    rec["warrant_price"] = winfo["regularMarketPrice"]
                    break
            except Exception:
                continue

        # NAV premium calc
        price = rec.get("current_price")
        nav = rec.get("trust_per_share") or 10.0
        if price and nav:
            rec["nav_premium_pct"] = round((price - nav) / nav * 100, 2)

        time.sleep(sleep)

    return records


def main(months: int = 6, enrich: bool = False) -> dict:
    from utils.spac_db import upsert_spacs

    records = []

    # NASDAQ calendar
    nasdaq_spacs = fetch_spacs_from_nasdaq(months=months)
    records.extend(nasdaq_spacs)

    # SEC EDGAR
    edgar_spacs = fetch_spacs_from_edgar()
    existing_keys = {r["spac_key"] for r in records}
    for rec in edgar_spacs:
        if rec["spac_key"] not in existing_keys:
            records.append(rec)
            existing_keys.add(rec["spac_key"])

    if enrich:
        logger.info("Enriching %d SPACs with yfinance...", len(records))
        records = enrich_with_yfinance(records)

    n = upsert_spacs(records)
    logger.info("Upserted %d SPAC records", n)
    return {"total_found": len(records), "upserted": n}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Sync SPAC data from NASDAQ + EDGAR + yfinance")
    ap.add_argument("--months", type=int, default=6, help="Months of NASDAQ calendar to scan")
    ap.add_argument("--enrich", action="store_true", help="Enrich with yfinance prices (slower)")
    args = ap.parse_args()
    result = main(months=args.months, enrich=args.enrich)
    print(f"Done: {result}")
