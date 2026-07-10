"""Daily M&A Deal Radar — in-app view of top buyer↔target synergy pairs,
scoring methodology, and data-coverage stats.

/app/deal-radar    -> ranked pairs by country
/app/methodology   -> synergy scoring methodology (rendered markdown)
/app/data-coverage -> pool stats + register sync triggers
"""
from __future__ import annotations

from pathlib import Path

import logging
import threading

from fasthtml.common import (Div, Span, H1, H2, H3, P, A, NotStr, Button,
                             Table, Thead, Tbody, Tr, Th, Td, Title, Script)
from fasthtml.core import APIRouter
from starlette.responses import JSONResponse

ar = APIRouter()
log = logging.getLogger(__name__)


def _shell(session, *, title: str, header_title: str, header_sub: str,
           content, current_path: str):
    from components.chat_shell import left_pane, right_pane
    user = session.get("user")
    email = user.get("email") if user else None
    sessions_list = []
    if user and user.get("user_id"):
        try:
            from utils.database import db_service
            convs = db_service.get_user_conversations(user["user_id"], limit=20) or []
            sessions_list = [{"id": c["id"],
                              "title": c.get("conversation_title") or c.get("user_query", "Untitled")}
                             for c in convs]
        except Exception:
            pass
    header = Div(
        Div(
            Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span(header_title, cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span(header_sub, cls="chat-header-agent"),
            cls="chat-header-left",
        ),
        cls="chat-header",
    )
    return (
        Title(title),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(user_email=email, sessions=sessions_list, current_sid="",
                      current_path=current_path,
                      current_currency=session.get("currency", "EUR"),
                      current_role=session.get("role", "buyer")),
            Div(header, Div(content, cls="overflow-y-auto flex-1"), cls="center-pane"),
            right_pane(),
            cls="app pane-closed",
        ),
        Script(src="/chat.js?v=2"),
    )

DATA_SOURCES = [
    ("Estonia",   "🟢 Live",   "RIK e-Business Register (open bulk, 374k + status)",
     "EMTA Tax Board turnover open data (VAT-based)", "Fully open — 43.5k targets ≥ €100k"),
    ("Denmark",   "🟡 Phase 2","CVR / data.virk.dk (open)",
     "Annual reports open but XBRL / credentialed CVR distribution", "Needs XBRL parse or CVR creds"),
    ("Norway",    "🟢 Live",   "Brønnøysund BRREG open API (426k AS)",
     "Regnskapsregisteret open API (per-company)", "Live — per-company fetch, ~10/s"),
    ("Latvia",    "🟢 Held",   "data.gov.lv (open)",
     "Annual-report open data", "24.5k LV already in pool"),
    ("Lithuania", "🟡 Scrape", "rekvizitai.lt (browser UA works) / Registrų centras",
     "Revenue is JS-rendered → needs a headless browser; RC statements paid", "~2.3k pooled, 522 covered"),
    ("Poland",    "🟡 Phase 2","KRS open API + REGON",
     "Financials free but per-company XML (RDF repository)", "Data free, financials fiddly"),
    ("Finland",   "🟡 Phase 2","PRH / YTJ open API",
     "Financials paid (Asiakastieto / PRH)", "Company data free, financials paid"),
    ("Sweden",    "🟡 Phase 2","Bolagsverket",
     "Financials semi-paid (allabolag scrape)", "Financials gated"),
]

BG_CARD, INK, MUTED, DIM, AMBER, LINE = "#111A2E", "#E5E7EB", "#94A3B8", "#64748B", "#F59E0B", "#1E293B"
GOOD, WARN, BAD = "#34D399", "#FBBF24", "#F87171"
_FLAG = {"Estonia": "🇪🇪", "Latvia": "🇱🇻", "Lithuania": "🇱🇹", "Norway": "🇳🇴",
         "Denmark": "🇩🇰", "Finland": "🇫🇮", "Sweden": "🇸🇪", "Poland": "🇵🇱"}


def _score_color(s: float) -> str:
    return GOOD if s >= 3.5 else (WARN if s >= 2.5 else BAD)


