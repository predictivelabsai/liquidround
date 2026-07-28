"""Reverse Mergers workspace components."""
from __future__ import annotations

from fasthtml.common import *

BG, CARD, LINE = "#0B1220", "#111A2E", "#1E293B"
INK, MUTED, AMBER, BLUE, GREEN, RED = "#F8FAFC", "#94A3B8", "#F59E0B", "#3B82F6", "#10B981", "#EF4444"

TYPE_LABELS = {
    "us_reverse_merger": "US reverse merger",
    "us_de_spac": "US de-SPAC",
    "ca_rto": "Canadian RTO",
    "ca_cpc_qt": "Canadian CPC QT",
    "ca_spac_qa": "Canadian SPAC QA",
}


def _money(value) -> str:
    if value in (None, "", 0, 0.0):
        return "—"
    value = float(value)
    if value >= 1e9:
        return f"${value / 1e9:.1f}B"
    if value >= 1e6:
        return f"${value / 1e6:.1f}M"
    return f"${value / 1e3:.0f}K" if value >= 1e3 else "<$1K"


def _badge(text: str, color: str = BLUE):
    return Span(text, style=f"color:{color};border:1px solid {color};border-radius:999px;padding:2px 7px;font-size:10px;white-space:nowrap;")


def summary_cards(rows: list[dict]):
    reverse = [r for r in rows if "spac" not in r["transaction_type"]]
    spacs = [r for r in rows if "spac" in r["transaction_type"]]
    completed = sum(str(r.get("status", "")).lower() == "completed" for r in rows)
    canada = sum(r.get("jurisdiction") == "CA" for r in rows)
    cards = (
        ("Reverse mergers", len(reverse), BLUE),
        ("SPAC / de-SPAC", len(spacs), AMBER),
        ("Completed", completed, GREEN),
        ("Canadian records", canada, RED),
    )
    return Div(*(
        Div(Div(str(value), style=f"font-size:25px;font-weight:750;color:{color}"),
            Div(label, style=f"font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:{MUTED}"),
            style=f"background:{CARD};border:1px solid {LINE};border-radius:10px;padding:14px;text-align:center;")
        for label, value, color in cards
    ), style="display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin-bottom:18px;")


def filter_bar(active_tab: str = "all", filters: dict | None = None):
    filters = filters or {}
    tabs = (
        ("all", "All transactions"),
        ("reverse", "Reverse mergers / RTOs"),
        ("spac", "SPAC comparison"),
        ("news", "Merger news"),
        ("methodology", "Methodology"),
        ("import", "Canadian manual import"),
    )
    return Div(
        Div(*(
            A(label, href=f"/app/reverse-mergers?tab={key}",
              cls="rto-tab active" if key == active_tab else "rto-tab")
            for key, label in tabs
        ), cls="rto-tabs"),
        Form(
            Select(Option("All jurisdictions", value="", selected=not filters.get("jurisdiction")),
                   Option("United States", value="US", selected=filters.get("jurisdiction") == "US"),
                   Option("Canada", value="CA", selected=filters.get("jurisdiction") == "CA"),
                   name="jurisdiction", cls="rto-control"),
            Select(Option("Completed + not completed", value="", selected=not filters.get("status")),
                   Option("Completed", value="completed", selected=filters.get("status") == "completed"),
                   Option("Not completed", value="not_completed", selected=filters.get("status") == "not_completed"),
                   name="status", cls="rto-control"),
            Select(Option("Targets: all", value="", selected=not filters.get("has_target")),
                   Option("Target identified", value="yes", selected=filters.get("has_target") == "yes"),
                   Option("Target missing", value="no", selected=filters.get("has_target") == "no"),
                   name="has_target", cls="rto-control"),
            Select(Option("Deal value: all", value="", selected=not filters.get("has_value")),
                   Option("Deal value disclosed", value="yes", selected=filters.get("has_value") == "yes"),
                   Option("Deal value missing", value="no", selected=filters.get("has_value") == "no"),
                   name="has_value", cls="rto-control"),
            Input(name="q", value=filters.get("q", ""),
                  placeholder="Company, target, ticker…", cls="rto-control rto-search"),
            Input(type="hidden", name="tab", value=active_tab),
            Button("Apply", type="submit", cls="rto-primary"),
            method="get", action="/app/reverse-mergers", cls="rto-filters",
        ) if active_tab not in {"methodology", "import", "news"} else None,
    )


