"""
yfinance wrapper for company profiles, financials, and comparables.
"""
import yfinance as yf
from typing import Optional


class YFinanceUtil:
    """Company data via yfinance (profiles, market cap, fundamentals)."""

    def get_company_profile(self, ticker: str) -> dict:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            return {
                "ticker": ticker.upper(),
                "name": info.get("longName") or info.get("shortName", ticker),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "description": (info.get("longBusinessSummary") or "")[:600],
                "market_cap": info.get("marketCap", 0),
                "enterprise_value": info.get("enterpriseValue", 0),
                "employees": info.get("fullTimeEmployees", 0),
                "website": info.get("website", ""),
                "country": info.get("country", ""),
                "city": info.get("city", ""),
            }
        except Exception as e:
            return {"ticker": ticker.upper(), "error": str(e)}

    def get_financials(self, ticker: str) -> dict:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            return {
                "ticker": ticker.upper(),
                "revenue": info.get("totalRevenue", 0),
                "ebitda": info.get("ebitda", 0),
                "net_income": info.get("netIncomeToCommon", 0),
                "gross_margins": info.get("grossMargins", 0),
                "ebitda_margins": info.get("ebitdaMargins", 0),
                "profit_margins": info.get("profitMargins", 0),
                "revenue_growth": info.get("revenueGrowth", 0),
                "debt_to_equity": info.get("debtToEquity", 0),
                "free_cashflow": info.get("freeCashflow", 0),
                "pe_ratio": info.get("trailingPE", 0),
                "ev_to_ebitda": info.get("enterpriseToEbitda", 0),
            }
        except Exception as e:
            return {"ticker": ticker.upper(), "error": str(e)}

    def search_companies(self, query: str) -> list:
        """Search tickers/companies. yfinance doesn't have a search API so we try direct ticker lookup."""
        results = []
        for candidate in [query.upper(), query.upper().replace(" ", "")]:
            try:
                t = yf.Ticker(candidate)
                info = t.info or {}
                if info.get("longName") or info.get("shortName"):
                    results.append({
                        "ticker": candidate,
                        "name": info.get("longName") or info.get("shortName", ""),
                        "sector": info.get("sector", ""),
                        "market_cap": info.get("marketCap", 0),
                    })
            except Exception:
                pass
        return results

    def get_comparable_companies(self, sector: str, industry: str) -> list:
        """Return sector ETF holdings as proxy for comparable companies."""
        sector_etfs = {
            "Technology": "XLK", "Healthcare": "XLV", "Financial Services": "XLF",
            "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP", "Energy": "XLE",
            "Utilities": "XLU", "Basic Materials": "XLB", "Industrials": "XLI",
            "Real Estate": "XLRE", "Communication Services": "XLC",
        }
        etf_ticker = sector_etfs.get(sector)
        if not etf_ticker:
            return []
        try:
            etf = yf.Ticker(etf_ticker)
            holdings = etf.info.get("holdings", [])
            return [{"ticker": h.get("symbol", ""), "name": h.get("holdingName", ""), "weight": h.get("holdingPercent", 0)} for h in holdings[:15]]
        except Exception:
            return []


yfinance_util = YFinanceUtil()