def _pair_row(p: dict):
    sc = float(p["composite_score"])
    rev = p.get("target_revenue_eur")
    rev_s = f"~€{float(rev)/1e6:.1f}M rev" if rev else ""
    mc = p.get("buyer_mktcap_usd")
    mc_s = f"${float(mc)/1e9:.1f}B mkt cap" if mc else ""
    return Div(
        Div(
            Div(
                Span("BUYER · PUBLIC", cls="mono", style=f"font-size:10px;color:{DIM};letter-spacing:.05em;"),
                Div(p["buyer_name"], style=f"font-size:15px;font-weight:700;color:{INK};"),
                Div(f"{p['buyer_ticker']} · {p.get('buyer_country') or ''} · {mc_s}",
                    style=f"font-size:11px;color:{MUTED};"),
                style="flex:1 1 42%;min-width:0;",
            ),
            Div(
                Span("→", style=f"font-size:20px;color:{AMBER};display:block;"),
                Span(f"{sc:.2f}", style=f"display:inline-block;background:{_score_color(sc)};color:#0B1220;"
                     "font-weight:800;font-size:15px;border-radius:8px;padding:2px 10px;margin-top:2px;"),
                style="flex:0 0 90px;text-align:center;",
            ),
            Div(
                Span("TARGET · PRIVATE", cls="mono",
                     style=f"font-size:10px;color:{DIM};letter-spacing:.05em;"),
                Div(p["target_name"], style=f"font-size:15px;font-weight:700;color:{INK};"),
                Div(f"{p.get('target_sector') or ''} · {p.get('target_country') or ''} · {rev_s}",
                    style=f"font-size:11px;color:{MUTED};"),
                style="flex:1 1 42%;min-width:0;text-align:right;",
            ),
            style="display:flex;align-items:center;gap:12px;",
        ),
        Div(
            Span(f"{p.get('recommendation') or ''}. ",
                 style=f"color:{_score_color(sc)};font-weight:600;"),
            Span(p.get("reasoning") or "", style=f"color:{MUTED};"),
            style=f"font-size:12.5px;line-height:1.55;margin-top:10px;padding-top:10px;border-top:1px solid {LINE};",
        ),
        style=f"background:{BG_CARD};border:1px solid {LINE};border-radius:12px;padding:16px;margin-bottom:12px;",
    )


def _deal_radar_content():
    from utils.deal_radar import get_latest_pairs
    try:
        pairs = get_latest_pairs(limit=25)
    except Exception:
        pairs = []
    run = pairs[0].get("run_date") if pairs else None

    header = Div(
        Div(
            H1("Daily M&A Deal Radar", cls="text-2xl font-bold", style=f"color:{INK};"),
            Span(str(run) if run else "", cls="mono", style=f"font-size:12px;color:{MUTED};"),
            style="display:flex;align-items:baseline;gap:12px;",
        ),
        P(NotStr("Top scored M&A pairs <b>by country</b> — each matches a <b>public buyer</b> "
                 "(any global exchange, via Yahoo Finance) with a <b>private target</b>, scored on "
                 "the 5-bucket synergy methodology (cost · revenue · strategic · financial · "
                 "organizational, weighted 1–5)."),
          style=f"font-size:13px;color:{MUTED};margin-top:6px;max-width:680px;"),
        Div(
            A("Scoring methodology →", href="/app/methodology",
              style=f"color:{AMBER};font-size:12px;font-weight:600;margin-right:16px;"),
            A("Edit the scorer prompt →", href="/app/instructions/deal_radar_synergy",
              style=f"color:{AMBER};font-size:12px;font-weight:600;"),
            style="margin-top:10px;",
        ),
        style="margin-bottom:18px;",
    )

    if not pairs:
        body = Div(P("No pairs scored yet — the Deal Radar runs daily (07:00 UTC). "
                     "Run `python -m scripts.build_deal_radar` to populate now.",
                     style=f"color:{MUTED};font-size:13px;"),
                   style=f"background:{BG_CARD};border:1px solid {LINE};border-radius:12px;padding:20px;")
    else:
        groups: dict = {}
        for p in pairs:
            groups.setdefault(p.get("target_country") or "Other", []).append(p)
        ordered = sorted(groups.items(),
                         key=lambda kv: -max(float(x["composite_score"]) for x in kv[1]))
        sections = []
        for country, cps in ordered:
            sections.append(Div(
                Span(f"{_FLAG.get(country,'')} {country}",
                     style=f"font-size:15px;font-weight:700;color:{INK};"),
                Span(f"· {len(cps)} deals", style=f"font-size:12px;color:{MUTED};margin-left:8px;"),
                style=f"margin:18px 0 10px;padding-bottom:5px;border-bottom:2px solid {AMBER};"))
            sections.extend(_pair_row(p) for p in cps)
        body = Div(*sections)

    return Div(header, body, cls="max-w-4xl mx-auto w-full", style="padding:24px 20px;")


