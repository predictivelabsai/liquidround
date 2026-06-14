"""Real historical IPO scraper for the IPO Map.

Replaces the old hardcoded ticker list in ``utils.ipo_utils``. Multi-source and
resilient:

1. **NASDAQ IPO calendar API** (primary) — clean JSON, covers NASDAQ/NYSE/AMEX,
   gives both *priced* (historical) and *upcoming/filed* (pipeline) rows.
2. **stockanalysis.com** SvelteKit ``__data.json`` (fallback) — a single request
   per year returning every US IPO with its return since listing.

Both yield lightweight ``{ticker, company_name, ipo_date, ipo_price, exchange}``
skeletons which are then enriched with yfinance (sector / market cap / current
price / performance) and tagged with country + region.

US IPOs are the focus for now; the regional fields keep the treemap hierarchy
(Region -> Country -> Sector -> Ticker) working for when other markets are added.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

from .ipo_utils import get_country_from_exchange

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Country -> region (Americas / EMEA / APAC). US-focused; extend as needed.
REGION_BY_COUNTRY = {
    "United States": "Americas", "Canada": "Americas", "Brazil": "Americas",
    "Mexico": "Americas", "Argentina": "Americas", "Chile": "Americas",
    "United Kingdom": "EMEA", "Germany": "EMEA", "France": "EMEA",
    "Netherlands": "EMEA", "Italy": "EMEA", "Spain": "EMEA", "Switzerland": "EMEA",
    "Sweden": "EMEA", "Norway": "EMEA", "Denmark": "EMEA", "Finland": "EMEA",
    "Israel": "EMEA", "Ireland": "EMEA", "Poland": "EMEA",
    "China": "APAC", "Hong Kong": "APAC", "Japan": "APAC", "India": "APAC",
    "Singapore": "APAC", "South Korea": "APAC", "Australia": "APAC", "Taiwan": "APAC",
}


def region_for_country(country: Optional[str]) -> str:
    return REGION_BY_COUNTRY.get(country or "", "Other")


def _normalize_exchange(raw: str) -> str:
    """Map yfinance / NASDAQ exchange labels to a clean canonical code."""
    e = (raw or "").upper()
    if e in ("NMS", "NGM", "NCM") or "NASDAQ" in e:
        return "NASDAQ"
    if e in ("NYQ",) or ("NYSE" in e and "AMERICAN" not in e and "MKT" not in e):
        return "NYSE"
    if "AMERICAN" in e or e in ("ASE", "AMEX") or "NYSE MKT" in e:
        return "AMEX"
    return raw or "UNKNOWN"


# ── helpers for parsing NASDAQ string fields ──────────────────────────────

def _parse_float(s) -> Optional[float]:
    if s is None:
        return None
    try:
        return float(str(s).replace("$", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_int(s) -> Optional[int]:
    f = _parse_float(s)
    return int(f) if f is not None else None


def _parse_nasdaq_date(s) -> Optional[str]:
    """NASDAQ dates look like '3/28/2024' -> ISO 'YYYY-MM-DD'."""
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


# ── Source 1: NASDAQ IPO calendar ─────────────────────────────────────────

def _fetch_nasdaq_month(year: int, month: int, session: requests.Session) -> dict:
    url = f"https://api.nasdaq.com/api/ipo/calendar?date={year}-{month:02d}"
    r = session.get(url, headers=_HEADERS, timeout=20)
    r.raise_for_status()
    return (r.json() or {}).get("data") or {}


def _nasdaq_rows_to_records(rows: list, status: str) -> List[Dict]:
    out = []
    for row in rows or []:
        ticker = (row.get("proposedTickerSymbol") or "").strip().upper()
        if not ticker:
            continue
        out.append({
            "ticker": ticker,
            "company_name": (row.get("companyName") or ticker).strip(),
            "ipo_date": _parse_nasdaq_date(row.get("pricedDate") or row.get("expectedPriceDate")),
            "ipo_price": _parse_float(row.get("proposedSharePrice")),
            "exchange": _normalize_exchange(row.get("proposedExchange") or ""),
            "shares_offered": _parse_int(row.get("sharesOffered")),
            "deal_value": _parse_int(row.get("dollarValueOfSharesOffered")),
            "status": status,
        })
    return out


def fetch_nasdaq_priced(year: int, session: Optional[requests.Session] = None) -> List[Dict]:
    """Priced (completed) US IPOs for a calendar year, via the NASDAQ calendar."""
    sess = session or requests.Session()
    records: List[Dict] = []
    for month in range(1, 13):
        try:
            data = _fetch_nasdaq_month(year, month, sess)
            priced = (data.get("priced") or {})
            records.extend(_nasdaq_rows_to_records(priced.get("rows") or [], "priced"))
            time.sleep(0.15)
        except Exception as e:  # noqa: BLE001 — one bad month shouldn't abort the year
            logger.warning("NASDAQ calendar %s-%02d failed: %s", year, month, e)
    return records


_SPAC_MARKERS = ("acquisition corp", "acquisition co", "acquisition company",
                 "blank check", "spac")


def _is_spac(name: str) -> bool:
    n = (name or "").lower()
    return any(m in n for m in _SPAC_MARKERS)


def fetch_nasdaq_pipeline(months: int = 4, session: Optional[requests.Session] = None,
                          exclude_spacs: bool = True) -> List[Dict]:
    """Upcoming + filed US IPOs over the next ``months`` months.

    SPAC shells are dropped by default so the pipeline shows real operating
    companies heading to market.
    """
    sess = session or requests.Session()
    now = datetime.now()
    seen: dict[str, dict] = {}
    for i in range(months):
        y = now.year + (now.month - 1 + i) // 12
        m = (now.month - 1 + i) % 12 + 1
        try:
            data = _fetch_nasdaq_month(y, m, sess)
            for status_key, kind in (("upcoming", "upcoming"), ("filed", "filed")):
                block = data.get(status_key) or {}
                for rec in _nasdaq_rows_to_records(block.get("rows") or [], kind):
                    if exclude_spacs and _is_spac(rec["company_name"]):
                        continue
                    rec["kind"] = kind
                    seen[rec["ticker"]] = rec  # de-dupe by ticker
            time.sleep(0.15)
        except Exception as e:  # noqa: BLE001
            logger.warning("NASDAQ pipeline %s-%02d failed: %s", y, m, e)
    return list(seen.values())


# ── Source 2: stockanalysis.com (fallback) ────────────────────────────────

def fetch_stockanalysis(year: int, session: Optional[requests.Session] = None) -> List[Dict]:
    """Fallback bulk source. Parses SvelteKit's deduplicated ``devalue`` payload."""
    sess = session or requests.Session()
    url = f"https://stockanalysis.com/ipos/{year}/__data.json"
    r = sess.get(url, headers=_HEADERS, timeout=25)
    r.raise_for_status()
    nodes = (r.json() or {}).get("nodes") or []
    flat = None
    for n in nodes:
        d = n.get("data")
        if isinstance(d, list) and len(d) > 10:
            flat = d
    if not flat:
        return []

    def resolve(idx):
        v = flat[idx]
        if isinstance(v, dict):
            return {k: resolve(i) for k, i in v.items()}
        if isinstance(v, list):
            return [resolve(i) for i in v]
        return v

    root = flat[0]
    rows_idx = root.get("data") if isinstance(root, dict) else None
    rows = resolve(rows_idx) if isinstance(rows_idx, int) else []
    out = []
    for rec in rows or []:
        ticker = (rec.get("s") or "").strip().upper()
        if not ticker:
            continue
        ret = rec.get("ipr")  # return-since-IPO in percent
        out.append({
            "ticker": ticker,
            "company_name": (rec.get("n") or ticker).strip(),
            "ipo_date": rec.get("ipoDate"),
            "ipo_price": _parse_float(rec.get("ipoPrice")),
            "exchange": "NASDAQ",  # source doesn't expose exchange reliably
            "price_change_since_ipo": (ret / 100.0) if isinstance(ret, (int, float)) else None,
            "status": "priced",
        })
    return out


