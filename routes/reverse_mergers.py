"""Reverse Mergers workspace, EDGAR synchronization, and manual CA imports."""
from __future__ import annotations

import logging
import math

from fasthtml.common import *

log = logging.getLogger(__name__)
ar = APIRouter()


def _shell(session, request, rows, tab, news_rows=None, news_source="", news_stage="",
           filters=None):
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
            Div(header, Div(page_content(rows, tab, news_rows, news_source, news_stage, filters),
                            cls="overflow-y-auto flex-1"), cls="center-pane"),
            right_pane(open_by_default=True, title="Deal context",
                       subtitle="GlobeNewswire · FT · Bloomberg",
                       feed_url="/app/reverse-mergers/context-news"),
            cls="app rto-shell",
        ),
        Script(src="/chat.js?v=4"),
    )


@ar("/app/reverse-mergers")
def reverse_mergers_page(session, request):
    from utils.reverse_mergers import combined_market_rows

    params = request.query_params
    tab = params.get("tab", "all")
    rows = combined_market_rows()
    news_rows = []
    news_source = params.get("source", "")
    news_stage = params.get("stage", "")
    if tab == "news":
        from utils.merger_news import list_merger_news
        news_rows = list_merger_news(source=news_source, stage=news_stage)
    if tab == "reverse":
        rows = [r for r in rows if "spac" not in r.get("transaction_type", "")]
    elif tab == "spac":
        rows = [r for r in rows if "spac" in r.get("transaction_type", "")]
    jurisdiction = params.get("jurisdiction", "")
    status = params.get("status", "")
    has_target = params.get("has_target", "")
    has_value = params.get("has_value", "")
    query = params.get("q", "").lower()
    if jurisdiction:
        rows = [r for r in rows if r.get("jurisdiction") == jurisdiction]
    if status == "completed":
        rows = [r for r in rows if r.get("status") == status]
    elif status == "not_completed":
        rows = [r for r in rows if r.get("status") != "completed"]
    if has_target == "yes":
        rows = [r for r in rows if r.get("private_target")]
    elif has_target == "no":
        rows = [r for r in rows if not r.get("private_target")]
    if has_value == "yes":
        rows = [r for r in rows if r.get("deal_value") not in (None, "")]
    elif has_value == "no":
        rows = [r for r in rows if r.get("deal_value") in (None, "")]
    if query:
        rows = [r for r in rows if query in " ".join(str(r.get(k, "")) for k in ("public_company", "private_target", "public_ticker")).lower()]
    page = max(1, int(params.get("page", "1") or 1))
    per_page = 50
    total = len(rows)
    summary = {
        "reverse": sum("spac" not in r.get("transaction_type", "") for r in rows),
        "spacs": sum("spac" in r.get("transaction_type", "") for r in rows),
        "completed": sum(str(r.get("status", "")).lower() == "completed" for r in rows),
        "canada": sum(r.get("jurisdiction") == "CA" for r in rows),
    }
    total_pages = max(1, math.ceil(total / per_page))
    page = min(page, total_pages)
    if tab not in {"news", "methodology", "import"}:
        rows = rows[(page - 1) * per_page:page * per_page]
    return _shell(session, request, rows, tab, news_rows, news_source, news_stage, {
        "jurisdiction": jurisdiction, "status": status,
        "has_target": has_target, "has_value": has_value,
        "q": params.get("q", ""),
        "_pagination": {
            "page": page, "total_pages": total_pages, "total": total,
            "query": {
                key: value for key, value in params.items()
                if key != "page" and value
            },
        },
        "_summary": summary,
    })


