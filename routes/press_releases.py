"""Press Releases — searchable page for 390K+ releases from GlobeNewswire,
Euronext, Nasdaq Nordic/Baltic, and PR Newswire.

/app/press-releases               -> full page
POST /app/press-releases/search   -> HTMX partial results
GET  /app/press-releases/<id>     -> single release detail
GET  /app/press-releases/pdf      -> PDF export
"""
from __future__ import annotations

import logging

from fasthtml.common import (
    APIRouter, Div, Span, H2, H3, P, A, Button, Title, Script, NotStr,
    Form, Input, Select, Option, Style,
)
from starlette.requests import Request

from utils.press_releases import (
    search_press_releases,
    get_press_release,
    get_event_types,
    press_release_stats,
)

log = logging.getLogger(__name__)
ar = APIRouter()

# Publisher choices for the dropdown
_PUBLISHER_CHOICES = [
    ("", "All Sources"),
    ("globenewswire", "GlobeNewswire"),
    ("euronext", "Euronext"),
    ("omx", "OMX Nordic"),
    ("baltics", "Baltics"),
    ("prnewswire", "PR Newswire"),
]


def _event_label(event: str) -> str:
    """Human-readable event type label."""
    return (event or "").replace("_", " ").title()


def _pr_card(r: dict) -> Div:
    """Render a single press release card."""
    title = r.get("display_title") or r.get("title") or "Untitled"
    company = r.get("company") or ""
    ticker = r.get("yf_ticker") or r.get("ticker") or ""
    event = r.get("event") or ""
    publisher = r.get("publisher") or ""
    snippet = r.get("snippet") or ""
    date_str = ""
    if r.get("published_date"):
        try:
            date_str = r["published_date"].strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_str = str(r["published_date"])[:16]

    # ML prediction badge
    pred_badge = ""
    if r.get("predicted_side"):
        side = r["predicted_side"].upper()
        move = r.get("predicted_move") or 0
        if side == "UP":
            pred_badge = Span(f"UP +{move:.1f}%", cls="pr-badge pr-badge-up")
        elif side == "DOWN":
            pred_badge = Span(f"DOWN {move:.1f}%", cls="pr-badge pr-badge-down")

    # Event badge
    event_badge = Span(_event_label(event), cls="pr-badge pr-badge-event") if event else ""

    # Ticker badge
    ticker_badge = Span(ticker, style="background:#1E293B;color:#94A3B8;display:inline-block;"
                        "padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;"
                        "margin-right:6px;") if ticker else ""

    return Div(
        Div(
            A(title, href=f"/app/press-releases/{r.get('id', 0)}",
              hx_get=f"/app/press-releases/{r.get('id', 0)}",
              hx_target="#pr-detail-modal",
              hx_swap="innerHTML",
              cls="pr-title", style="text-decoration:none;cursor:pointer;"),
        ),
        Div(
            ticker_badge,
            Span(company, style="color:#94A3B8;font-size:12px;margin-right:8px;") if company else "",
            Span(date_str, style="color:#64748B;font-size:11px;margin-right:8px;"),
            Span(publisher, style="color:#64748B;font-size:11px;"),
            cls="pr-meta",
        ),
        Div(
            event_badge,
            pred_badge,
            style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;",
        ) if (event or pred_badge) else "",
        P(snippet, cls="pr-snippet") if snippet else "",
        cls="pr-card",
    )


def _stats_bar(stats: dict, days: int) -> Div:
    """Summary stats row at the top."""
    def _stat(label, value):
        return Div(
            Span(f"{value:,}" if isinstance(value, (int, float)) else str(value),
                 style="font-size:20px;font-weight:700;color:#F1F5F9;"),
            Span(label, style="font-size:11px;color:#64748B;margin-top:2px;"),
            style="display:flex;flex-direction:column;align-items:center;",
        )

    return Div(
        _stat("Releases", stats.get("total", 0)),
        _stat("Companies", stats.get("companies", 0)),
        _stat("Sources", stats.get("sources", 0)),
        _stat("M&A", stats.get("ma_count", 0)),
        _stat("Earnings", stats.get("earnings_count", 0)),
        style="display:flex;gap:32px;justify-content:center;padding:16px 0;margin-bottom:16px;"
              "border-bottom:1px solid #1E293B;",
    )


