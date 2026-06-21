"""
Companies routes — searchable company directory + detail/overview page.

Ported from pehero, adapted for LiquidRound's architecture (APIRouter,
navy+amber palette, optional auth, no i18n).

/app/companies         -> company search page (name ILIKE + sector filter)
/app/company/{slug}    -> company detail/overview (deep-link target from email)
"""
from __future__ import annotations

import os

from fasthtml.common import (
    Html, Head, Body, Meta, Title, Link, Script, NotStr,
    Div, Span, H2, H3, H4, P, A, Button, Form, Input, Select, Option, Label,
    Table, Thead, Tbody, Tr, Th, Td,
)
from fasthtml.core import APIRouter

from utils.database import get_conn

ar = APIRouter()

DB_SCHEMA = os.getenv("COMPANY_DB_SCHEMA", "pehero")


# ── Helpers ─────────────────────────────────────────────────────────────

def _fetch_one(sql: str, params: tuple = ()):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None


def _fetch_all(sql: str, params: tuple = ()):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def _fmt_money(val, sym="€"):
    if not val:
        return "—"
    v = float(val)
    if v >= 1_000_000_000:
        return f"{sym}{v / 1e9:.1f}B"
    if v >= 1_000_000:
        return f"{sym}{v / 1e6:.1f}M"
    if v >= 1_000:
        return f"{sym}{v / 1e3:.0f}K"
    return f"{sym}{v:,.0f}"


def _fmt_int(val):
    if not val:
        return "—"
    return f"{int(val):,}"


def _stage_badge(stage):
    colors = {
        "sourced": "#9CA89E",
        "screened": "#7A9E88",
        "loi": "#C89B5B",
        "diligence": "#B57D3E",
        "ic": "#4A8E66",
        "signed": "#2F7151",
        "closed": "#1F5D43",
        "held": "#3C5748",
        "exited": "#6B4E2F",
        "passed": "#9C8F7A",
    }
    color = colors.get(stage, "#9CA89E")
    return Span(
        (stage or "sourced").replace("_", " ").title(),
        style=(
            f"background:{color};color:white;padding:2px 8px;border-radius:4px;"
            f"font-size:.68rem;font-weight:600;text-transform:uppercase;"
            f"letter-spacing:.06em;"
        ),
    )


def _head(title: str = "Companies · LiquidRound"):
    return Head(
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width,initial-scale=1"),
        Title(title),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap",
        ),
        Script(src="https://cdn.tailwindcss.com"),
        Link(rel="stylesheet", href="/app.css"),
        Link(rel="stylesheet", href="/pipeline.css"),
        Link(rel="icon", type="image/svg+xml", href="/favicon.svg"),
    )


# ── Company search page ────────────────────────────────────────────────

