"""IPO Map — global IPO heatmap (ported from the `ipomap` Streamlit app).

/app/ipo-map               → full dashboard page
GET  /app/ipo-map/body     → filtered dashboard body (HTMX partial)
POST /app/ipo-map/refresh  → scrape fresh IPO data, re-render the body
GET  /app/ipo-map/commentary → lazy AI market commentary
GET  /app/ipo-map/news     → lazy IPO news
POST /app/ipo-map/signup   → email signup
"""
from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
import plotly.express as px
from fasthtml.common import (
    APIRouter, Div, Span, H2, H3, P, A, Button, Form, Input, Select, Option,
    Label, Title, Script, NotStr,
)
from starlette.requests import Request

from components.charts import PlotlyDiv, apply_dark_layout
from utils.database import db_service
from utils.ipo_utils import format_market_cap, format_percentage
from utils.ipo_scraper import region_for_country, REGION_BY_COUNTRY

log = logging.getLogger(__name__)
ar = APIRouter()

_FILTER_KEYS = ["region", "country", "exchange", "sector"]


# ── data ───────────────────────────────────────────────────────────────────

def _load_df(n_years: int = 3) -> pd.DataFrame:
    year = datetime.now().year
    frames = []
    for y in range(year, year - n_years, -1):
        df = db_service.get_ipo_data(year=y)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["ticker"])
    # backfill region/country for any legacy rows
    df["country"] = df["country"].fillna("United States")
    df["region"] = df.apply(
        lambda r: r["region"] if pd.notna(r["region"]) else region_for_country(r["country"]),
        axis=1,
    )
    for col in ("sector", "exchange"):
        df[col] = df[col].fillna("Unknown")
    df["market_cap"] = pd.to_numeric(df["market_cap"], errors="coerce").fillna(0)
    df["price_change_since_ipo"] = pd.to_numeric(df["price_change_since_ipo"], errors="coerce").fillna(0)
    return df


def _apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    out = df
    for key in _FILTER_KEYS:
        vals = filters.get(key)
        if vals:
            out = out[out[key].isin(vals)]
    return out


# ── small UI helpers ─────────────────────────────────────────────────────────

def _kpi(label: str, value: str, sub: str = "") -> Div:
    return Div(
        H3(value, cls="ipo-kpi-value"),
        P(label, cls="ipo-kpi-label"),
        P(sub, cls="ipo-kpi-sub") if sub else None,
        cls="ipo-kpi",
    )


def _multiselect(name: str, label: str, options: list, selected: list) -> Div:
    sel = set(selected) if selected else set(options)
    return Div(
        Label(label, cls="ipo-filter-label"),
        Select(
            *[Option(o, value=o, selected=(o in sel)) for o in options],
            name=name, multiple=True, size="4", cls="ipo-filter-select",
        ),
        cls="ipo-filter",
    )


def _table(df: pd.DataFrame, cols: dict) -> NotStr:
    view = df[list(cols.keys())].rename(columns=cols)
    return NotStr(view.to_html(index=False, classes="artifact-table", border=0))


# ── body renderer ────────────────────────────────────────────────────────────

