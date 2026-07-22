"""Press release tools for the press release analyst agent."""
from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from tools.artifact import emit


class SearchPRArgs(BaseModel):
    query: str = Field(default="", description="Search text in title/content")
    ticker: str = Field(default="", description="Company ticker symbol")
    event_type: str = Field(default="", description="Event type filter: earnings_releases_and_operating_results, mergers_acquisitions, management_changes, clinical_study, partnerships, etc.")
    days: int = Field(default=30, description="Look-back period in days")


def _search_press_releases(query: str = "", ticker: str = "", event_type: str = "", days: int = 30) -> str:
    from utils.press_releases import search_press_releases
    results = search_press_releases(query=query, ticker=ticker, event_type=event_type, days=days, limit=25)
    if not results:
        return "No press releases found matching your criteria."
    rows = [
        {"date": r["published_date"].strftime("%Y-%m-%d") if r["published_date"] else "",
         "company": (r["company"] or "")[:30],
         "ticker": r["yf_ticker"] or r["ticker"] or "",
         "title": (r["display_title"] or "")[:80],
         "event": (r["event"] or "").replace("_", " ")[:30],
         "source": (r["publisher"] or "")[:25]}
        for r in results
    ]
    return emit(
        kind="table",
        title="Press Releases",
        subtitle=f"{len(results)} releases found (last {days} days)",
        columns=["date", "company", "ticker", "title", "event", "source"],
        rows=rows,
    )

search_press_releases_tool = StructuredTool.from_function(
    func=_search_press_releases,
    name="search_press_releases",
    description="Search press releases from GlobeNewswire, PR Newswire, Nasdaq Nordic/Baltic, and Euronext. Filter by keyword, ticker, event type, or time period.",
    args_schema=SearchPRArgs,
)


class ReadPRArgs(BaseModel):
    news_id: int = Field(description="ID of the press release to read")


def _read_press_release(news_id: int) -> str:
    from utils.press_releases import get_press_release
    r = get_press_release(news_id)
    if not r:
        return f"Press release #{news_id} not found."
    content = r.get("full_content") or ""
    title = r.get("display_title") or r.get("title") or ""
    company = r.get("company") or ""
    date = r["published_date"].strftime("%Y-%m-%d %H:%M") if r.get("published_date") else ""
    prediction = ""
    if r.get("predicted_side"):
        prediction = f"\n\nML Prediction: {r['predicted_side']} ({r.get('predicted_move', 0):.1f}%)"
    reason = f"\n\nAnalysis: {r['reason']}" if r.get("reason") else ""

    return f"**{title}**\n{company} · {date} · {r.get('publisher', '')}\n\n{content[:5000]}{prediction}{reason}"

read_press_release_tool = StructuredTool.from_function(
    func=_read_press_release,
    name="read_press_release",
    description="Read the full text of a specific press release by its ID.",
    args_schema=ReadPRArgs,
)


class AnalyzePRArgs(BaseModel):
    sql_query: str = Field(description="SQL SELECT query to run against the public.news table. Available columns: id, title, company, yf_ticker, ticker, published_date, event, publisher, industry, content, predicted_side, predicted_move, reason, language")


def _analyze_press_releases(sql_query: str) -> str:
    from utils.press_releases import text_to_sql_query
    results = text_to_sql_query(sql_query)
    if not results:
        return "Query returned no results."
    if results[0].get("error"):
        return results[0]["error"]
    cols = list(results[0].keys())
    rows = [{c: str(r.get(c, ""))[:50] for c in cols} for r in results]
    return emit(
        kind="table",
        title="Press Release Analysis",
        subtitle=f"{len(results)} rows",
        columns=cols,
        rows=rows,
    )

analyze_press_releases_tool = StructuredTool.from_function(
    func=_analyze_press_releases,
    name="analyze_press_releases",
    description="Run a SQL query against the press releases database for custom analysis. Use SELECT queries on public.news table. Good for aggregations (count by event type, top companies, trends over time).",
    args_schema=AnalyzePRArgs,
)

PRESS_RELEASE_TOOLS = [
    search_press_releases_tool,
    read_press_release_tool,
    analyze_press_releases_tool,
]
