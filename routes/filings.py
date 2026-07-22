"""SEC EDGAR Filings — search & browse page.

/app/filings               -> full page with search form
POST /app/filings/search    -> HTMX partial — search results table
GET  /app/filings/pdf       -> PDF export of current results
"""
from __future__ import annotations

import logging

from fasthtml.common import (
    APIRouter, Div, Span, H2, H3, P, A, Button, Input, Title, Script, NotStr,
    Form, Table, Thead, Tbody, Tr, Th, Td, Option, Select, Label,
)
from starlette.requests import Request
from starlette.responses import FileResponse

log = logging.getLogger(__name__)
ar = APIRouter()

_FORM_TYPES = [
    ("", "All types"),
    ("10-K", "10-K (Annual)"),
    ("10-Q", "10-Q (Quarterly)"),
    ("8-K", "8-K (Current events)"),
    ("DEF 14A", "DEF 14A (Proxy)"),
    ("S-1", "S-1 (Registration)"),
    ("4", "Form 4 (Insider)"),
]

BG_CARD, INK, MUTED, DIM, AMBER, LINE = "#111A2E", "#E5E7EB", "#94A3B8", "#64748B", "#F59E0B", "#1E293B"


def _search_form():
    """HTMX search form that POSTs to /app/filings/search."""
    form_options = [Option(label, value=val, selected=(val == "")) for val, label in _FORM_TYPES]
    return Form(
        Div(
            Div(
                Label("Search query", style=f"font-size:11px;color:{MUTED};display:block;margin-bottom:4px;"),
                Input(name="query", type="text", placeholder="e.g. material weakness, revenue recognition...",
                      style=f"width:100%;padding:8px 12px;background:#0D1526;border:1px solid {LINE};"
                            f"border-radius:6px;color:{INK};font-size:13px;"),
                style="flex:2 1 240px;",
            ),
            Div(
                Label("Ticker", style=f"font-size:11px;color:{MUTED};display:block;margin-bottom:4px;"),
                Input(name="ticker", type="text", placeholder="e.g. AAPL",
                      style=f"width:100%;padding:8px 12px;background:#0D1526;border:1px solid {LINE};"
                            f"border-radius:6px;color:{INK};font-size:13px;"),
                style="flex:0 1 120px;",
            ),
            Div(
                Label("Form type", style=f"font-size:11px;color:{MUTED};display:block;margin-bottom:4px;"),
                Select(*form_options, name="form_type",
                       style=f"width:100%;padding:8px 12px;background:#0D1526;border:1px solid {LINE};"
                             f"border-radius:6px;color:{INK};font-size:13px;"),
                style="flex:0 1 160px;",
            ),
            Div(
                Label("From", style=f"font-size:11px;color:{MUTED};display:block;margin-bottom:4px;"),
                Input(name="start_date", type="date",
                      style=f"width:100%;padding:8px 12px;background:#0D1526;border:1px solid {LINE};"
                            f"border-radius:6px;color:{INK};font-size:13px;"),
                style="flex:0 1 140px;",
            ),
            Div(
                Label("To", style=f"font-size:11px;color:{MUTED};display:block;margin-bottom:4px;"),
                Input(name="end_date", type="date",
                      style=f"width:100%;padding:8px 12px;background:#0D1526;border:1px solid {LINE};"
                            f"border-radius:6px;color:{INK};font-size:13px;"),
                style="flex:0 1 140px;",
            ),
            Div(
                Label(NotStr("&nbsp;"), style="font-size:11px;display:block;margin-bottom:4px;"),
                Button("Search", type="submit",
                       style=f"padding:8px 20px;background:{AMBER};color:#0B1220;font-weight:700;"
                             f"border:none;border-radius:6px;font-size:13px;cursor:pointer;"),
                style="flex:0 0 auto;",
            ),
            style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;",
        ),
        hx_post="/app/filings/search",
        hx_target="#filings-results",
        hx_swap="innerHTML",
        hx_indicator="#filings-spinner",
        style=f"background:{BG_CARD};border:1px solid {LINE};border-radius:12px;padding:20px;margin-bottom:20px;",
    )


def _empty_state():
    return Div(
        P("Search SEC filings by keyword, company ticker, or form type.",
          style=f"color:{MUTED};font-size:14px;text-align:center;padding:40px 20px;"),
        id="filings-results",
    )


def _results_table(results: list[dict], total: int = 0, company_name: str = "") -> Div:
    """Render filing results as an HTML table."""
    if not results:
        return Div(
            P("No filings found matching your criteria.",
              style=f"color:{MUTED};font-size:14px;text-align:center;padding:40px 20px;"),
        )

    subtitle = f"{company_name} — " if company_name else ""
    subtitle += f"{total:,} results" if total else f"{len(results)} results"

    rows = []
    for r in results:
        url = r.get("url") or r.get("file_url", "")
        rows.append(Tr(
            Td(r.get("filing_date", r.get("date", "")),
               style=f"padding:8px 12px;font-size:12px;color:{INK};white-space:nowrap;"),
            Td(Span(r.get("form_type", r.get("form", "")),
                     style=f"background:rgba(245,158,11,.15);color:{AMBER};padding:2px 8px;"
                           f"border-radius:4px;font-size:11px;font-weight:600;"),
               style="padding:8px 12px;"),
            Td(r.get("entity_name", r.get("company", "")),
               style=f"padding:8px 12px;font-size:12px;color:{INK};"),
            Td(r.get("description", "")[:60],
               style=f"padding:8px 12px;font-size:12px;color:{MUTED};"),
            Td(A("View", href=url, target="_blank",
                 style=f"color:{AMBER};font-size:12px;text-decoration:none;font-weight:600;") if url else "",
               style="padding:8px 12px;"),
            style=f"border-bottom:1px solid {LINE};",
        ))

    return Div(
        P(subtitle, style=f"color:{MUTED};font-size:12px;margin-bottom:12px;"),
        Div(
            Table(
                Thead(Tr(
                    Th("Date", style=f"padding:8px 12px;font-size:11px;color:{DIM};text-align:left;font-weight:600;"),
                    Th("Form", style=f"padding:8px 12px;font-size:11px;color:{DIM};text-align:left;font-weight:600;"),
                    Th("Company", style=f"padding:8px 12px;font-size:11px;color:{DIM};text-align:left;font-weight:600;"),
                    Th("Description", style=f"padding:8px 12px;font-size:11px;color:{DIM};text-align:left;font-weight:600;"),
                    Th("Link", style=f"padding:8px 12px;font-size:11px;color:{DIM};text-align:left;font-weight:600;"),
                    style=f"border-bottom:2px solid {LINE};",
                )),
                Tbody(*rows),
                style="width:100%;border-collapse:collapse;",
            ),
            style="overflow-x:auto;",
        ),
    )