@ar("/app/companies")
def companies_search(sess, name: str = "", sector: str = ""):
    from components.chat_shell import left_pane

    user_email = sess.get("email") if sess else None
    current_role = sess.get("role", "buyer") if sess else "buyer"

    # Fetch distinct sectors for the filter dropdown
    sectors = _fetch_all(
        f"SELECT DISTINCT sector FROM {DB_SCHEMA}.companies "
        f"WHERE sector IS NOT NULL ORDER BY sector"
    )
    sector_list = [r["sector"] for r in sectors]

    # Build query with optional filters
    sql = (
        f"SELECT slug, name, hq_city, country, sector, sub_sector, employees, "
        f"revenue_ltm, ebitda_ltm, ebitda_margin, deal_stage, founded_year "
        f"FROM {DB_SCHEMA}.companies WHERE TRUE"
    )
    params: list = []

    if name.strip():
        sql += " AND name ILIKE %s"
        params.append(f"%{name.strip()}%")
    if sector.strip():
        sql += " AND sector = %s"
        params.append(sector.strip())

    sql += " ORDER BY revenue_ltm DESC NULLS LAST LIMIT 200"
    rows = _fetch_all(sql, tuple(params))

    # Sector dropdown options
    sector_options = [Option("All sectors", value="")]
    for s in sector_list:
        sector_options.append(Option(
            s.replace("_", " ").title(),
            value=s,
            selected=s == sector,
        ))

    # Search bar
    search_bar = Form(
        Div(
            Input(
                type="text", name="name", value=name,
                placeholder="Search by company name...",
                cls="co-search-input",
            ),
            Select(*sector_options, name="sector", cls="co-sector-select"),
            Button("Search", type="submit", cls="co-search-btn"),
            cls="co-search-row",
        ),
        method="GET", action="/app/companies",
        cls="co-search-form",
    )

    # Results table
    if rows:
        header = Tr(
            Th("Name"), Th("City"), Th("Sector"), Th("Revenue"),
            Th("EBITDA"), Th("Employees"), Th("Stage"),
        )
        body_rows = []
        for r in rows:
            sector_chip = Span(
                (r.get("sector") or "—").replace("_", " ").title(),
                style=(
                    "background:rgba(245,158,11,.15);color:#F59E0B;"
                    "padding:2px 8px;border-radius:4px;font-size:.7rem;"
                    "font-weight:500;"
                ),
            ) if r.get("sector") else Span("—")

            body_rows.append(Tr(
                Td(A(r["name"], href=f"/app/company/{r['slug']}", cls="co-name-link")),
                Td(r.get("hq_city") or "—"),
                Td(sector_chip),
                Td(_fmt_money(r.get("revenue_ltm")), cls="co-num"),
                Td(_fmt_money(r.get("ebitda_ltm")), cls="co-num"),
                Td(_fmt_int(r.get("employees")), cls="co-num"),
                Td(_stage_badge(r.get("deal_stage"))),
            ))

        results = Div(
            Span(f"{len(rows)} companies", cls="co-result-count"),
            Table(Thead(header), Tbody(*body_rows), cls="co-table"),
            cls="co-results",
        )
    else:
        results = Div(
            P("No companies found. Try a different search.", cls="co-empty"),
            cls="co-results",
        )

    from routes.analytics import copilot_pane, copilot_toggle_btn

    body = Body(
        Div(id="left-overlay", cls="left-overlay", onclick="toggleLeftPane()"),
        left_pane(
            user_email=user_email,
            current_path="/app/companies",
            current_role=current_role,
        ),
        Div(
            Div(
                Div(
                    Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()"),
                    Span("Companies", cls="chat-header-title"),
                    cls="chat-header-left",
                ),
                Div(copilot_toggle_btn(), cls="chat-header-actions"),
                cls="chat-header",
            ),
            Div(search_bar, results, cls="companies-wrap"),
            cls="center-pane pipeline-center",
        ),
        copilot_pane(
            page_name="Companies",
            page_context={"page": "Companies", "capabilities": "search, filter, browse company directory"},
        ),
        Script(src="/chat.js?v=2"),
        Script(src="/copilot.js"),
        cls="lr-dark app pane-closed pipeline-app",
        style="background:#0B1220;color:#E5E7EB;",
    )

    return Html(_head("Companies · LiquidRound"), body, lang="en")


# ── Company detail/overview page ────────────────────────────────────────