def transaction_table(rows: list[dict]):
    if not rows:
        return Div(
            H3("No matching transactions yet", style=f"color:{INK};font-size:16px;margin-bottom:6px;"),
            P("Run the EDGAR sync after applying SQL migration 18, or add a reviewed Canadian record.",
              style=f"color:{MUTED};font-size:13px;"),
            cls="rto-empty",
        )
    body = []
    for row in rows:
        kind = row.get("transaction_type", "")
        color = AMBER if "spac" in kind else BLUE
        source = row.get("source_url", "")
        body.append(Tr(
            Td(Div(Span(row.get("public_ticker") or "—", style=f"color:{AMBER};font-weight:700;"),
                   Span(row.get("public_company") or "—",
                        title=row.get("public_company") or "", cls="rto-company-name"),
                   style="display:flex;flex-direction:column;gap:2px;"), cls="rto-td"),
            Td(_badge(TYPE_LABELS.get(kind, kind.replace("_", " ")), color), cls="rto-td"),
            Td(_badge(row.get("jurisdiction", "—"), GREEN if row.get("jurisdiction") == "CA" else BLUE), cls="rto-td"),
            Td(row.get("private_target") or "—", cls="rto-td"),
            Td(str(row.get("announcement_date") or "—")[:10], cls="rto-td"),
            Td(_money(row.get("deal_value")), cls="rto-td"),
            Td(_badge(str(row.get("status") or "candidate").title(), MUTED), cls="rto-td"),
            Td(A("Source ↗", href=source, target="_blank", rel="noopener",
                 style=f"color:{AMBER};text-decoration:none;") if source else "—", cls="rto-td"),
        ))
    return Div(Table(
        Thead(Tr(*(Th(x, cls="rto-th") for x in
                   ("Public vehicle", "Structure", "Market", "Private target", "Announced", "Deal value", "Status", "Evidence")))),
        Tbody(*body), cls="rto-table"), cls="rto-table-wrap")


def methodology_panel():
    return Div(
        H2("Classification methodology", style=f"color:{INK};font-size:18px;margin-bottom:10px;"),
        P("LiquidRound separates traditional reverse mergers from de-SPACs, then normalizes both into one comparison model.",
          style=f"color:{MUTED};font-size:13px;margin-bottom:14px;"),
        Div(
            Div(H3("US reverse merger", cls="rto-card-title"),
                P("Detected from SEC 8-K Items 1.01, 2.01, 5.01, 5.06 and 9.01; shell-exit and change-of-control language drive confidence.", cls="rto-card-copy")),
            Div(H3("SPAC / de-SPAC", cls="rto-card-title"),
                P("Trust, redemption, sponsor and business-combination signals classify the purpose-built shell separately.", cls="rto-card-copy")),
            Div(H3("Canadian RTO / CPC", cls="rto-card-title"),
                P("Discovered from sedarplus.ca via a headless Chromium scraper that reads the public document search, downloads filings, and parses them through the same document-intelligence pipeline as EDGAR. Metadata and a content hash are stored; documents are not mirrored.", cls="rto-card-copy")),
            cls="rto-method-grid",
        ),
        Div(
            H3("Three-year US coverage", cls="rto-card-title"),
            P("The EDGAR synchronization searches recent 8-K disclosures, reads primary filings, records evidence signals, and stores canonical SEC links. Every derived classification retains confidence and review status.", cls="rto-card-copy"),
            style=f"margin-top:12px;background:{CARD};border:1px solid {LINE};border-radius:10px;padding:16px;",
        ),
    )


def import_panel():
    return Div(
        H2("Add a reviewed Canadian transaction", style=f"color:{INK};font-size:18px;margin-bottom:6px;"),
        P("Enter metadata from a public source one transaction at a time. LiquidRound stores the citation, not a mirrored SEDAR+ document.",
          style=f"color:{MUTED};font-size:13px;margin-bottom:16px;"),
        Form(
            Div(Label("Public company *"), Input(name="public_company", required=True, cls="rto-control"), cls="rto-field"),
            Div(Label("Ticker"), Input(name="public_ticker", cls="rto-control"), cls="rto-field"),
            Div(Label("Private target"), Input(name="private_target", cls="rto-control"), cls="rto-field"),
            Div(Label("Exchange"), Input(name="exchange", placeholder="TSXV / TSX", cls="rto-control"), cls="rto-field"),
            Div(Label("Structure *"), Select(
                Option("Canadian RTO", value="ca_rto"),
                Option("CPC qualifying transaction", value="ca_cpc_qt"),
                Option("Canadian SPAC qualifying acquisition", value="ca_spac_qa"),
                name="transaction_type", cls="rto-control"), cls="rto-field"),
            Div(Label("Announcement date"), Input(type="date", name="announcement_date", cls="rto-control"), cls="rto-field"),
            Div(Label("Public source URL *"), Input(type="url", name="source_url", required=True, cls="rto-control"), cls="rto-field rto-wide"),
            Div(Label("Source document (optional)"),
                Input(type="file", name="source_document",
                      accept=".pdf,.html,.htm,.xml,.txt", cls="rto-control"),
                P("Upload a document you obtained manually or under licence. It is parsed in memory and not mirrored.",
                  style=f"color:{MUTED};font-size:11px;margin-top:5px;"),
                cls="rto-field rto-wide"),
            Div(Label("Reviewed summary"), Textarea(name="summary", rows="4", cls="rto-control"), cls="rto-field rto-wide"),
            Input(type="hidden", name="jurisdiction", value="CA"),
            Button("Add reviewed record", type="submit", cls="rto-primary rto-wide"),
            hx_post="/app/reverse-mergers/import", hx_target="#rto-import-result",
            hx_swap="innerHTML", enctype="multipart/form-data", cls="rto-import-grid",
        ),
        Div(id="rto-import-result"),
    )