def _search_form(event_types: list[str]) -> Form:
    """HTMX search form for press releases."""
    event_options = [Option("All Events", value="")]
    for et in event_types:
        event_options.append(Option(_event_label(et), value=et))

    publisher_options = [Option(label, value=val) for val, label in _PUBLISHER_CHOICES]

    days_options = [
        Option("7 days", value="7"),
        Option("30 days", value="30", selected=True),
        Option("90 days", value="90"),
        Option("1 year", value="365"),
    ]

    input_style = ("background:#111A2E;border:1px solid #1E293B;border-radius:6px;"
                   "padding:8px 12px;color:#F1F5F9;font-size:13px;width:100%;")
    select_style = ("background:#111A2E;border:1px solid #1E293B;border-radius:6px;"
                    "padding:8px 12px;color:#F1F5F9;font-size:13px;width:100%;")

    return Form(
        Div(
            Input(name="query", placeholder="Search headlines & content...",
                  style=input_style, type="text"),
            Input(name="ticker", placeholder="Ticker (e.g. AAPL, NOVO-B.CO)",
                  style=input_style, type="text"),
            Select(*event_options, name="event_type", style=select_style),
            Select(*publisher_options, name="publisher", style=select_style),
            Select(*days_options, name="days", style=select_style),
            Button("Search",
                   type="submit",
                   style="background:#F59E0B;color:#0B1220;border:none;border-radius:6px;"
                         "padding:8px 20px;font-size:13px;font-weight:600;cursor:pointer;"
                         "white-space:nowrap;"),
            style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;",
        ),
        hx_post="/app/press-releases/search",
        hx_target="#pr-results",
        hx_swap="innerHTML",
        style="margin-bottom:16px;",
    )


def _render_results(releases: list[dict], days: int) -> Div:
    """Render the press release results list."""
    if not releases:
        return Div(
            P("No press releases found matching your criteria.",
              style="color:#64748B;text-align:center;padding:40px 0;font-size:14px;"),
            id="pr-results",
        )
    cards = [_pr_card(r) for r in releases]
    return Div(
        P(f"{len(releases)} releases found (last {days} days)",
          style="color:#64748B;font-size:12px;margin-bottom:12px;"),
        *cards,
        id="pr-results",
    )


_PR_CSS = """
.pr-card { background: #111A2E; border: 1px solid #1E293B; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.pr-title { color: #F1F5F9; font-weight: 600; font-size: 14px; }
.pr-title:hover { color: #F59E0B; }
.pr-meta { color: #94A3B8; font-size: 12px; margin-top: 4px; }
.pr-snippet { color: #CBD5E1; font-size: 13px; margin-top: 8px; line-height: 1.5; }
.pr-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.pr-badge-event { background: #1E3A5F; color: #60A5FA; }
.pr-badge-up { background: #064E3B; color: #34D399; }
.pr-badge-down { background: #7F1D1D; color: #FCA5A5; }
.pr-detail { background: #111A2E; border: 1px solid #1E293B; border-radius: 8px; padding: 24px; margin-top: 16px; }
.pr-detail-title { color: #F1F5F9; font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.pr-detail-meta { color: #94A3B8; font-size: 12px; margin-bottom: 16px; }
.pr-detail-content { color: #CBD5E1; font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
"""


@ar("/app/press-releases")
def press_releases_page(session, request: Request):
    from components.chat_shell import left_pane, right_pane

    user = session.get("user")
    email = user.get("email") if user else None
    sessions_list = []
    if user and user.get("user_id"):
        try:
            from utils.database import db_service
            convs = db_service.get_user_conversations(user["user_id"], limit=20) or []
            sessions_list = [{"id": c["id"], "title": c.get("conversation_title") or c.get("user_query", "Untitled")}
                             for c in convs]
        except Exception:
            pass

    # Load initial data
    try:
        stats = press_release_stats(days=30)
    except Exception:
        stats = {"total": 0, "companies": 0, "sources": 0, "ma_count": 0, "earnings_count": 0}

    try:
        event_types = get_event_types()
    except Exception:
        event_types = []

    try:
        releases = search_press_releases(days=30, limit=50)
    except Exception:
        releases = []

    header = Div(
        Div(
            Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span("Press Releases", cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span("390K+ releases from GlobeNewswire, Euronext, Nasdaq Nordic/Baltic",
                 cls="chat-header-agent"),
            cls="chat-header-left",
        ),
        Div(
            A("⬇ PDF", href="/app/press-releases/pdf",
              style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;"
                    "font-size:12px;font-weight:600;color:#F59E0B;"
                    "border:1px solid rgba(245,158,11,.4);border-radius:6px;"
                    "text-decoration:none;"),
            cls="chat-header-actions",
        ),
        cls="chat-header",
    )

    content = Div(
        _stats_bar(stats, 30),
        _search_form(event_types),
        _render_results(releases, 30),
        Div(id="pr-detail-modal"),
        style="padding:16px 24px;max-width:960px;margin:0 auto;",
    )

    return (
        Title("Press Releases · LiquidRound"),
        Style(_PR_CSS),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(user_email=email, sessions=sessions_list, current_sid="",
                      current_path="/app/press-releases",
                      current_currency=session.get("currency", "EUR"),
                      current_role=session.get("role", "buyer")),
            Div(
                header,
                Div(content, cls="overflow-y-auto flex-1"),
                cls="center-pane",
            ),
            right_pane(),
            cls="app pane-closed",
        ),
        Script(src="/chat.js?v=2"),
    )


