"""Tools for the Reverse Merger Analyst."""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from tools.artifact import emit


class SearchArgs(BaseModel):
    query: str = Field(default="", description="Company, target, ticker, structure, or jurisdiction")
    include_spacs: bool = Field(default=True, description="Include SPAC/de-SPAC comparison records")


def _search(query: str = "", include_spacs: bool = True) -> str:
    from utils.reverse_mergers import combined_market_rows
    rows = combined_market_rows()
    if not include_spacs:
        rows = [r for r in rows if "spac" not in r.get("transaction_type", "")]
    if query:
        q = query.lower()
        rows = [r for r in rows if q in " ".join(str(v) for v in r.values()).lower()]
    data = [{
        "date": str(r.get("announcement_date") or "")[:10],
        "market": r.get("jurisdiction"),
        "structure": r.get("transaction_type"),
        "public_vehicle": r.get("public_company"),
        "target": r.get("private_target") or "—",
        "status": r.get("status"),
        "source": r.get("source_url") or "",
    } for r in rows[:40]]
    if not data:
        return "No matching stored reverse-merger records. Use the workspace EDGAR sync or add a reviewed Canadian record."
    return emit(kind="table", title="Reverse Merger & SPAC Monitor",
                subtitle=f"{len(data)} matching records",
                columns=["date", "market", "structure", "public_vehicle", "target", "status", "source"],
                rows=data)


search_reverse_mergers_tool = StructuredTool.from_function(
    func=_search, name="search_reverse_mergers",
    description="Search LiquidRound's three-year reverse-merger, RTO, CPC and SPAC comparison dataset.",
    args_schema=SearchArgs,
)


class FilingArgs(BaseModel):
    query: str = Field(description="EDGAR full-text query")
    ticker: str = Field(default="", description="Optional public-company ticker")


def _search_edgar(query: str, ticker: str = "") -> str:
    from utils.edgar import search_filings
    result = search_filings(query, forms="8-K,S-4,DEF 14A", ticker=ticker, limit=20)
    rows = [{"date": r["filing_date"], "form": r["form_type"],
             "company": r["entity_name"], "source": r["file_url"]}
            for r in result.get("results", [])]
    return emit(kind="table", title=f"EDGAR reverse-merger evidence: {query}",
                subtitle=f"{result.get('total', 0):,} indexed matches",
                columns=["date", "form", "company", "source"], rows=rows)


search_reverse_merger_filings_tool = StructuredTool.from_function(
    func=_search_edgar, name="search_reverse_merger_edgar_filings",
    description="Search SEC EDGAR for reverse-merger evidence including shell status, control changes and acquisition filings.",
    args_schema=FilingArgs,
)

REVERSE_MERGER_TOOLS = [search_reverse_mergers_tool, search_reverse_merger_filings_tool]