def merger_news_panel(news_rows: list[dict], source: str = "", stage: str = ""):
    source_labels = {
        "globenewswire": "GlobeNewswire",
        "businesswire": "Business Wire",
        "prnewswire": "PR Newswire",
    }
    cards = []
    for row in news_rows:
        cards.append(Div(
            Div(
                _badge(source_labels.get(row["source"], row["source"]), AMBER),
                _badge(str(row.get("event_stage") or "other").title(), GREEN),
                _badge("Reverse merger", BLUE) if row.get("is_reverse_merger") else None,
                style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;",
            ),
            A(row["title"], href=row["source_url"], target="_blank", rel="noopener",
              style=f"color:{INK};font-size:15px;font-weight:650;text-decoration:none;line-height:1.35;"),
            P(row.get("summary") or "No feed summary supplied.",
              style=f"color:{MUTED};font-size:12px;line-height:1.5;margin:0;",
              cls="line-clamp-3"),
            Div(
                Span(str(row.get("published_at") or "")[:10] or "Date unavailable"),
                Span(f"Target: {row['target']}") if row.get("target") else None,
                Span(f"Value: {row['deal_value']}") if row.get("deal_value") else None,
                style=f"color:{MUTED};font-size:11px;display:flex;gap:12px;flex-wrap:wrap;",
            ),
            style=f"background:{CARD};border:1px solid {LINE};border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:9px;",
        ))
    return Div(
        Div(
            Div(H2("Merger announcement monitor", style=f"color:{INK};font-size:18px;margin:0;"),
                P("Filtered RSS releases from GlobeNewswire, Business Wire and PR Newswire.",
                  style=f"color:{MUTED};font-size:12px;margin:4px 0 0;")),
            Form(
                Select(
                    Option("All wires", value="", selected=not source),
                    *(Option(label, value=key, selected=source == key)
                      for key, label in source_labels.items()),
                    name="source", cls="rto-control",
                ),
                Select(
                    Option("All stages", value="", selected=not stage),
                    *(Option(value.title(), value=value, selected=stage == value)
                      for value in ("announced", "proposed", "approved", "completed", "terminated", "other")),
                    name="stage", cls="rto-control",
                ),
                Input(type="hidden", name="tab", value="news"),
                Button("Apply", type="submit", cls="rto-secondary"),
                Button("Sync feeds", type="button", cls="rto-primary",
                       hx_post="/app/reverse-mergers/sync-news",
                       hx_target="#merger-news-sync", hx_swap="innerHTML"),
                method="get", action="/app/reverse-mergers",
                style="display:flex;gap:8px;flex-wrap:wrap;",
            ),
            style="display:flex;justify-content:space-between;gap:14px;align-items:flex-end;flex-wrap:wrap;margin-bottom:14px;",
        ),
        Div(id="merger-news-sync"),
        Div(*cards, style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;")
        if cards else Div("No matching merger releases yet. Sync the feeds to populate this view.", cls="rto-empty"),
    )


def page_content(rows: list[dict], active_tab: str, news_rows: list[dict] | None = None,
                 news_source: str = "", news_stage: str = "",
                 filters: dict | None = None):
    if active_tab == "methodology":
        content = methodology_panel()
    elif active_tab == "import":
        content = import_panel()
    elif active_tab == "news":
        content = merger_news_panel(news_rows or [], news_source, news_stage)
    else:
        content = transaction_table(rows)
    return Div(
        Div(
            Div(H1("Reverse Mergers", style=f"color:{INK};font-size:24px;font-weight:750;"),
                P("RTO, shell and de-SPAC intelligence · United States + reviewed Canadian records",
                  style=f"color:{MUTED};font-size:13px;margin-top:4px;")),
            Div(
                Button("Sync 3y EDGAR", hx_post="/app/reverse-mergers/sync",
                       hx_target="#rto-sync-result", hx_swap="innerHTML", cls="rto-primary"),
                Button("Sync SEDAR+ (CA)", hx_post="/app/reverse-mergers/sync-sedar",
                       hx_target="#rto-sync-result", hx_swap="innerHTML", cls="rto-secondary"),
                A("Ask RTO Analyst", href="/app?q=rto%3A+summarize+recent+reverse+mergers", cls="rto-secondary"),
                id="rto-sync-result", style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;",
            ),
            cls="rto-hero",
        ),
        summary_cards(rows),
        filter_bar(active_tab, filters),
        content,
        cls="rto-page",
    )