@ar("/app/deal-radar")
def deal_radar_page(session):
    return _shell(
        session, title="Deal Radar · LiquidRound",
        header_title="Daily M&A Deal Radar", header_sub="Buyer ↔ target synergy pairs",
        content=_deal_radar_content(), current_path="/app/deal-radar")


# ── Data Coverage ───────────────────────────────────────────────────────────

def _pool_stats() -> list[dict]:
    from utils.database import get_conn
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT country,
                  count(*)                                                          AS total,
                  count(*) FILTER (WHERE estimated_revenue_eur >= 100000)           AS covered,
                  count(*) FILTER (WHERE sector IS NOT NULL AND sector <> '')       AS with_sector,
                  count(*) FILTER (WHERE reg_code IS NOT NULL)                      AS with_regcode,
                  count(*) FILTER (WHERE estimated_ebitda_eur IS NOT NULL)          AS with_ebitda,
                  round(percentile_cont(0.5) WITHIN GROUP (ORDER BY estimated_revenue_eur)
                        FILTER (WHERE estimated_revenue_eur > 0))                   AS median_rev,
                  count(DISTINCT source)                                            AS n_sources
                FROM liquidround.deal_candidates
                WHERE COALESCE(is_active, TRUE)
                GROUP BY country ORDER BY count(*) DESC
            """)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


def _data_coverage_content():
    src_rows = [Tr(
        Td(name, style=f"font-weight:600;color:{INK};"),
        Td(status, cls="mono", style="font-size:12px;"),
        Td(comp, style=f"color:{MUTED};font-size:12px;"),
        Td(fin, style=f"color:{MUTED};font-size:12px;"),
        Td(verdict, style=f"color:{MUTED};font-size:12px;"),
        style=f"border-top:1px solid {LINE};",
    ) for name, status, comp, fin, verdict in DATA_SOURCES]

    pool = _pool_stats()
    total_cov = sum(r["covered"] for r in pool)

    def _held(r):
        bits = []
        if r["covered"]:
            bits.append("revenue")
        if r["with_ebitda"]:
            bits.append("EBITDA")
        if r["with_sector"]:
            bits.append("sector")
        if r["with_regcode"]:
            bits.append("reg-code")
        return " · ".join(bits) or "names only"

    def _num(v, color=INK):
        return Td(f"{v:,}" if v else "—", cls="mono", style=f"color:{color};font-size:12px;")

    pool_rows = [Tr(
        Td(r["country"], style=f"color:{INK};font-weight:600;"),
        _num(r["total"]),
        _num(r["covered"], GOOD),
        _num(r["with_sector"]),
        _num(r["with_ebitda"]),
        Td(f"€{float(r['median_rev'])/1e6:.2f}M" if r["median_rev"] else "—",
           cls="mono", style=f"color:{MUTED};font-size:12px;"),
        Td(_held(r), style=f"color:{MUTED};font-size:12px;"),
        style=f"border-top:1px solid {LINE};",
    ) for r in pool]

    pool_section = ""
    if pool_rows:
        heads = ("Country", "In pool", "Covered ≥€100k", "With sector",
                 "With EBITDA", "Median rev.", "Data held")
        pool_section = Div(
            H3("What we hold, by country (live from the database)",
               cls="text-sm font-semibold mt-6 mb-2", style=f"color:{INK};"),
            Div(Table(
                Thead(Tr(*[Th(h, style=f"text-align:left;color:{MUTED};font-size:11px;"
                              "text-transform:uppercase;white-space:nowrap;") for h in heads])),
                Tbody(*pool_rows), cls="w-full",
                style=f"background:{BG_CARD};border:1px solid {LINE};border-radius:12px;"
                      "border-collapse:collapse;min-width:640px;"),
                style="overflow-x:auto;"),
        )

    return Div(
        H1("Data Coverage", cls="text-2xl font-bold", style=f"color:{INK};"),
        P(NotStr("Where LiquidRound sources <b>private-company data + financials</b> for the "
                 "Deal Radar target pool. Open registries (🟢) give free financials at scale; "
                 "🟡 need scraping or paid feeds."),
          style=f"font-size:13px;color:{MUTED};margin:6px 0 16px;max-width:720px;"),
        Div(
            Div(f"{total_cov:,}", style=f"font-size:30px;font-weight:800;color:{INK};"),
            Div("covered targets (≥ €100k revenue, active)", style=f"font-size:12px;color:{MUTED};"),
            Div(
                Button("↻ Sync Estonia now", hx_post="/app/sync/ee", hx_target="#sync-status",
                       hx_swap="innerHTML",
                       style=f"background:{AMBER};color:#0B1220;font-weight:700;font-size:12px;"
                       "border:none;border-radius:8px;padding:8px 14px;cursor:pointer;margin-top:10px;"),
                Button("↻ Sync Norway now", hx_post="/app/sync/no", hx_target="#sync-status",
                       hx_swap="innerHTML",
                       style=f"background:transparent;color:{AMBER};font-weight:700;font-size:12px;"
                       f"border:1px solid {AMBER};border-radius:8px;padding:8px 14px;cursor:pointer;margin:10px 0 0 8px;"),
                Span(id="sync-status", cls="mono", style=f"font-size:11px;color:{MUTED};margin-left:10px;"),
            ),
            style=f"background:{BG_CARD};border:1px solid {LINE};border-radius:12px;padding:18px;margin-bottom:16px;",
        ),
        Table(
            Thead(Tr(*[Th(h, style=f"text-align:left;color:{MUTED};font-size:11px;text-transform:uppercase;")
                       for h in ("Country", "Status", "Company data", "Financials", "Verdict")])),
            Tbody(*src_rows),
            cls="w-full", style=f"background:{BG_CARD};border:1px solid {LINE};border-radius:12px;border-collapse:collapse;",
        ),
        pool_section,
        cls="max-w-4xl mx-auto w-full", style="padding:24px 20px;",
    )


@ar("/app/data-coverage")
def data_coverage_page(session):
    return _shell(
        session, title="Data Coverage · LiquidRound",
        header_title="Data Coverage", header_sub="Company + financials sources",
        content=_data_coverage_content(), current_path="/app/data-coverage")


@ar("/app/sync/ee", methods=["POST"])
def sync_ee_trigger(session):
    def _job():
        try:
            from scripts.sync_ee_register import main
            r = main(refresh=True)
            log.info("Manual EE sync: %s", r)
        except Exception:
            log.exception("Manual EE sync failed")
    threading.Thread(target=_job, daemon=True, name="ee-sync-manual").start()
    return Span("Estonia sync started — refreshing (~1 min), reload shortly.", style=f"color:{GOOD};")


@ar("/app/sync/no", methods=["POST"])
def sync_no_trigger(session):
    def _job():
        try:
            from scripts.sync_no_register import main
            log.info("Manual NO sync: %s", main(target=3000))
        except Exception:
            log.exception("Manual NO sync failed")
    threading.Thread(target=_job, daemon=True, name="no-sync-manual").start()
    return Span("Norway sync started — collecting ~3k covered (~5 min).", style=f"color:{GOOD};")


@ar("/app/methodology")
def methodology_page(session):
    from routes.help import _md_to_components
    md_path = Path(__file__).resolve().parent.parent / "docs" / "synergy_methodology.md"
    md = md_path.read_text() if md_path.exists() else "# Methodology\n\nComing soon."
    content = Div(
        Div(*_md_to_components(md), cls="guide-content"),
        cls="max-w-3xl mx-auto w-full", style="padding:24px 20px;",
    )
    return _shell(
        session, title="Synergy Methodology · LiquidRound",
        header_title="Synergy Scoring Methodology", header_sub="How the Deal Radar scores pairs",
        content=content, current_path="/app/methodology")
