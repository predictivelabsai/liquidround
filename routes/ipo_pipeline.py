"""IPO Pipeline — pre-IPO private companies (.PVT) + upcoming US IPOs.

/app/ipo-pipeline               → full page
GET  /app/ipo-pipeline/body     → sorted body (HTMX partial)
POST /app/ipo-pipeline/refresh  → refresh private + upcoming data, re-render
"""
from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
import plotly.express as px
from fasthtml.common import (
    APIRouter, Div, Span, H2, H3, P, A, Button, Title, Script, NotStr,
)
from starlette.requests import Request

from components.charts import PlotlyDiv, apply_dark_layout
from utils.database import db_service
from utils.ipo_utils import format_market_cap

log = logging.getLogger(__name__)
ar = APIRouter()


def _fmt_val(v) -> str:
    return format_market_cap(float(v)) if pd.notna(v) and v else "—"


def _fmt_date(v) -> str:
    return str(v)[:10] if pd.notna(v) and v else "—"


def _fmt_int(v) -> str:
    return f"{int(v):,}" if pd.notna(v) and v else "—"


def _txt(v) -> str:
    """Coerce a possibly-NaN cell to a clean string ('' if missing)."""
    return v if isinstance(v, str) and v.strip() else ""


def _private_card(r: pd.Series) -> Div:
    summary = _txt(r.get("summary"))
    website = _txt(r.get("website"))
    return Div(
        Div(
            Span(_txt(r.get("company_name")) or "—", cls="ipo-pl-name"),
            Span(_fmt_val(r.get("last_valuation")), cls="ipo-pl-val"),
            cls="ipo-pl-card-head",
        ),
        P(_txt(r.get("sector")) or "—", cls="ipo-pl-sector"),
        Div(
            Span(f"Round: {_txt(r.get('last_round')) or '—'}", cls="ipo-pl-meta"),
            Span(f"Date: {_fmt_date(r.get('last_round_date'))}", cls="ipo-pl-meta"),
            Span(f"Rounds: {_fmt_int(r.get('total_rounds'))}", cls="ipo-pl-meta"),
            Span(f"Staff: {_fmt_int(r.get('employees'))}", cls="ipo-pl-meta"),
            cls="ipo-pl-metarow",
        ),
        P(summary[:240], cls="ipo-pl-summary") if summary else None,
        A("Website ↗", href=website, target="_blank", cls="ipo-pl-link") if website else None,
        cls="ipo-pl-card",
    )


def render_pipeline_body(sort: str = "last_valuation") -> Div:
    df = db_service.get_pipeline_companies(order_by=sort)
    if df.empty:
        return Div(
            Div(P("No pipeline data yet.", cls="ipo-empty-title"),
                P("Click “Refresh pipeline” to load private companies and upcoming IPOs.",
                  cls="ipo-empty-sub"), cls="ipo-empty"),
            id="ipo-pipeline-body",
        )

    completed = df[df["kind"] == "ipo_completed"].copy()
    private = df[df["kind"] == "private"].copy()
    upcoming = df[(df["kind"] != "private") & (df["kind"] != "ipo_completed")].copy()

    children = []

    # Recently completed IPOs
    if not completed.empty:
        comp = completed.copy()
        comp["Valuation"] = comp["last_valuation"].apply(_fmt_val)
        comp["IPO Date"] = comp["expected_date"].apply(_fmt_date)
        view_c = comp[["company_name", "ticker", "exchange", "Valuation", "IPO Date"]].rename(
            columns={"company_name": "Company", "ticker": "Ticker", "exchange": "Exchange"})
        view_c = view_c.fillna("—")
        children.append(Div(
            H3(f"Recently completed IPOs ({len(completed)})", cls="ipo-section-title"),
            NotStr(view_c.to_html(index=False, classes="artifact-table", border=0)),
            cls="ipo-card",
        ))

    # Valuation chart for private companies
    pv = private[private["last_valuation"].notna() & (private["last_valuation"] > 0)].copy()
    if not pv.empty:
        pv = pv.sort_values("last_valuation", ascending=True)
        pv["sector"] = pv["sector"].fillna("Other")
        fig = px.bar(x=pv["last_valuation"] / 1e9, y=pv["company_name"], orientation="h",
                     color=pv["sector"], labels={"x": "Implied valuation ($B)", "y": ""})
        j = apply_dark_layout(fig, height=max(320, 36 * len(pv)))
        children.append(Div(H3("Private valuations", cls="ipo-section-title"),
                            PlotlyDiv("ipo-pl-valbar", j["data"], j["layout"]), cls="ipo-card"))

    # Private cards
    if not private.empty:
        children.append(Div(
            H3(f"Pre-IPO private companies ({len(private)})", cls="ipo-section-title"),
            Div(*[_private_card(r) for _, r in private.iterrows()], cls="ipo-pl-grid"),
            cls="ipo-card",
        ))

    # Upcoming / filed IPOs table
    if not upcoming.empty:
        up = upcoming.copy()
        up["Valuation/Deal"] = up["deal_value"].apply(_fmt_val)
        up["Price"] = up["proposed_price"].apply(lambda v: f"${float(v):.2f}" if pd.notna(v) and v else "—")
        up["Expected"] = up["expected_date"].apply(_fmt_date)
        view = up[["company_name", "ticker", "exchange", "Price", "Valuation/Deal", "Expected", "status"]].rename(
            columns={"company_name": "Company", "ticker": "Ticker", "exchange": "Exchange", "status": "Status"})
        view = view.fillna("—")
        children.append(Div(
            H3(f"Upcoming & filed IPOs ({len(upcoming)})", cls="ipo-section-title"),
            NotStr(view.to_html(index=False, classes="artifact-table", border=0)),
            cls="ipo-card",
        ))

    return Div(*children, id="ipo-pipeline-body")


