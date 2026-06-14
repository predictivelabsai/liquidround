"""Unit tests for the .PVT pipeline fetcher — no network (monkeypatched)."""
from __future__ import annotations

import sys
import types

from utils import ipo_pipeline_fetcher as pf


def _install_fake_yf(monkeypatch, info_by_symbol: dict):
    class _FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        @property
        def info(self):
            return info_by_symbol.get(self.symbol, {})

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = _FakeTicker
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)


def test_epoch_to_date():
    # 1774915200 = 2026-03-31 UTC
    assert pf._epoch_to_date(1774915200) == "2026-03-31"
    assert pf._epoch_to_date(None) is None
    assert pf._epoch_to_date("bad") is None


def test_norm_country():
    assert pf._norm_country("US") == "United States"
    assert pf._norm_country("Germany") == "Germany"
    assert pf._norm_country(None) == "United States"


def test_fetch_pvt_company_maps_fields(monkeypatch):
    _install_fake_yf(monkeypatch, {
        "OPAI.PVT": {
            "quoteType": "PRIVATE_COMPANY", "longName": "OpenAI",
            "sector": "Artificial Intelligence", "industry": "AI",
            "country": "US", "latestImpliedValuation": 908_000_000_000,
            "latestShareClass": "Series C-NV", "latestFundingDate": 1774915200,
            "latestAmountRaised": 6_600_000_000, "fundingToDate": 178_000_000_000,
            "totalFundingRounds": 11, "fullTimeEmployees": 1001,
            "website": "https://openai.com", "longBusinessSummary": "AI lab.",
        },
    })
    rec = pf.fetch_pvt_company({"pvt_ticker": "OPAI.PVT", "company_name": "OpenAI"})
    assert rec["pipeline_key"] == "pvt:OPAI.PVT"
    assert rec["company_name"] == "OpenAI"
    assert rec["kind"] == "private"
    assert rec["last_valuation"] == 908_000_000_000
    assert rec["last_round"] == "Series C-NV"
    assert rec["last_round_date"] == "2026-03-31"
    assert rec["total_rounds"] == 11
    assert rec["country"] == "United States"
    assert rec["source"] == "yfinance"


def test_fetch_pvt_company_seed_fallback(monkeypatch):
    # yfinance returns a non-private quote -> fall back to seed
    _install_fake_yf(monkeypatch, {"XXX.PVT": {"quoteType": "EQUITY"}})
    rec = pf.fetch_pvt_company({"pvt_ticker": "XXX.PVT", "company_name": "Mystery Co",
                               "sector": "Software"})
    assert rec["source"] == "seed"
    assert rec["company_name"] == "Mystery Co"
    assert rec.get("last_valuation") is None  # not enriched on fallback


def test_fetch_upcoming_ipos(monkeypatch):
    monkeypatch.setattr(
        "utils.ipo_scraper.fetch_nasdaq_pipeline",
        lambda months=4: [{"ticker": "NEWCO", "company_name": "NewCo Inc", "kind": "filed",
                           "exchange": "NASDAQ", "ipo_price": 18.0, "shares_offered": 1_000_000,
                           "deal_value": 18_000_000, "ipo_date": "2026-07-01"}],
    )
    out = pf.fetch_upcoming_ipos()
    assert len(out) == 1
    r = out[0]
    assert r["pipeline_key"] == "nasdaq:NEWCO"
    assert r["kind"] == "filed"
    assert r["proposed_price"] == 18.0
    assert r["expected_date"] == "2026-07-01"
    assert r["source"] == "nasdaq"
