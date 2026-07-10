"""Deal Radar — unified two-tab view combining synergy pairs + daily targets.

/app/deal-radar       -> tabbed page: Synergies | Targets
/app/deal-radar/tab/* -> HTMX tab content
/app/methodology      -> synergy scoring methodology (rendered markdown)
/app/data-coverage    -> pool stats + register sync triggers
"""
from __future__ import annotations

from pathlib import Path

import logging
import threading

from fasthtml.common import (Div, Span, H1, H2, H3, P, A, NotStr, Button, Input,
                             Table, Thead, Tbody, Tr, Th, Td, Title, Script)
from fasthtml.core import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse

ar = APIRouter()
log = logging.getLogger(__name__)


def _shell(session, *, title: str, header_title: str, header_sub: str,
           content, current_path: str, extra_js: str = ""):
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
        Div(
            A("⬇ PDF", href=f"{current_path}/pdf",
              style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;"
                    "font-size:12px;font-weight:600;color:#F59E0B;"
                    "border:1px solid rgba(245,158,11,.4);border-radius:6px;"
                    "text-decoration:none;"),
            cls="chat-header-actions",
        ),
        cls="chat-header",
    )
    parts = [
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
    ]
    if extra_js:
        parts.append(Script(NotStr(extra_js)))
    return tuple(parts)


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


# ── Tab bar ──────────────────────────────────────────────────────────

_TAB_STYLE_ACTIVE = (f"background:{AMBER};color:#0B1220;font-weight:700;font-size:13px;"
                     "border:none;border-radius:8px 8px 0 0;padding:10px 20px;cursor:pointer;")
_TAB_STYLE_INACTIVE = (f"background:transparent;color:{MUTED};font-weight:600;font-size:13px;"
                       f"border:1px solid {LINE};border-bottom:none;border-radius:8px 8px 0 0;"
                       "padding:10px 20px;cursor:pointer;")


def _tab_bar(active: str):
    def _btn(label, tab_id):
        is_active = tab_id == active
        return Button(
            label,
            hx_get=f"/app/deal-radar/tab/{tab_id}",
            hx_target="#radar-tab-content",
            hx_swap="innerHTML",
            onclick=f"setActiveTab(this, '{tab_id}')",
            style=_TAB_STYLE_ACTIVE if is_active else _TAB_STYLE_INACTIVE,
            cls=f"radar-tab{' active' if is_active else ''}",
            type="button",
        )
    return Div(
        _btn("Synergies", "synergies"),
        _btn("Targets", "targets"),
        style=f"display:flex;gap:4px;border-bottom:2px solid {AMBER};padding:0 20px;",
    )


# ── Synergies tab content ────────────────────────────────────────────

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