@ar("/app/company/{slug}")
def company_detail(slug: str, sess):
    from components.chat_shell import left_pane

    user_email = sess.get("email") if sess else None
    current_role = sess.get("role", "buyer") if sess else "buyer"

    co = _fetch_one(
        f"SELECT * FROM {DB_SCHEMA}.companies WHERE slug = %s", (slug,)
    )

    if not co:
        body = Body(
            Div(id="left-overlay", cls="left-overlay", onclick="toggleLeftPane()"),
            left_pane(
                user_email=user_email,
                current_path="/app/companies",
                current_role=current_role,
            ),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()"),
                        Span("Company not found", cls="chat-header-title"),
                        cls="chat-header-left",
                    ),
                    cls="chat-header",
                ),
                Div(
                    P("The requested company could not be found."),
                    A("← Back to Companies", href="/app/companies", cls="co-back-link"),
                    cls="companies-wrap", style="padding:2rem;",
                ),
                cls="center-pane pipeline-center",
            ),
            Script(src="/chat.js?v=2"),
            cls="lr-dark app pipeline-app",
            style="background:#0B1220;color:#E5E7EB;",
        )
        return Html(_head("Not found · LiquidRound"), body, lang="en")

    # Compute margin from actual data
    revenue = co.get("revenue_ltm")
    ebitda = co.get("ebitda_ltm")
    margin_computed = None
    if revenue and ebitda:
        try:
            margin_computed = round(float(ebitda) / float(revenue) * 100, 1)
        except (ValueError, ZeroDivisionError):
            pass

    margin_display = f"{margin_computed}%" if margin_computed is not None else (
        f"{float(co['ebitda_margin']):.1f}%" if co.get("ebitda_margin") else "—"
    )

    name = co.get("name", slug)
    sector = co.get("sector", "")
    sub_sector = co.get("sub_sector", "")
    stage = co.get("deal_stage", "sourced")
    description = co.get("description") or co.get("business_description") or ""

    # Tags row
    tags = []
    if sector:
        tags.append(Span(
            sector.replace("_", " ").title(),
            style=(
                "background:rgba(245,158,11,.15);color:#F59E0B;"
                "padding:2px 10px;border-radius:4px;font-size:.72rem;"
                "font-weight:500;"
            ),
        ))
    if sub_sector:
        tags.append(Span(
            sub_sector.replace("_", " ").title(),
            style=(
                "background:rgba(156,163,175,.15);color:#9CA3AF;"
                "padding:2px 10px;border-radius:4px;font-size:.72rem;"
                "font-weight:500;"
            ),
        ))
    tags.append(_stage_badge(stage))

    # KV grid
    kv_items = [
        ("HQ", f"{co.get('hq_city') or '—'}, {co.get('country') or '—'}"),
        ("Country", co.get("country") or "—"),
        ("Employees", _fmt_int(co.get("employees"))),
        ("Founded", str(co.get("founded_year") or "—")),
        ("Ownership", (co.get("ownership") or "—").replace("_", " ").title()),
    ]
    kv_grid = Div(
        *[Div(
            Span(k, cls="co-kv-label"),
            Span(v, cls="co-kv-value"),
            cls="co-kv-item",
        ) for k, v in kv_items],
        cls="co-kv-grid",
    )

    # Financial metric cards
    growth_rate = co.get("growth_rate")
    ev = co.get("enterprise_value")
    ask_multiple = co.get("ask_multiple")

    fin_cards = Div(
        _fin_card("Revenue LTM", _fmt_money(revenue)),
        _fin_card("EBITDA LTM", _fmt_money(ebitda)),
        _fin_card("Margin", margin_display),
        _fin_card("Growth Rate", f"{float(growth_rate):+.1f}%" if growth_rate else "—"),
        _fin_card("Enterprise Value", _fmt_money(ev)),
        _fin_card("Ask Multiple", f"{float(ask_multiple):.1f}x" if ask_multiple else "—"),
        cls="co-fin-grid",
    )

    # Description
    desc_section = Div(
        H4("Description", cls="co-section-title"),
        P(description or "No description available.", cls="co-description-text"),
        cls="co-description",
    ) if True else None

    # Center pane
    center = Div(
        Div(
            Div(
                Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()"),
                A("← Companies", href="/app/companies", cls="co-back-btn"),
                Span(name, cls="chat-header-title"),
                _stage_badge(stage),
                cls="chat-header-left",
            ),
            cls="chat-header",
        ),
        Div(
            Div(
                H2(name, cls="co-detail-name"),
                Div(*tags, cls="co-tags-row"),
                cls="co-detail-header",
            ),
            kv_grid,
            fin_cards,
            desc_section,
            cls="companies-wrap",
        ),
        cls="center-pane pipeline-center",
    )

    # Right pane — deal brief + download buttons
    brief_html = _deal_brief_html(co, margin_display)

    right = Div(
        Div(
            Div(
                Span("Deal Brief", cls="right-header-title",
                     style="font-weight:600;font-size:.85rem;color:#E5E7EB;"),
                cls="right-header-left",
            ),
            Button("✕", cls="right-close", onclick="closeRightPane()", type="button"),
            cls="right-header",
        ),
        Div(
            NotStr(brief_html),
            Div(
                A("⬇ CSV", href=f"/app/company/{slug}/csv",
                  style="display:inline-block;padding:.35rem .8rem;font-size:.72rem;"
                        "font-weight:600;border:1px solid rgba(245,158,11,.4);"
                        "border-radius:.4rem;color:#F59E0B;text-decoration:none;"
                        "margin-right:.5rem;transition:all .15s;",
                ),
                A("⬇ PDF", href=f"/app/company/{slug}/pdf",
                  style="display:inline-block;padding:.35rem .8rem;font-size:.72rem;"
                        "font-weight:600;border:1px solid rgba(245,158,11,.4);"
                        "border-radius:.4rem;color:#F59E0B;text-decoration:none;"
                        "transition:all .15s;",
                ),
                style="margin-top:1rem;padding-top:.8rem;border-top:1px solid rgba(255,255,255,.08);",
            ),
            cls="right-body",
            style="padding:1rem;overflow-y:auto;",
        ),
        id="right-pane", cls="right-pane open",
    )

    body = Body(
        Div(id="left-overlay", cls="left-overlay", onclick="toggleLeftPane()"),
        left_pane(
            user_email=user_email,
            current_path="/app/companies",
            current_role=current_role,
        ),
        center,
        right,
        Script(src="/chat.js?v=2"),
        cls="lr-dark app pipeline-app",
        style="background:#0B1220;color:#E5E7EB;",
    )

    return Html(_head(f"{name} · LiquidRound"), body, lang="en")