def _page_content():
    return Div(
        _search_form(),
        Div(
            Span("Searching...", style=f"color:{MUTED};font-size:13px;"),
            id="filings-spinner",
            cls="htmx-indicator",
            style="text-align:center;padding:20px;",
        ),
        _empty_state(),
        style="padding:20px;max-width:1200px;margin:0 auto;",
    )


@ar("/app/filings")
def filings_page(session, request):
    from components.chat_shell import left_pane, right_pane

    user = session.get("user")
    email = user.get("email") if user else None
    sessions_list = []
    if user and user.get("user_id"):
        try:
            from utils.database import db_service
            convs = db_service.get_user_conversations(user["user_id"], limit=20) or []
            sessions_list = [{"id": c["id"],
                              "title": c.get("conversation_title") or c.get("user_query", "Untitled")}
                             for c in convs]
        except Exception:
            pass

    header = Div(
        Div(
            Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span("SEC Filings", cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span("Search & analyze EDGAR filings", cls="chat-header-agent"),
            cls="chat-header-left",
        ),
        Div(
            A("⬇ PDF", href="/app/filings/pdf",
              style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;"
                    "font-size:12px;font-weight:600;color:#F59E0B;"
                    "border:1px solid rgba(245,158,11,.4);border-radius:6px;"
                    "text-decoration:none;"),
            cls="chat-header-actions",
        ),
        cls="chat-header",
    )

    return (
        Title("SEC Filings · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(user_email=email, sessions=sessions_list, current_sid="",
                      current_path="/app/filings",
                      current_currency=session.get("currency", "EUR"),
                      current_role=session.get("role", "buyer")),
            Div(
                header,
                Div(_page_content(), cls="overflow-y-auto flex-1"),
                cls="center-pane",
            ),
            right_pane(),
            cls="app pane-closed",
        ),
        Script(src="/chat.js?v=2"),
    )


@ar("/app/filings/search", methods=["POST"])
async def filings_search(request: Request):
    """HTMX search endpoint — returns results table fragment."""
    form = await request.form()
    query = (form.get("query") or "").strip()
    ticker = (form.get("ticker") or "").strip()
    form_type = (form.get("form_type") or "").strip()
    start_date = (form.get("start_date") or "").strip()
    end_date = (form.get("end_date") or "").strip()

    if not query and not ticker:
        return Div(
            P("Enter a search query or ticker to search SEC filings.",
              style=f"color:{MUTED};font-size:14px;text-align:center;padding:40px 20px;"),
        )

    try:
        from utils.edgar import search_filings, get_company_filings

        # If ticker provided but no query, show company filing history
        if ticker and not query:
            result = get_company_filings(ticker=ticker, form_type=form_type, limit=20)
            if result.get("error"):
                return Div(P(result["error"],
                             style=f"color:#F87171;font-size:14px;text-align:center;padding:40px 20px;"))
            return _results_table(
                result.get("filings", []),
                total=len(result.get("filings", [])),
                company_name=result.get("company_name", ""),
            )

        # Full-text search
        result = search_filings(
            query=query, forms=form_type, ticker=ticker,
            start_date=start_date, end_date=end_date, limit=20,
        )
        return _results_table(
            result.get("results", []),
            total=result.get("total", 0),
        )
    except Exception as e:
        log.error("Filing search error: %s", e)
        return Div(P(f"Search error: {e}",
                     style=f"color:#F87171;font-size:14px;text-align:center;padding:40px 20px;"))


@ar("/app/filings/pdf")
async def filings_pdf():
    """Export a sample filing search as PDF."""
    from utils.page_pdf import build_pdf, pdf_filename, Section, Row

    sections = [
        Section("SEC EDGAR Filing Search",
                headers=["Feature", "Description"],
                rows=[
                    Row(["Full-text search", "Search across all SEC filing types by keyword"]),
                    Row(["Company filings", "Browse filing history by ticker symbol"]),
                    Row(["XBRL data", "Structured financial facts from 10-K/10-Q"]),
                    Row(["Filing text", "Read and analyze filing documents"]),
                ],
                text="Use the SEC Filings page to search and analyze EDGAR filings, "
                     "or chat with the Filing Analyst agent using the 'filings:' prefix."),
    ]
    path = build_pdf("SEC Filings", "EDGAR filing search and analysis", sections)
    fname = pdf_filename("SEC-Filings")
    return FileResponse(str(path), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})