def _synergies_content():
    from utils.deal_radar import get_latest_pairs
    try:
        pairs = get_latest_pairs(limit=25)
    except Exception:
        pairs = []
    run = pairs[0].get("run_date") if pairs else None

    intro = Div(
        Div(
            Span(str(run) if run else "No run yet", cls="mono",
                 style=f"font-size:12px;color:{MUTED};"),
            A("Methodology →", href="/app/methodology",
              style=f"color:{AMBER};font-size:12px;font-weight:600;margin-left:16px;"),
            A("Edit prompt →", href="/app/instructions/deal_radar_synergy",
              style=f"color:{AMBER};font-size:12px;font-weight:600;margin-left:12px;"),
            A("Data coverage →", href="/app/data-coverage",
              style=f"color:{AMBER};font-size:12px;font-weight:600;margin-left:12px;"),
            style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;",
        ),
        P(NotStr("Public buyer ↔ private target pairs scored on the <b>5-bucket synergy methodology</b> "
                 "(cost · revenue · strategic · financial · organizational, weighted 1–5)."),
          style=f"font-size:12px;color:{MUTED};margin-top:6px;max-width:680px;"),
        style="margin-bottom:14px;",
    )

    if not pairs:
        body = Div(P("No pairs scored yet — the Deal Radar runs daily at 05:00 UTC.",
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

    return Div(intro, body)


# ── Targets tab content ──────────────────────────────────────────────

def _target_card(c: dict, is_featured: bool = False):
    flag = _FLAG.get(c.get("country", ""), "")
    rev = c.get("estimated_revenue_eur")
    rev_s = f"€{float(rev)/1e6:.1f}M" if rev else ""
    ds = c.get("deal_size_estimate", "")
    ds_s = f" · {ds}" if ds and ds != "undisclosed" else ""

    header_parts = [
        Span(f"{flag} {c.get('name', 'N/A')}", style=f"font-size:15px;font-weight:700;color:{INK};"),
    ]
    if is_featured:
        header_parts.append(
            Span("DEEP DIVE", style=f"font-size:9px;font-weight:700;color:{AMBER};"
                 f"background:#1E293B;border:1px solid {AMBER};border-radius:4px;padding:2px 6px;"
                 "margin-left:8px;letter-spacing:.05em;vertical-align:middle;"))

    meta = f"{c.get('sector', '')} · {c.get('country', '')}"
    if rev_s:
        meta += f" · {rev_s} rev"
    meta += ds_s

    parts = [
        Div(*header_parts),
        Div(meta, style=f"font-size:11px;color:{MUTED};margin:2px 0 6px;"),
    ]
    if c.get("description"):
        parts.append(P(c["description"], style=f"font-size:12.5px;color:{INK};line-height:1.5;margin:0 0 4px;"))
    if c.get("deal_context"):
        parts.append(P(NotStr(f"<b style='color:{AMBER};'>Deal angle:</b> {c['deal_context']}"),
                       style=f"font-size:12px;color:{MUTED};line-height:1.5;margin:0 0 4px;"))
    if c.get("thesis"):
        parts.append(P(NotStr(f"<b>Thesis:</b> <i>{c['thesis']}</i>"),
                       style=f"font-size:12px;color:{MUTED};line-height:1.5;margin:0;"))

    return Div(*parts,
               style=f"background:{BG_CARD};border:1px solid {LINE};border-radius:12px;"
                     f"padding:16px;margin-bottom:12px;")


def _targets_content():
    from utils.digest import get_cached_digest
    cached = get_cached_digest()
    digest = cached.get("digest", {}) if cached else {}
    companies = digest.get("companies", [])
    featured = digest.get("featured", {})
    deep_dive = digest.get("deep_dive", "")
    cached_at = cached.get("cached_at", "") if cached else ""

    action_bar = Div(
        Div(
            Span(f"{len(companies)} companies", style=f"font-size:12px;color:{INK};font-weight:600;"),
            Span(f"· {cached_at}", cls="mono", style=f"font-size:11px;color:{MUTED};margin-left:8px;")
            if cached_at else "",
            style="display:flex;align-items:center;",
        ),
        Div(
            Button("Regenerate", onclick="generateTargets()", type="button",
                   id="targets-gen-btn",
                   style=f"background:{AMBER};color:#0B1220;font-weight:700;font-size:12px;"
                   "border:none;border-radius:8px;padding:8px 14px;cursor:pointer;"),
            Input(type="email", id="targets-email", placeholder="recipient@email.com",
                  value="julian@predictivelabs.co.uk",
                  style=f"background:{BG_CARD};border:1px solid {LINE};color:{INK};"
                  "border-radius:8px;padding:7px 12px;font-size:12px;margin-left:8px;width:200px;"),
            Button("Send Email", onclick="sendTargetsEmail()", type="button",
                   id="targets-send-btn",
                   style=f"background:transparent;color:{AMBER};font-weight:700;font-size:12px;"
                   f"border:1px solid {AMBER};border-radius:8px;padding:8px 14px;cursor:pointer;margin-left:4px;"),
            Button("PDF", onclick="downloadTargetsPDF()", type="button",
                   style=f"background:transparent;color:{MUTED};font-weight:600;font-size:12px;"
                   f"border:1px solid {LINE};border-radius:8px;padding:8px 14px;cursor:pointer;margin-left:4px;"),
            Span(id="targets-status", cls="mono",
                 style=f"font-size:11px;color:{MUTED};margin-left:10px;"),
            style="display:flex;align-items:center;flex-wrap:wrap;gap:2px;",
        ),
        style=f"display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;"
              f"gap:10px;margin-bottom:14px;padding:12px 16px;background:{BG_CARD};"
              f"border:1px solid {LINE};border-radius:12px;",
    )

    if not companies:
        body = Div(
            P("No daily scan available yet. Click Regenerate to build one (~60s).",
              style=f"color:{MUTED};font-size:13px;"),
            style=f"background:{BG_CARD};border:1px solid {LINE};border-radius:12px;padding:20px;",
        )
    else:
        featured_name = featured.get("name") if featured else None
        cards = [_target_card(c, is_featured=(c.get("name") == featured_name)) for c in companies]

        if featured and deep_dive:
            import re
            lines = deep_dive.strip().splitlines()
            dive_parts = []
            for raw in lines:
                line = raw.strip()
                if not line:
                    continue
                elif line.startswith("## "):
                    dive_parts.append(H3(line[3:], style=f"font-size:14px;font-weight:700;color:{INK};margin:12px 0 4px;"))
                elif line.startswith("# "):
                    dive_parts.append(H2(line[2:], style=f"font-size:16px;font-weight:700;color:{INK};margin:14px 0 4px;"))
                elif line.startswith("- ") or line.startswith("* "):
                    dive_parts.append(P(NotStr(f"• {line[2:]}"),
                                        style=f"font-size:12px;color:{INK};line-height:1.5;margin:2px 0 2px 12px;"))
                elif line.startswith("> "):
                    dive_parts.append(P(NotStr(f"<i>{line[2:]}</i>"),
                                        style=f"font-size:12px;color:{MUTED};line-height:1.5;margin:2px 0;"))
                else:
                    dive_parts.append(P(line, style=f"font-size:12px;color:{INK};line-height:1.5;margin:2px 0;"))

            f_flag = _FLAG.get(featured.get("country", ""), "")
            deep_dive_section = Div(
                Div(
                    Span(f"Deep Dive — {f_flag} {featured.get('name', '')}",
                         style=f"font-size:16px;font-weight:700;color:{AMBER};"),
                    Div(f"{featured.get('sector', '')} · {featured.get('country', '')}",
                        style=f"font-size:11px;color:{MUTED};margin-top:2px;"),
                    style=f"padding-bottom:10px;border-bottom:2px solid {AMBER};margin-bottom:10px;",
                ),
                *dive_parts,
                style=f"background:{BG_CARD};border:1px solid {LINE};border-radius:12px;"
                      f"padding:16px;margin-bottom:12px;",
            )
            cards.append(deep_dive_section)

        body = Div(*cards)

    return Div(action_bar, body)


# ── Main page ────────────────────────────────────────────────────────

_RADAR_JS = """
function setActiveTab(el, tabId) {
    document.querySelectorAll('.radar-tab').forEach(function(t) {
        t.style.background = 'transparent';
        t.style.color = '#94A3B8';
        t.style.border = '1px solid #1E293B';
        t.style.borderBottom = 'none';
        t.classList.remove('active');
    });
    el.style.background = '#F59E0B';
    el.style.color = '#0B1220';
    el.style.border = 'none';
    el.classList.add('active');
}
async function generateTargets() {
    var btn = document.getElementById('targets-gen-btn');
    var status = document.getElementById('targets-status');
    btn.disabled = true; btn.textContent = 'Generating…';
    status.textContent = 'Building digest (~60s)…';
    try {
        var resp = await fetch('/app/deals/generate', {method: 'POST'});
        var data = await resp.json();
        if (data.ok) {
            status.textContent = 'Done! Reloading…';
            htmx.ajax('GET', '/app/deal-radar/tab/targets', '#radar-tab-content');
        } else {
            status.textContent = data.error || 'Failed';
        }
    } catch(e) { status.textContent = 'Failed'; }
    btn.disabled = false; btn.textContent = 'Regenerate';
}
async function sendTargetsEmail() {
    var btn = document.getElementById('targets-send-btn');
    var status = document.getElementById('targets-status');
    var email = (document.getElementById('targets-email') || {}).value || '';
    if (!email) { status.textContent = 'Enter an email'; return; }
    btn.disabled = true; btn.textContent = 'Sending…';
    try {
        var resp = await fetch('/app/deals/send', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: email})
        });
        var data = await resp.json();
        status.textContent = data.ok ? ('Sent to ' + (data.to || email)) : (data.error || 'Failed');
    } catch(e) { status.textContent = 'Send failed'; }
    btn.disabled = false; btn.textContent = 'Send Email';
}
function downloadTargetsPDF() { window.location.href = '/app/deals/pdf'; }
"""


@ar("/app/deal-radar")
def deal_radar_page(session):
    tab = "synergies"
    content = Div(
        _tab_bar(tab),
        Div(_synergies_content(), id="radar-tab-content",
            style="padding:16px 20px;"),
        cls="max-w-4xl mx-auto w-full",
    )
    return _shell(
        session, title="Deal Radar · LiquidRound",
        header_title="Deal Radar", header_sub="Synergies & Daily Targets",
        content=content, current_path="/app/deal-radar",
        extra_js=_RADAR_JS)


@ar("/app/deal-radar/tab/synergies")
def tab_synergies(session):
    return _synergies_content()


@ar("/app/deal-radar/tab/targets")
def tab_targets(session):
    return _targets_content()


# ── PDF export ──────────────────────────────────────────────────────────────

@ar("/app/deal-radar/pdf")
def deal_radar_pdf(session):
    from utils.deal_radar import get_latest_pairs
    from utils.page_pdf import build_pdf, pdf_filename, Section, Row

    pairs = get_latest_pairs(limit=25)
    groups: dict[str, list[dict]] = {}
    for p in pairs:
        groups.setdefault(p.get("target_country") or "Other", []).append(p)
    ordered = sorted(groups.items(),
                     key=lambda kv: -max(float(x["composite_score"]) for x in kv[1]))

    sections = []
    for country, cps in ordered:
        rows = [
            Row([
                p["buyer_name"],
                p["buyer_ticker"],
                p["target_name"],
                p.get("target_sector") or "",
                f"{float(p['composite_score']):.2f}",
                p.get("recommendation") or "",
            ])
            for p in cps
        ]
        sections.append(Section(
            f"{_FLAG.get(country, '')} {country}",
            headers=["Buyer", "Ticker", "Target", "Sector", "Score", "Recommendation"],
            rows=rows,
        ))

    path = build_pdf("Deal Radar", "Synergy pairs export", sections)
    fname = pdf_filename("Deal-Radar")
    return FileResponse(str(path), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})


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


@ar("/app/data-coverage/pdf")
async def data_coverage_pdf():
    """Export data coverage overview as PDF."""
    from utils.page_pdf import build_pdf, pdf_filename, Section, Row
    from starlette.responses import FileResponse

    src_rows = [Row([name, status, comp, fin, verdict]) for name, status, comp, fin, verdict in DATA_SOURCES]
    sections = [Section("Data Sources", headers=["Country", "Status", "Company Data", "Financials", "Verdict"], rows=src_rows)]

    pool = _pool_stats()
    if pool:
        pool_rows = [Row([
            r["country"],
            f'{r["total"]:,}',
            f'{r["covered"]:,}' if r["covered"] else "—",
            f'{r["with_sector"]:,}' if r["with_sector"] else "—",
            f'€{float(r["median_rev"])/1e6:.2f}M' if r.get("median_rev") else "—",
        ]) for r in pool]
        sections.append(Section("Pool by Country", headers=["Country", "Total", "Covered ≥€100k", "With Sector", "Median Rev"], rows=pool_rows))

    path = build_pdf("Data Coverage", "Company + financials sources", sections)
    fname = pdf_filename("Data-Coverage")
    return FileResponse(str(path), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@ar("/app/methodology/pdf")
async def methodology_pdf():
    """Export synergy scoring methodology as PDF."""
    from utils.page_pdf import build_pdf, pdf_filename, Section
    from starlette.responses import FileResponse

    md_path = Path(__file__).resolve().parent.parent / "docs" / "synergy_methodology.md"
    md = md_path.read_text() if md_path.exists() else "Methodology content not available."

    sections = [Section("M&A Synergy Scoring Methodology", text=md)]
    path = build_pdf("Methodology", "Synergy scoring methodology", sections)
    fname = pdf_filename("Methodology")
    return FileResponse(str(path), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})
