"""SEC EDGAR API client — full-text search, company filings, XBRL facts.

Rate limit: 10 req/s per SEC policy. We target 8 req/s with backoff.
All endpoints are free, no API key required — just a User-Agent header.
"""
from __future__ import annotations

import logging
import os
import time
import json
from functools import lru_cache
from typing import Optional
from urllib.parse import urlencode

import requests

log = logging.getLogger(__name__)

USER_AGENT = os.getenv("SEC_USER_AGENT", "LiquidRound/1.0 (info@liquidround.com)")
_RATE_INTERVAL = 0.125  # 8 req/s
_last_request = 0.0

def _throttle():
    global _last_request
    now = time.monotonic()
    wait = _RATE_INTERVAL - (now - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()

def _get(url: str, **kwargs) -> requests.Response:
    _throttle()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    headers.update(kwargs.pop("headers", {}))
    r = requests.get(url, headers=headers, timeout=30, **kwargs)
    r.raise_for_status()
    return r

# CIK <-> ticker mapping
@lru_cache(maxsize=1)
def _ticker_to_cik_map() -> dict[str, str]:
    """Load SEC's ticker->CIK mapping. Cached in process."""
    r = _get("https://www.sec.gov/files/company_tickers.json")
    data = r.json()
    mapping = {}
    for entry in data.values():
        ticker = entry.get("ticker", "").upper()
        cik = str(entry.get("cik_str", "")).zfill(10)
        if ticker:
            mapping[ticker] = cik
    return mapping

def ticker_to_cik(ticker: str) -> Optional[str]:
    m = _ticker_to_cik_map()
    return m.get(ticker.upper().strip())

def cik_to_padded(cik: str) -> str:
    return str(cik).zfill(10)

# Full-text search (EFTS)
def search_filings(query: str, forms: str = "", ticker: str = "",
                   start_date: str = "", end_date: str = "",
                   limit: int = 20) -> dict:
    """Search EDGAR full-text search index."""
    params = {"q": query, "from": 0, "size": min(limit, 40)}
    if forms:
        params["forms"] = forms
    if ticker:
        cik = ticker_to_cik(ticker)
        if cik:
            params["ciks"] = cik
    if start_date:
        params["dateRange"] = "custom"
        params["startdt"] = start_date
    if end_date:
        params["dateRange"] = "custom"
        params["enddt"] = end_date
    r = _get(f"https://efts.sec.gov/LATEST/search-index?{urlencode(params)}")
    data = r.json()
    hits = data.get("hits", {})
    total = hits.get("total", {}).get("value", 0)
    results = []
    for h in hits.get("hits", []):
        src = h.get("_source", {})
        results.append({
            "form_type": src.get("form_type", ""),
            "entity_name": src.get("entity_name", ""),
            "filing_date": src.get("file_date", ""),
            "accession_number": src.get("file_num", ""),
            "description": src.get("display_names", [""])[0] if src.get("display_names") else "",
            "file_url": f"https://www.sec.gov/Archives/edgar/data/{src.get('ciks', [''])[0]}/{src.get('adsh', '').replace('-', '')}/{src.get('file_name', '')}",
        })
    return {"total": total, "results": results}


# Company submissions (filing history)
def get_company_filings(ticker: str, form_type: str = "", limit: int = 20) -> dict:
    """Get filing history for a company by ticker."""
    cik = ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Ticker '{ticker}' not found in SEC database", "filings": []}
    r = _get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    data = r.json()
    company_name = data.get("name", "")
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    filings = []
    for i in range(len(forms)):
        if form_type and forms[i] != form_type:
            continue
        acc_clean = accessions[i].replace("-", "")
        filings.append({
            "form_type": forms[i],
            "filing_date": dates[i],
            "accession_number": accessions[i],
            "description": descriptions[i] if i < len(descriptions) else "",
            "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{primary_docs[i]}",
        })
        if len(filings) >= limit:
            break
    return {"company_name": company_name, "cik": cik, "filings": filings}


# XBRL financial facts
def get_financial_facts(ticker: str) -> dict:
    """Get structured XBRL financial data for a company."""
    cik = ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Ticker '{ticker}' not found"}
    r = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
    data = r.json()
    company_name = data.get("entityName", "")

    us_gaap = data.get("facts", {}).get("us-gaap", {})
    key_metrics = {}
    for tag in ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "NetIncomeLoss", "Assets", "StockholdersEquity",
                "EarningsPerShareBasic", "OperatingIncomeLoss"]:
        if tag in us_gaap:
            units = us_gaap[tag].get("units", {})
            usd_data = units.get("USD", units.get("USD/shares", []))
            if usd_data:
                recent = [d for d in usd_data if d.get("form") in ("10-K", "10-Q")]
                recent.sort(key=lambda x: x.get("end", ""), reverse=True)
                key_metrics[tag] = recent[:8]
    return {"company_name": company_name, "cik": cik, "metrics": key_metrics}


# Fetch filing document text
def get_filing_text(url: str, max_chars: int = 50000) -> str:
    """Download an SEC filing and extract plain text (truncated)."""
    import re
    from html import unescape
    r = _get(url, headers={"Accept": "text/html"})
    html = r.text
    # Strip HTML tags, decode entities
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'(&nbsp;|\xa0)+', ' ', text)
    return text[:max_chars]