def fetch_ipo_calendar(year: int) -> List[Dict]:
    """Historical IPO skeletons for a year. NASDAQ primary, stockanalysis fallback."""
    sess = requests.Session()
    try:
        records = fetch_nasdaq_priced(year, sess)
        if records:
            logger.info("Fetched %d priced IPOs from NASDAQ for %s", len(records), year)
            return records
        logger.warning("NASDAQ returned no IPOs for %s; trying stockanalysis", year)
    except Exception as e:  # noqa: BLE001
        logger.warning("NASDAQ source failed for %s (%s); trying stockanalysis", year, e)
    try:
        records = fetch_stockanalysis(year, sess)
        logger.info("Fetched %d IPOs from stockanalysis for %s", len(records), year)
        return records
    except Exception as e:  # noqa: BLE001
        logger.error("All IPO calendar sources failed for %s: %s", year, e)
        return []


# ── yfinance enrichment ───────────────────────────────────────────────────

def enrich_with_yfinance(records: List[Dict], max_tickers: int = 80,
                         sleep: float = 0.2) -> List[Dict]:
    """Fill sector/industry/market_cap/current_price/volume/performance + region.

    Bounded by ``max_tickers`` (most recent first) so a manual refresh stays fast.
    Records that can't be enriched are still kept when they already carry a price
    and a return (e.g. from stockanalysis).
    """
    import yfinance as yf

    # most-recent first, capped
    records = sorted(records, key=lambda r: r.get("ipo_date") or "", reverse=True)
    capped = records[:max_tickers]
    if len(records) > max_tickers:
        logger.info("Enriching %d of %d IPOs (max_tickers cap)", max_tickers, len(records))

    out: List[Dict] = []
    now_iso = datetime.now().isoformat()
    for rec in capped:
        ticker = rec["ticker"]
        sector = industry = None
        market_cap = current_price = volume = None
        price_change = rec.get("price_change_since_ipo")
        exchange = rec.get("exchange") or "UNKNOWN"
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            hist = stock.history(period="1y")
            sector = info.get("sector")
            industry = info.get("industry")
            if info.get("exchange"):
                exchange = _normalize_exchange(info["exchange"])
            if len(hist):
                current_price = float(hist["Close"].iloc[-1])
                volume = int(hist["Volume"].iloc[-1])
            market_cap = info.get("marketCap") or 0
            if not market_cap and info.get("sharesOutstanding") and current_price:
                market_cap = int(info["sharesOutstanding"] * current_price)
            # recompute performance from scraped IPO price when possible
            if rec.get("ipo_price") and current_price:
                price_change = (current_price - rec["ipo_price"]) / rec["ipo_price"]
            time.sleep(sleep)
        except Exception as e:  # noqa: BLE001 — skip enrichment, keep record if usable
            logger.debug("yfinance enrich failed for %s: %s", ticker, e)

        if price_change is None and current_price is None:
            continue  # nothing to plot

        country = get_country_from_exchange(exchange)
        if country == "Unknown":
            country = "United States"  # US-focused sources
        out.append({
            "ticker": ticker,
            "company_name": rec.get("company_name") or ticker,
            "sector": sector or "Unknown",
            "industry": industry or "Unknown",
            "exchange": exchange,
            "country": country,
            "region": region_for_country(country),
            "ipo_date": rec.get("ipo_date"),
            "ipo_price": rec.get("ipo_price") or 0,
            "current_price": current_price or rec.get("ipo_price") or 0,
            "market_cap": int(market_cap or 0),
            "price_change_since_ipo": float(price_change or 0),
            "volume": int(volume or 0),
            "last_updated": now_iso,
        })
    return out


def scrape_ipos(year: int, max_tickers: int = 80) -> List[Dict]:
    """End-to-end: scrape a year's IPO calendar and enrich with yfinance."""
    skeletons = fetch_ipo_calendar(year)
    return enrich_with_yfinance(skeletons, max_tickers=max_tickers)
