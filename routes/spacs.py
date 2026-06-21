"""SPAC tracker routes — dashboard page + HTMX partials + data API."""
from __future__ import annotations

import logging

from fasthtml.common import *
from fasthtml.core import APIRouter

log = logging.getLogger(__name__)
ar = APIRouter()


@ar("/app/spacs")
def spacs_page(session, request):
    from components.chat_shell import left_pane, right_pane
    from components.spacs import spac_page_content
    from utils.spac_db import get_spac_data, get_spac_stats, get_spac_timeline, get_status_breakdown

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

    stats = get_spac_stats()
    df = get_spac_data(limit=200)
    timeline = get_spac_timeline(years=6)
    breakdown = get_status_breakdown()

    header = Div(
        Div(
            Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span("SPAC Tracker", cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span("Special Purpose Acquisition Companies", cls="chat-header-agent"),
            cls="chat-header-left",
        ),
        cls="chat-header",
    )

    return (
        Title("SPACs · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(user_email=email, sessions=sessions_list, current_sid="",
                      current_path="/app/spacs",
                      current_currency=session.get("currency", "EUR"),
                      current_role=session.get("role", "buyer")),
            Div(
                header,
                Div(
                    spac_page_content(stats, df, timeline, breakdown),
                    cls="overflow-y-auto flex-1",
                ),
                cls="center-pane",
            ),
            right_pane(),
            cls="app pane-closed",
        ),
        Script(src="/chat.js?v=2"),
    )


@ar("/app/spacs/body")
def spacs_body(request):
    from components.spacs import spac_table
    from utils.spac_db import get_spac_data, search_spacs

    params = request.query_params
    status = params.get("status", "") or None
    min_trust = int(params.get("min_trust", 0))
    q = params.get("q", "").strip()

    if q:
        df = search_spacs(q)
    else:
        df = get_spac_data(status=status, limit=500)

    if min_trust and not df.empty:
        df = df[df["trust_size"].fillna(0) >= min_trust]

    return spac_table(df)


@ar("/app/spacs/holders/{ticker}")
def spac_holders(ticker: str):
    from utils.spac_db import get_institutional_holders

    if not ticker or ticker == "None":
        return Div(P("No ticker", cls="text-xs", style="color:#94A3B8"))

    holders = get_institutional_holders(ticker, limit=10)
    if not holders:
        return Div(P(f"No 13F institutional holders found for {ticker}",
                     cls="text-xs", style="color:#94A3B8"))

    rows = []
    for h in holders:
        val = h.get("position_value") or 0
        fmt_val = f"${val/1e6:.1f}M" if val >= 1e6 else f"${val/1e3:.0f}K" if val >= 1e3 else f"${val}"
        rows.append(Tr(
            Td(str(h.get("fund", "—"))[:40], cls="px-2 py-1 text-xs", style="color:#F8FAFC"),
            Td(fmt_val, cls="px-2 py-1 text-xs text-right", style="color:#F59E0B"),
            Td(f"{h.get('shares', 0):,.0f}" if h.get("shares") else "—",
               cls="px-2 py-1 text-xs text-right", style="color:#94A3B8"),
        ))

    return Div(
        P(f"13F Institutional Holders — {ticker}", cls="text-xs font-medium mb-1",
          style="color:#F59E0B"),
        Table(
            Thead(Tr(
                Th("Fund", cls="px-2 py-1 text-xs text-left", style="color:#94A3B8"),
                Th("Value", cls="px-2 py-1 text-xs text-right", style="color:#94A3B8"),
                Th("Shares", cls="px-2 py-1 text-xs text-right", style="color:#94A3B8"),
            )),
            Tbody(*rows),
            cls="w-full",
        ),
    )


@ar("/app/spacs/refresh", methods=["POST"])
async def spacs_refresh(request):
    try:
        from scripts.sync_spacs import main as sync_main
        result = sync_main(months=6, enrich=False)
        return Div(
            P(f"Synced {result.get('upserted', 0)} SPACs", cls="text-xs",
              style="color:#10B981"),
        )
    except Exception as e:
        log.error("SPAC refresh failed: %s", e)
        return Div(
            P(f"Refresh failed: {e}", cls="text-xs", style="color:#EF4444"),
        )