@ar("/app/press-releases/search", methods=["POST"])
async def press_releases_search(request: Request):
    """HTMX search endpoint — returns result cards."""
    form = await request.form()
    query = form.get("query", "")
    ticker = form.get("ticker", "")
    event_type = form.get("event_type", "")
    publisher = form.get("publisher", "")
    days = int(form.get("days", "30"))

    try:
        releases = search_press_releases(
            query=query, ticker=ticker, event_type=event_type,
            publisher=publisher, days=days, limit=50,
        )
    except Exception as e:
        log.error("Press release search error: %s", e)
        releases = []

    return _render_results(releases, days)


@ar("/app/press-releases/{news_id:int}")
def press_release_detail(news_id: int):
    """Return a single press release detail — rendered as an expanded card."""
    r = get_press_release(news_id)
    if not r:
        return Div(P("Press release not found.", style="color:#64748B;padding:20px;"))

    title = r.get("display_title") or r.get("title") or "Untitled"
    company = r.get("company") or ""
    ticker = r.get("yf_ticker") or r.get("ticker") or ""
    publisher = r.get("publisher") or ""
    content = r.get("full_content") or ""
    link = r.get("link") or ""
    date_str = ""
    if r.get("published_date"):
        try:
            date_str = r["published_date"].strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_str = str(r["published_date"])[:16]

    # ML prediction
    pred = ""
    if r.get("predicted_side"):
        side = r["predicted_side"].upper()
        move = r.get("predicted_move") or 0
        cls = "pr-badge-up" if side == "UP" else "pr-badge-down"
        pred = Div(
            Span(f"ML Prediction: {side} {move:+.1f}%", cls=f"pr-badge {cls}"),
            style="margin-top:12px;",
        )

    reason_block = ""
    if r.get("reason"):
        reason_block = Div(
            P("AI Analysis", style="color:#F59E0B;font-size:12px;font-weight:600;margin-bottom:4px;"),
            P(r["reason"], style="color:#CBD5E1;font-size:13px;line-height:1.5;"),
            style="margin-top:12px;padding:12px;background:#0B1220;border-radius:6px;",
        )

    source_link = ""
    if link:
        source_link = A("View original source", href=link, target="_blank",
                        style="color:#F59E0B;font-size:12px;text-decoration:none;"
                              "display:inline-block;margin-top:12px;")

    close_btn = Button("Close",
                       onclick="document.getElementById('pr-detail-modal').innerHTML='';",
                       style="background:#1E293B;color:#94A3B8;border:none;border-radius:6px;"
                             "padding:6px 16px;font-size:12px;cursor:pointer;margin-top:16px;")

    return Div(
        Div(title, cls="pr-detail-title"),
        Div(
            Span(f"{company} · " if company else ""),
            Span(f"{ticker} · " if ticker else ""),
            Span(f"{date_str} · " if date_str else ""),
            Span(publisher),
            cls="pr-detail-meta",
        ),
        pred,
        Div(content, cls="pr-detail-content"),
        reason_block,
        source_link,
        close_btn,
        cls="pr-detail",
    )


@ar("/app/press-releases/pdf")
async def press_releases_pdf():
    """Export current press releases as PDF."""
    from utils.page_pdf import build_pdf, pdf_filename, Section, Row
    from starlette.responses import FileResponse

    try:
        releases = search_press_releases(days=30, limit=100)
    except Exception:
        releases = []

    rows = []
    for r in releases:
        date_str = ""
        if r.get("published_date"):
            try:
                date_str = r["published_date"].strftime("%Y-%m-%d")
            except Exception:
                date_str = str(r["published_date"])[:10]
        rows.append(Row([
            date_str,
            (r.get("company") or "")[:25],
            r.get("yf_ticker") or r.get("ticker") or "",
            (r.get("display_title") or "")[:60],
            _event_label(r.get("event") or "")[:25],
            (r.get("publisher") or "")[:20],
        ]))

    sections = [Section("Press Releases (Last 30 Days)",
                        headers=["Date", "Company", "Ticker", "Title", "Event", "Source"],
                        rows=rows)]
    path = build_pdf("Press Releases", "GlobeNewswire, Euronext, Nasdaq Nordic/Baltic", sections)
    fname = pdf_filename("Press-Releases")
    return FileResponse(str(path), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})
