"""SEC EDGAR filing tools for the filing analyst agent."""
from __future__ import annotations

import json
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from tools.artifact import emit


class SearchFilingsArgs(BaseModel):
    query: str = Field(description="Search query (supports boolean: AND, OR, NOT, exact phrases in quotes)")
    forms: str = Field(default="", description="Comma-separated form types to filter: 10-K, 10-Q, 8-K, DEF 14A, S-1, etc.")
    ticker: str = Field(default="", description="Company ticker to filter results (e.g. AAPL, MSFT)")
    start_date: str = Field(default="", description="Start date YYYY-MM-DD")
    end_date: str = Field(default="", description="End date YYYY-MM-DD")


def _search_filings(query: str, forms: str = "", ticker: str = "",
                    start_date: str = "", end_date: str = "") -> str:
    from utils.edgar import search_filings
    result = search_filings(query=query, forms=forms, ticker=ticker,
                           start_date=start_date, end_date=end_date, limit=20)
    if not result.get("results"):
        return f"No SEC filings found for query: {query}"
    rows = [
        {"date": r["filing_date"], "form": r["form_type"],
         "company": r["entity_name"][:40], "description": r["description"][:60],
         "url": r["file_url"]}
        for r in result["results"]
    ]
    return emit(
        kind="table",
        title=f"SEC Filing Search: {query[:50]}",
        subtitle=f"{result['total']:,} total results",
        columns=["date", "form", "company", "description", "url"],
        rows=rows,
    )

search_filings_tool = StructuredTool.from_function(
    func=_search_filings,
    name="search_sec_filings",
    description="Search SEC EDGAR full-text index across all filing types. Use for finding specific topics in filings (e.g. 'material weakness', 'revenue recognition', 'goodwill impairment').",
    args_schema=SearchFilingsArgs,
)


class CompanyFilingsArgs(BaseModel):
    ticker: str = Field(description="Company ticker symbol (e.g. AAPL, MSFT)")
    form_type: str = Field(default="", description="Filter by form type: 10-K, 10-Q, 8-K, DEF 14A, etc.")


def _get_company_filings(ticker: str, form_type: str = "") -> str:
    from utils.edgar import get_company_filings
    result = get_company_filings(ticker=ticker, form_type=form_type, limit=20)
    if result.get("error"):
        return result["error"]
    if not result.get("filings"):
        return f"No filings found for {ticker}"
    rows = [
        {"date": f["filing_date"], "form": f["form_type"],
         "description": f["description"][:60], "url": f["url"]}
        for f in result["filings"]
    ]
    return emit(
        kind="table",
        title=f"{result['company_name']} — SEC Filings",
        subtitle=f"CIK: {result['cik']}",
        columns=["date", "form", "description", "url"],
        rows=rows,
    )

get_company_filings_tool = StructuredTool.from_function(
    func=_get_company_filings,
    name="get_company_sec_filings",
    description="Get the filing history for a company by ticker — 10-K, 10-Q, 8-K, proxy statements, etc.",
    args_schema=CompanyFilingsArgs,
)


class FilingTextArgs(BaseModel):
    url: str = Field(description="URL of the SEC filing document to read")
    question: str = Field(default="", description="Specific question to focus the analysis on (optional)")


def _get_filing_text(url: str, question: str = "") -> str:
    from utils.edgar import get_filing_text
    text = get_filing_text(url, max_chars=50000)
    if not text:
        return "Could not retrieve filing text."
    preview = text[:2000]
    return f"Filing text ({len(text):,} chars):\n\n{preview}\n\n[... truncated — full text available for analysis ...]"

get_filing_text_tool = StructuredTool.from_function(
    func=_get_filing_text,
    name="read_sec_filing",
    description="Download and read the text of a specific SEC filing by URL. Returns plain text extracted from the HTML filing document.",
    args_schema=FilingTextArgs,
)


class FinancialFactsArgs(BaseModel):
    ticker: str = Field(description="Company ticker symbol (e.g. AAPL, MSFT)")


def _get_financial_facts(ticker: str) -> str:
    from utils.edgar import get_financial_facts
    result = get_financial_facts(ticker=ticker)
    if result.get("error"):
        return result["error"]
    if not result.get("metrics"):
        return f"No XBRL financial data found for {ticker}"

    lines = [f"**{result['company_name']}** — XBRL Financial Facts\n"]
    for tag, periods in result["metrics"].items():
        label = tag.replace("FromContractWithCustomerExcludingAssessedTax", "")
        lines.append(f"\n**{label}:**")
        for p in periods[:4]:
            val = p.get("val", 0)
            end = p.get("end", "?")
            form = p.get("form", "?")
            if abs(val) >= 1e9:
                formatted = f"${val/1e9:.1f}B"
            elif abs(val) >= 1e6:
                formatted = f"${val/1e6:.0f}M"
            else:
                formatted = f"${val:,.0f}"
            lines.append(f"  {end} ({form}): {formatted}")

    return "\n".join(lines)

get_financial_facts_tool = StructuredTool.from_function(
    func=_get_financial_facts,
    name="get_xbrl_financial_facts",
    description="Get structured XBRL financial data (revenue, net income, assets, EPS) for a company from SEC filings. Returns historical values across reporting periods.",
    args_schema=FinancialFactsArgs,
)

FILING_TOOLS = [
    search_filings_tool,
    get_company_filings_tool,
    get_filing_text_tool,
    get_financial_facts_tool,
]
