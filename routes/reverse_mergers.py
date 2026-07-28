"""Reverse Mergers workspace, EDGAR synchronization, and manual CA imports."""
from __future__ import annotations

import logging

from fasthtml.common import *

log = logging.getLogger(__name__)
ar = APIRouter()


def _shell(session, request, rows, tab):
    from components.chat_shell import left_pane, right_pane
    from components.reverse_mergers import page_content

    user = session.get("user")
    email = user.get("email") if user else None
    header = Div(
        Div(Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span("Reverse Mergers", cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span("RTO & de-SPAC intelligence", cls="chat-header-agent"),
            cls="chat-header-left"),
        cls="chat-header",
    )
    return (
        Title("Reverse Mergers · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(user_email=email, sessions=[], current_sid="",
                      current_path="/app/reverse-mergers",
                      current_currency=session.get("currency", "EUR"),
                      current_role=session.get("role", "buyer")),
            Div(header, Div(page_content(rows, tab), cls="overflow-y-auto flex-1"), cls="center-pane"),
            right_pane(),
            cls="app pane-closed",
        ),
        Script(src="/chat.js?v=3"),
    )


@ar("/app/reverse-mergers")
def reverse_mergers_page(session, request):
    from utils.reverse_mergers import combined_market_rows

    params = request.query_params
    tab = params.get("tab", "all")
    rows = combined_market_rows()
    if tab == "reverse":
        rows = [r for r in rows if "spac" not in r.get("transaction_type", "")]
    elif tab == "spac":
        rows = [r for r in rows if "spac" in r.get("transaction_type", "")]
    jurisdiction, status, query = params.get("jurisdiction", ""), params.get("status", ""), params.get("q", "").lower()
    if jurisdiction:
        rows = [r for r in rows if r.get("jurisdiction") == jurisdiction]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if query:
        rows = [r for r in rows if query in " ".join(str(r.get(k, "")) for k in ("public_company", "private_target", "public_ticker")).lower()]
    return _shell(session, request, rows, tab)


@ar("/app/reverse-mergers/import", methods=["POST"])
async def import_reverse_merger(request):
    from utils.reverse_mergers import upsert_transactions, validate_manual_record
    try:
        record = validate_manual_record(dict(await request.form()))
        upsert_transactions([record])
        return Div("Reviewed Canadian record added.", style="color:#10B981;font-size:13px;margin-top:12px;")
    except Exception as exc:
        log.warning("Reverse-merger manual import failed: %s", exc)
        return Div(str(exc), style="color:#EF4444;font-size:13px;margin-top:12px;")


@ar("/app/reverse-mergers/sync", methods=["POST"])
def sync_reverse_mergers():
    try:
        from scripts.sync_reverse_mergers_edgar import main
        result = main(years=3, limit=100)
        return Span(f"{result['stored']} US records synced", style="color:#10B981;font-size:12px;")
    except Exception as exc:
        log.exception("Reverse-merger sync failed")
        return Span(f"Sync needs migration 18 / EDGAR access: {exc}", style="color:#EF4444;font-size:12px;")