def render_ipo_map_body(filters: dict) -> Div:
    df_full = _load_df()
    if df_full.empty:
        return Div(
            Div(
                P("No IPO data loaded yet.", cls="ipo-empty-title"),
                P("Click “Refresh IPO data” to pull recent IPOs from the NASDAQ calendar.",
                  cls="ipo-empty-sub"),
                cls="ipo-empty",
            ),
            id="ipo-map-body",
        )

    # filter option universe (region cascades into the rest)
    regions = sorted(df_full["region"].dropna().unique().tolist())
    region_sel = filters.get("region") or regions
    scoped = df_full[df_full["region"].isin(region_sel)]
    countries = sorted(scoped["country"].dropna().unique().tolist())
    exchanges = sorted(scoped["exchange"].dropna().unique().tolist())
    sectors = sorted(df_full["sector"].dropna().unique().tolist())

    df = _apply_filters(df_full, filters)

    filter_form = Form(
        _multiselect("region", "🌍 Regions", regions, filters.get("region")),
        _multiselect("country", "🏳️ Countries", countries, filters.get("country")),
        _multiselect("exchange", "🏢 Exchanges", exchanges, filters.get("exchange")),
        _multiselect("sector", "🏭 Sectors", sectors, filters.get("sector")),
        cls="ipo-filters",
        hx_get="/app/ipo-map/body",
        hx_target="#ipo-map-body",
        hx_swap="outerHTML",
        hx_trigger="change",
        hx_push_url="true",
    )

    if df.empty:
        return Div(
            filter_form,
            Div(P("No IPOs match the selected filters.", cls="ipo-empty-sub"), cls="ipo-empty"),
            id="ipo-map-body",
        )

    # KPIs
    best = df.loc[df["price_change_since_ipo"].idxmax()]
    kpis = Div(
        _kpi("Total IPOs", str(len(df))),
        _kpi("Avg performance", format_percentage(df["price_change_since_ipo"].mean())),
        _kpi("Total market cap", format_market_cap(df["market_cap"].sum())),
        _kpi("Best performer", best["ticker"],
             f"{format_percentage(best['price_change_since_ipo'])}"),
        cls="ipo-kpis",
    )

    # Treemap (needs positive market caps)
    tdf = df[df["market_cap"] > 0]
    charts = []
    if not tdf.empty:
        fig = px.treemap(
            tdf,
            path=[px.Constant("All IPOs"), "region", "country", "sector", "ticker"],
            values="market_cap",
            color="price_change_since_ipo",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
        )
        fig.update_traces(textinfo="label+value")
        j = apply_dark_layout(fig, height=560)
        ipo_legend = Div(
            Div(
                Span("How to read this treemap", cls="text-xs font-semibold", style="color:#F8FAFC"),
                cls="mb-1",
            ),
            Div(
                Div(
                    Div(style="width:40px;height:12px;border-radius:2px;background:linear-gradient(90deg,#EF4444,#FBBF24,#22C55E);flex-shrink:0"),
                    Span("Color = performance since IPO (red = negative, yellow = flat, green = positive)", cls="text-xs", style="color:#94A3B8"),
                    cls="flex items-center gap-2",
                ),
                Div(
                    Div(style="width:12px;height:12px;border-radius:2px;border:1px solid #1E293B;background:#111827;flex-shrink:0"),
                    Span("Size = market cap in USD (larger cell = larger company)", cls="text-xs", style="color:#94A3B8"),
                    cls="flex items-center gap-2",
                ),
                Div(
                    Span("Hierarchy: All IPOs → Region → Country → Sector → Ticker", cls="text-xs", style="color:#94A3B8"),
                    cls="flex items-center gap-2 ml-[20px]",
                ),
                cls="flex flex-col gap-1",
            ),
            cls="mt-2 p-3 rounded-lg",
            style="background:#111827; border:1px solid #1E293B",
        )
        charts.append(Div(H3("Performance treemap", cls="ipo-section-title"),
                          PlotlyDiv("ipo-treemap", j["data"], j["layout"]),
                          ipo_legend,
                          cls="ipo-card"))

    # Histogram + sector bar side by side
    hfig = px.histogram(df, x="price_change_since_ipo", nbins=20,
                        labels={"price_change_since_ipo": "Return since IPO"})
    hj = apply_dark_layout(hfig, height=360)
    sector_perf = df.groupby("sector")["price_change_since_ipo"].mean().sort_values()
    bfig = px.bar(x=sector_perf.values, y=sector_perf.index, orientation="h",
                  labels={"x": "Avg return", "y": "Sector"})
    bj = apply_dark_layout(bfig, height=360)
    charts.append(Div(
        Div(H3("Performance distribution", cls="ipo-section-title"),
            PlotlyDiv("ipo-hist", hj["data"], hj["layout"]), cls="ipo-card ipo-half"),
        Div(H3("Sector performance", cls="ipo-section-title"),
            PlotlyDiv("ipo-sector", bj["data"], bj["layout"]), cls="ipo-card ipo-half"),
        cls="ipo-row",
    ))

    # Tables
    df_disp = df.copy()
    df_disp["Performance"] = df_disp["price_change_since_ipo"].apply(format_percentage)
    df_disp["Market Cap"] = df_disp["market_cap"].apply(format_market_cap)
    tbl_cols = {"ticker": "Ticker", "company_name": "Company", "country": "Country",
                "sector": "Sector", "Performance": "Performance", "Market Cap": "Market Cap"}
    top = df_disp.nlargest(10, "price_change_since_ipo")
    worst = df_disp.nsmallest(10, "price_change_since_ipo")
    tables = Div(
        Div(H3("🚀 Top performers", cls="ipo-section-title"), _table(top, tbl_cols), cls="ipo-card ipo-half"),
        Div(H3("📉 Worst performers", cls="ipo-section-title"), _table(worst, tbl_cols), cls="ipo-card ipo-half"),
        cls="ipo-row",
    )

    # Lazy AI commentary + news (load after paint)
    lazy = Div(
        Div(H3("🤖 AI market analysis", cls="ipo-section-title"),
            Div(P("Generating analysis…", cls="ipo-empty-sub"),
                hx_get="/app/ipo-map/commentary", hx_trigger="load", hx_swap="innerHTML"),
            cls="ipo-card"),
        Div(H3("📰 IPO news", cls="ipo-section-title"),
            Div(P("Loading news…", cls="ipo-empty-sub"),
                hx_get="/app/ipo-map/news", hx_trigger="load", hx_swap="innerHTML"),
            cls="ipo-card"),
        cls="ipo-row",
    )

    return Div(filter_form, kpis, *charts, tables, lazy, id="ipo-map-body")


# ── routes ───────────────────────────────────────────────────────────────────

