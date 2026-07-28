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
    if value in (None, ""):
        return "—"
    value = float(value)
    return f"${value / 1e9:.1f}B" if value >= 1e9 else f"${value / 1e6:.1f}M"


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


def filter_bar(active_tab: str = "all"):
    tabs = (
        ("all", "All transactions"),
        ("reverse", "Reverse mergers / RTOs"),
        ("spac", "SPAC comparison"),
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
            Select(Option("All jurisdictions", value=""), Option("United States", value="US"),
                   Option("Canada", value="CA"), name="jurisdiction", cls="rto-control"),
            Select(Option("All statuses", value=""), Option("Candidate", value="candidate"),
                   Option("Announced", value="announced"), Option("Completed", value="completed"),
                   Option("Terminated", value="terminated"), name="status", cls="rto-control"),
            Input(name="q", placeholder="Company, target, ticker…", cls="rto-control"),
            Input(type="hidden", name="tab", value=active_tab),
            Button("Apply", type="submit", cls="rto-primary"),
            method="get", action="/app/reverse-mergers", cls="rto-filters",
        ) if active_tab not in {"methodology", "import"} else None,
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
                   Span(row.get("public_company") or "—", style=f"color:{INK};font-size:12px;"),
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
                P("Reviewed metadata only until licensed bulk access is available. The application does not crawl or mirror SEDAR+.", cls="rto-card-copy")),
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
            Div(Label("Reviewed summary"), Textarea(name="summary", rows="4", cls="rto-control"), cls="rto-field rto-wide"),
            Input(type="hidden", name="jurisdiction", value="CA"),
            Button("Add reviewed record", type="submit", cls="rto-primary rto-wide"),
            hx_post="/app/reverse-mergers/import", hx_target="#rto-import-result",
            hx_swap="innerHTML", cls="rto-import-grid",
        ),
        Div(id="rto-import-result"),
    )


def page_content(rows: list[dict], active_tab: str):
    if active_tab == "methodology":
        content = methodology_panel()
    elif active_tab == "import":
        content = import_panel()
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
                A("Ask RTO Analyst", href="/app?q=rto%3A+summarize+recent+reverse+mergers", cls="rto-secondary"),
                id="rto-sync-result", style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;",
            ),
            cls="rto-hero",
        ),
        summary_cards(rows),
        filter_bar(active_tab),
        content,
        cls="rto-page",
    )