def _fin_card(label: str, value: str):
    return Div(
        Span(label, style=(
            "display:block;font-size:.68rem;color:#9CA3AF;"
            "text-transform:uppercase;letter-spacing:.05em;margin-bottom:.25rem;"
        )),
        Span(value, style=(
            "display:block;font-size:1.1rem;font-weight:600;color:#E5E7EB;"
            "font-family:'JetBrains Mono',monospace;"
        )),
        style=(
            "background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);"
            "border-radius:8px;padding:.75rem 1rem;"
        ),
    )


def _deal_brief_html(co: dict, margin_display: str) -> str:
    """Build the deal-brief HTML string for the right pane."""
    name = co.get("name", "")
    sector = co.get("sector", "")
    sub_sector = co.get("sub_sector", "")
    stage = co.get("deal_stage", "sourced")
    description = co.get("description") or co.get("business_description") or ""

    # Tags
    tags_html = ""
    if sector:
        tags_html += (
            f'<span style="background:rgba(245,158,11,.15);color:#F59E0B;'
            f'padding:2px 8px;border-radius:4px;font-size:.68rem;font-weight:500;'
            f'margin-right:4px;">{sector.replace("_", " ").title()}</span>'
        )
    if sub_sector:
        tags_html += (
            f'<span style="background:rgba(156,163,175,.15);color:#9CA3AF;'
            f'padding:2px 8px;border-radius:4px;font-size:.68rem;font-weight:500;'
            f'margin-right:4px;">{sub_sector.replace("_", " ").title()}</span>'
        )
    stage_colors = {
        "sourced": "#9CA89E", "screened": "#7A9E88", "loi": "#C89B5B",
        "diligence": "#B57D3E", "ic": "#4A8E66", "signed": "#2F7151",
        "closed": "#1F5D43", "held": "#3C5748", "exited": "#6B4E2F",
        "passed": "#9C8F7A",
    }
    sc = stage_colors.get(stage, "#9CA89E")
    tags_html += (
        f'<span style="background:{sc};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:.68rem;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:.06em;">'
        f'{(stage or "sourced").replace("_", " ").title()}</span>'
    )

    # KV rows
    def _kv(label: str, value: str) -> str:
        return (
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:4px 0;border-bottom:1px solid rgba(255,255,255,.06);">'
            f'<span style="color:#9CA3AF;font-size:.78rem;">{label}</span>'
            f'<span style="color:#E5E7EB;font-size:.78rem;font-weight:500;">{value}</span>'
            f'</div>'
        )

    hq = f"{co.get('hq_city') or '—'}, {co.get('country') or '—'}"

    kv_section = (
        _kv("HQ", hq)
        + _kv("Employees", _fmt_int(co.get("employees")))
        + _kv("Founded", str(co.get("founded_year") or "—"))
        + _kv("Ownership", (co.get("ownership") or "—").replace("_", " ").title())
    )

    # Financials
    fin_section = (
        _kv("Revenue (LTM)", _fmt_money(co.get("revenue_ltm")))
        + _kv("EBITDA (LTM)", _fmt_money(co.get("ebitda_ltm")))
        + _kv("Margin", margin_display)
        + _kv("Enterprise Value", _fmt_money(co.get("enterprise_value")))
        + _kv("Ask Multiple",
              f"{float(co['ask_multiple']):.1f}x" if co.get("ask_multiple") else "—")
    )

    # Truncate description for brief
    desc = description[:300] + ("..." if len(description) > 300 else "")

    return f"""
<div style="font-family:Inter,sans-serif;">
  <h3 style="margin:0 0 .5rem;font-size:1rem;font-weight:600;color:#E5E7EB;">
    {name}
  </h3>
  <div style="margin-bottom:.75rem;display:flex;flex-wrap:wrap;gap:4px;">
    {tags_html}
  </div>
  <div style="margin-bottom:1rem;">
    {kv_section}
  </div>
  <h4 style="margin:.75rem 0 .35rem;font-size:.78rem;font-weight:600;
             color:#9CA3AF;text-transform:uppercase;letter-spacing:.06em;">
    LTM Financials
  </h4>
  <div style="margin-bottom:1rem;">
    {fin_section}
  </div>
  <h4 style="margin:.75rem 0 .35rem;font-size:.78rem;font-weight:600;
             color:#9CA3AF;text-transform:uppercase;letter-spacing:.06em;">
    Description
  </h4>
  <p style="color:#D1D5DB;font-size:.78rem;line-height:1.5;margin:0;">
    {desc or "No description available."}
  </p>
</div>
"""