def _parse_filters(request: Request) -> dict:
    qp = request.query_params
    return {k: qp.getlist(k) for k in _FILTER_KEYS if qp.getlist(k)}


@ar("/app/ipo-map")
def ipo_map_page(session, request: Request):
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

    last = None
    try:
        last = db_service.get_last_ipo_refresh()
    except Exception:
        pass
    last_txt = f"Last refresh: {str(last['completed_at'])[:16]}" if last and last.get("completed_at") else "Not refreshed yet"

    header = Div(
        Div(
            Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span("IPO Map", cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span("Global heatmap", cls="chat-header-agent"),
            cls="chat-header-left",
        ),
        Div(
            Button("🔄 Refresh IPO data", cls="ipo-refresh-btn",
                   hx_post="/app/ipo-map/refresh", hx_target="#ipo-map-body",
                   hx_swap="outerHTML", **{"hx-indicator": "#ipo-refresh-ind"}),
            Span("", id="ipo-refresh-ind", cls="ipo-indicator htmx-indicator", title="Working…"),
            cls="chat-header-actions",
        ),
        cls="chat-header",
    )

    signup = Form(
        Input(type="email", name="email", placeholder="you@example.com", cls="ipo-signup-input", required=True),
        Button("Notify me", type="submit", cls="ipo-signup-btn"),
        Span(last_txt, cls="ipo-refresh-meta"),
        cls="ipo-signup",
        hx_post="/app/ipo-map/signup", hx_target="#ipo-signup-msg", hx_swap="innerHTML",
    )

    return (
        Title("IPO Map · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(user_email=email, sessions=sessions_list, current_sid="",
                      current_path="/app/ipo-map",
                      current_currency=session.get("currency", "EUR"),
                      current_role=session.get("role", "buyer")),
            Div(
                header,
                Div(
                    Div(
                        H2("Global IPO heatmap", cls="text-ink"),
                        P("Recent IPOs sized by market cap, colored by performance since listing.",
                          cls="text-ink-muted"),
                        signup,
                        Div(id="ipo-signup-msg"),
                        cls="ipo-hero",
                    ),
                    render_ipo_map_body({}),
                    cls="ipo-wrap",
                ),
                cls="center-pane",
            ),
            right_pane(),
            cls="app pane-closed",
        ),
        Script(src="/chat.js?v=2"),
    )


@ar("/app/ipo-map/body")
def ipo_map_body(request: Request):
    return render_ipo_map_body(_parse_filters(request))


@ar("/app/ipo-map/refresh", methods=["POST"])
def ipo_map_refresh():
    started = datetime.now().isoformat()
    try:
        from utils.ipo_utils import IPODataFetcher
        fetcher = IPODataFetcher()
        year = datetime.now().year
        total = 0
        for y in (year, year - 1):
            records = fetcher.get_nasdaq_nyse_ipos(year=y, max_tickers=60)
            total += db_service.insert_ipo_data(records)
        db_service.log_ipo_refresh("IPO_MAP_REFRESH", "SUCCESS", total, started_at=started)
    except Exception as e:  # noqa: BLE001
        log.exception("IPO map refresh failed")
        db_service.log_ipo_refresh("IPO_MAP_REFRESH", "ERROR", 0, error_message=str(e), started_at=started)
    return render_ipo_map_body({})


@ar("/app/ipo-map/commentary")
def ipo_map_commentary(request: Request):
    from utils.ipo_commentary import get_ipo_commentary
    df = _apply_filters(_load_df(), _parse_filters(request))
    if df.empty:
        return Div(P("No data for commentary.", cls="ipo-empty-sub"))
    return Div(NotStr(_md(get_ipo_commentary(df))), cls="ipo-markdown")


@ar("/app/ipo-map/news")
async def ipo_map_news():
    from utils.ipo_news import get_ipo_news
    items = await get_ipo_news()
    if not items:
        return Div(P("No news available right now.", cls="ipo-empty-sub"))
    cards = []
    for a in items:
        cards.append(Div(
            A(a["title"], href=a["url"], target="_blank", cls="ipo-news-title"),
            P(a["summary"][:220], cls="ipo-news-summary"),
            P(a["source"], cls="ipo-news-source"),
            cls="ipo-news-item",
        ))
    return Div(*cards, cls="ipo-news-list")


@ar("/app/ipo-map/signup", methods=["POST"])
async def ipo_map_signup(request: Request):
    form = await request.form()
    email = (form.get("email") or "").strip()
    ok = db_service.insert_ipo_signup(email)
    msg = "Thanks — we'll keep you posted." if ok else "You're already on the list (or invalid email)."
    return Span(msg, cls="ipo-signup-ok" if ok else "ipo-signup-warn")


def _md(text: str) -> str:
    """Minimal markdown → HTML (headings, bold, lists, paragraphs)."""
    try:
        import markdown2
        return markdown2.markdown(text)
    except Exception:
        return "<p>" + text.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