@ar("/app/ipo-pipeline")
def ipo_pipeline_page(session):
    from components.chat_shell import left_pane, right_pane

    user = session.get("user")
    email = user.get("email") if user else None
    sessions_list = []
    if user and user.get("user_id"):
        try:
            convs = db_service.get_user_conversations(user["user_id"], limit=20) or []
            sessions_list = [{"id": c["id"], "title": c.get("conversation_title") or c.get("user_query", "Untitled")}
                             for c in convs]
        except Exception:
            pass

    sort_bar = Div(
        Span("Sort:", cls="ipo-sort-label"),
        *[Button(lbl, cls="ipo-sort-btn",
                 hx_get=f"/app/ipo-pipeline/body?sort={key}",
                 hx_target="#ipo-pipeline-body", hx_swap="outerHTML")
          for lbl, key in (("Valuation", "last_valuation"), ("Name", "name"),
                           ("Round date", "round_date"), ("Expected", "expected_date"))],
        cls="ipo-sort-bar",
    )

    header = Div(
        Div(
            Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span("IPO Pipeline", cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span("Pre-IPO & upcoming", cls="chat-header-agent"),
            cls="chat-header-left",
        ),
        Div(
            Button("🔄 Refresh pipeline", cls="ipo-refresh-btn",
                   hx_post="/app/ipo-pipeline/refresh", hx_target="#ipo-pipeline-body",
                   hx_swap="outerHTML", **{"hx-indicator": "#ipo-pl-ind"}),
            Span("", id="ipo-pl-ind", cls="ipo-indicator htmx-indicator"),
            cls="chat-header-actions",
        ),
        cls="chat-header",
    )

    return (
        Title("IPO Pipeline · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(user_email=email, sessions=sessions_list, current_sid="",
                      current_path="/app/ipo-pipeline",
                      current_currency=session.get("currency", "EUR"),
                      current_role=session.get("role", "buyer")),
            Div(
                header,
                Div(
                    Div(
                        H2("Companies heading to public markets", cls="text-ink"),
                        P("Private mega-caps (via Yahoo .PVT) and upcoming US IPOs from the NASDAQ calendar.",
                          cls="text-ink-muted"),
                        sort_bar,
                        cls="ipo-hero",
                    ),
                    render_pipeline_body(),
                    cls="ipo-wrap",
                ),
                cls="center-pane",
            ),
            right_pane(),
            cls="app",
        ),
        Script(src="/chat.js?v=4"),
    )


@ar("/app/ipo-pipeline/body")
def ipo_pipeline_body(request: Request):
    sort = request.query_params.get("sort", "last_valuation")
    return render_pipeline_body(sort)


@ar("/app/ipo-pipeline/refresh", methods=["POST"])
def ipo_pipeline_refresh():
    try:
        from utils.ipo_pipeline_fetcher import refresh_pipeline
        refresh_pipeline()
    except Exception:  # noqa: BLE001
        log.exception("Pipeline refresh failed")
    return render_pipeline_body()