@ar("/app/reverse-mergers/context-news")
async def reverse_merger_context_news():
    """Merger wires plus FT/Bloomberg market context; intentionally no ERR."""
    import re
    from datetime import datetime, timezone
    from utils.merger_news import list_merger_news
    from utils.news import fetch_news

    def ago(value) -> str:
        try:
            dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            seconds = (datetime.now(timezone.utc) - dt).total_seconds()
            if seconds < 3600:
                return f"{max(1, int(seconds // 60))}m ago"
            if seconds < 86400:
                return f"{int(seconds // 3600)}h ago"
            return f"{int(seconds // 86400)}d ago"
        except Exception:
            return ""

    items = [{
        "icon": "GNW", "title": row["title"], "url": row["source_url"],
        "summary": row.get("summary") or "", "published": row.get("published_at"),
    } for row in list_merger_news(source="globenewswire", limit=12)]

    market_news = [
        article for article in await fetch_news()
        if article["icon"] in {"FT", "BBG"}
    ]
    deal_pattern = re.compile(
        r"\b(merger|acqui(?:re|res|red|sition)|takeover|spac|buyout|"
        r"take-private|stake sale|acquisition bid)\b",
        re.IGNORECASE,
    )
    contextual = [
        article for article in market_news
        if deal_pattern.search(f"{article['title']} {article.get('summary', '')}")
    ]
    for article in contextual:
        if len(items) >= 30:
            break
        if not any(item["url"] == article["url"] for item in items):
            items.append(article)
    items.sort(key=lambda item: str(item.get("published") or ""), reverse=True)

    return Div(*(
        A(
            Div(Span(item["icon"], cls="news-source"),
                Span(ago(item.get("published")), cls="news-time"),
                cls="news-item-header"),
            Div(item["title"], cls="news-item-title"),
            Div(re.sub(r"<[^>]+>", "", item.get("summary", ""))[:140],
                cls="news-item-summary") if item.get("summary") else None,
            href=item["url"], target="_blank", rel="noopener", cls="news-item",
        )
        for item in items[:30]
    ))


@ar("/app/reverse-mergers/import", methods=["POST"])
async def import_reverse_merger(request):
    from utils.reverse_mergers import (
        extract_transaction_terms,
        upsert_transactions,
        validate_manual_record,
    )
    try:
        form = dict(await request.form())
        source_document = form.pop("source_document", None)
        record = validate_manual_record(form)
        if source_document and getattr(source_document, "filename", ""):
            from utils.filing_intelligence import parse_authorized_document

            parsed = parse_authorized_document(
                await source_document.read(), source_document.filename
            )
            terms = extract_transaction_terms(
                parsed["text"], public_company=record["public_company"]
            )
            record["private_target"] = record.get("private_target") or terms["private_target"]
            record["deal_value"] = terms["deal_value"]
            if terms["completed"]:
                record["status"] = "completed"
            elif terms["announced"]:
                record["status"] = "announced"
            record["metadata"].update({
                "document_parsed": True,
                "document_filename": parsed["filename"],
                "document_hash": parsed["sha256"],
                "section_items": sorted(parsed["sections"]),
            })
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


@ar("/app/reverse-mergers/sync-sedar", methods=["POST"])
def sync_sedar_reverse_mergers():
    try:
        from scripts.sync_reverse_mergers_sedar import main
        result = main(days=365, limit=40)
        return Span(f"{result['stored']} Canadian records synced from SEDAR+", style="color:#10B981;font-size:12px;")
    except Exception as exc:
        log.exception("SEDAR+ sync failed")
        return Span(f"SEDAR+ sync needs Playwright + chromium: {exc}", style="color:#EF4444;font-size:12px;")


@ar("/app/reverse-mergers/sync-news", methods=["POST"])
def sync_merger_news():
    try:
        from utils.merger_news import fetch_merger_news, upsert_merger_news
        stored = upsert_merger_news(fetch_merger_news())
        return Span(f"{stored} merger releases synced. Refresh to view.",
                    style="color:#10B981;font-size:12px;")
    except Exception as exc:
        log.exception("Merger-news RSS sync failed")
        return Span(f"Feed sync failed: {exc}", style="color:#EF4444;font-size:12px;")
