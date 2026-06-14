"""Unit tests for the historical IPO scraper — no network (monkeypatched)."""
from __future__ import annotations

import pytest

from utils import ipo_scraper


# ── parsing helpers ──────────────────────────────────────────────────────────

def test_parse_helpers():
    assert ipo_scraper._parse_float("$16.00") == 16.0
    assert ipo_scraper._parse_int("6,250,000") == 6_250_000
    assert ipo_scraper._parse_float(None) is None
    assert ipo_scraper._parse_nasdaq_date("3/28/2024") == "2024-03-28"
    assert ipo_scraper._parse_nasdaq_date("garbage") is None


def test_normalize_exchange():
    assert ipo_scraper._normalize_exchange("NASDAQ Global Select") == "NASDAQ"
    assert ipo_scraper._normalize_exchange("NMS") == "NASDAQ"
    assert ipo_scraper._normalize_exchange("NYQ") == "NYSE"
    assert ipo_scraper._normalize_exchange("NYSE American") == "AMEX"


def test_region_for_country():
    assert ipo_scraper.region_for_country("United States") == "Americas"
    assert ipo_scraper.region_for_country("Germany") == "EMEA"
    assert ipo_scraper.region_for_country("Japan") == "APAC"
    assert ipo_scraper.region_for_country("Atlantis") == "Other"


def test_is_spac():
    assert ipo_scraper._is_spac("Viking Acquisition Corp. II")
    assert not ipo_scraper._is_spac("NovaTech Solutions")


# ── NASDAQ row mapping ───────────────────────────────────────────────────────

def test_nasdaq_rows_to_records():
    rows = [{
        "proposedTickerSymbol": "BOLD", "companyName": "Boundless Bio, Inc.",
        "proposedExchange": "NASDAQ Global Select", "proposedSharePrice": "16.00",
        "sharesOffered": "6,250,000", "pricedDate": "3/28/2024",
        "dollarValueOfSharesOffered": "$100,000,000",
    }]
    recs = ipo_scraper._nasdaq_rows_to_records(rows, "priced")
    assert len(recs) == 1
    r = recs[0]
    assert r["ticker"] == "BOLD"
    assert r["exchange"] == "NASDAQ"
    assert r["ipo_price"] == 16.0
    assert r["ipo_date"] == "2024-03-28"
    assert r["deal_value"] == 100_000_000


# ── source fallback: NASDAQ fails -> stockanalysis used ──────────────────────

def test_fetch_ipo_calendar_falls_back(monkeypatch):
    def boom(year, session):
        raise RuntimeError("nasdaq down")

    def fake_sa(year, session=None):
        return [{"ticker": "ACME", "company_name": "Acme", "ipo_date": f"{year}-02-01",
                 "ipo_price": 10.0, "exchange": "NASDAQ", "price_change_since_ipo": 0.2,
                 "status": "priced"}]

    monkeypatch.setattr(ipo_scraper, "fetch_nasdaq_priced", boom)
    monkeypatch.setattr(ipo_scraper, "fetch_stockanalysis", fake_sa)
    recs = ipo_scraper.fetch_ipo_calendar(2024)
    assert recs and recs[0]["ticker"] == "ACME"


# ── enrichment with a fake yfinance ──────────────────────────────────────────

class _FakeHist:
    def __init__(self):
        import pandas as pd
        self._df = pd.DataFrame({"Close": [10.0, 18.0], "Volume": [100, 200]})

    def __len__(self):
        return len(self._df)

    def __getitem__(self, k):
        return self._df[k]


class _FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    @property
    def info(self):
        return {"sector": "Technology", "industry": "Software",
                "exchange": "NMS", "marketCap": 5_000_000_000}

    def history(self, period="1y"):
        return _FakeHist()


def test_enrich_with_yfinance(monkeypatch):
    import sys, types
    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = _FakeTicker
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    skeletons = [{"ticker": "ACME", "company_name": "Acme", "ipo_date": "2024-05-01",
                  "ipo_price": 10.0, "exchange": "NASDAQ"}]
    out = ipo_scraper.enrich_with_yfinance(skeletons, max_tickers=5, sleep=0)
    assert len(out) == 1
    rec = out[0]
    assert rec["sector"] == "Technology"
    assert rec["market_cap"] == 5_000_000_000
    assert rec["country"] == "United States"
    assert rec["region"] == "Americas"
    # perf recomputed from ipo_price (10) -> current (18) = +0.8
    assert rec["price_change_since_ipo"] == pytest.approx(0.8)
