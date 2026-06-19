"""Hedge fund routes — treemap page + JSON data API with in-memory cache."""
from __future__ import annotations

import logging
import time

from fasthtml.common import *
from fasthtml.core import APIRouter
from starlette.responses import JSONResponse

from components.hedge_funds import hedge_fund_page_content

log = logging.getLogger(__name__)
ar = APIRouter()

_cache: dict[str, tuple[float, list]] = {}
_CACHE_TTL = 600  # 10 minutes


@ar("/app/hedgefunds")
def hedge_funds_page(session, request):
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

    header = Div(
        Div(
            Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span("Hedge Funds", cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span("SEC 13F Institutional Holdings", cls="chat-header-agent"),
            cls="chat-header-left",
        ),
        cls="chat-header",
    )

    return (
        Title("Hedge Funds · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(user_email=email, sessions=sessions_list, current_sid="",
                      current_path="/app/hedgefunds",
                      current_currency=session.get("currency", "EUR"),
                      current_role=session.get("role", "buyer")),
            Div(
                header,
                Div(hedge_fund_page_content(), cls="overflow-y-auto flex-1"),
                cls="center-pane",
            ),
            right_pane(),
            cls="app pane-closed",
        ),
        Script(src="/chat.js"),
    )


@ar("/app/hedgefunds/data")
def hedge_funds_data(request):
    params = request.query_params
    fund = params.get("fund", "")
    min_value = int(params.get("min_value", 0))
    limit = min(int(params.get("limit", 500)), 2000)
    cache_key = f"{fund}:{min_value}:{limit}"
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key][0] < _CACHE_TTL:
        return JSONResponse(_cache[cache_key][1])
    try:
        from utils.hedge_fund_db import get_treemap_data
        data = get_treemap_data(min_value=min_value, fund_filter=fund, limit=limit)
        _cache[cache_key] = (now, data)
        return JSONResponse(data)
    except Exception as e:
        log.error("Treemap data error: %s", e)
        return JSONResponse([], status_code=500)
