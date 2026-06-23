"""Daily Deal Digest routes — workspace page, send, PDF tearsheet.

/app/deals           → workspace page: cached digest with Send + PDF + Generate
/app/deals/generate  → build digest on demand (POST)
/app/deals/send      → send digest to a specific email address (POST)
/app/deals/pdf       → download digest as a PDF tearsheet (GET)
/app/digest          → standalone preview (legacy)
/app/digest/send     → send the digest via Postmark email (POST)
/app/digest/send-all → send to all opted-in users (POST)
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import date
from pathlib import Path

from fasthtml.common import (
    Html, Head, Body, Meta, Title, Link, Script, NotStr,
    Div, Span, H1, H2, P, A, Button, Form, Input, Label,
)
from fasthtml.core import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, FileResponse, Response

ar = APIRouter()
log = logging.getLogger(__name__)

CACHE_DIR = Path("/tmp/liquidround-digest-pdf")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ── helpers ──────────────────────────────────────────────────────────

def _session_info(session):
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
    return email, sessions_list


def _deals_shell(session, center_children):
    """Wrap center content in the standard 3-pane layout."""
    from components.chat_shell import left_pane, right_pane
    email, sessions_list = _session_info(session)
    return (
        Title("Daily Deals · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(
                user_email=email,
                sessions=sessions_list,
                current_sid="",
                current_path="/app/deals",
                current_currency=session.get("currency", "EUR"),
                current_role=session.get("role", "buyer"),
            ),
            Div(*center_children, cls="center-pane pipeline-center"),
            right_pane(),
            cls="app pane-closed",
        ),
        Script(src="/chat.js?v=2"),
        Script(NotStr(_DEALS_JS)),
    )


# ── Workspace page — /app/deals ─────────────────────────────────────

@ar("/app/deals")
async def deals_page(session):
    """Daily Deals workspace page — shows cached digest or empty state."""
    from utils.digest import get_cached_digest

    cached = get_cached_digest()

    header = Div(
        Div(
            Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span("Daily Deals", cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span("Baltic ECM & M&A", cls="chat-header-agent"),
            cls="chat-header-left",
        ),
        cls="chat-header",
    )

    if cached and cached.get("html"):
        digest = cached.get("digest", {})
        html = cached["html"]
        n = len(digest.get("companies", []))
        featured = digest.get("featured", {})
        featured_name = featured.get("name", "N/A") if featured else "N/A"
        cached_date = cached.get("cached_at", "unknown")

        action_bar = Div(
            Div(
                Span(f"{n} companies", cls="deals-stat"),
                Span("·", cls="deals-dot"),
                Span(f"Deep dive: {featured_name}", cls="deals-stat"),
                Span("·", cls="deals-dot"),
                Span(f"Generated: {cached_date}", cls="deals-stat"),
                cls="deals-stats",
            ),
            Div(
                Button("Regenerate", onclick="generateDeals()", cls="deals-btn deals-btn-gen",
                       type="button", id="deals-gen-btn"),
                Input(type="email", id="deals-email", placeholder="recipient@email.com",
                      value="julian@predictivelabs.co.uk",
                      cls="deals-email-input"),
                Button("Send Email", onclick="sendDealsEmail()", cls="deals-btn deals-btn-send",
                       type="button", id="deals-send-btn"),
                Button("Download PDF", onclick="downloadDealsPDF()", cls="deals-btn deals-btn-pdf",
                       type="button"),
                Span(id="deals-status", cls="deals-status"),
                cls="deals-actions",
            ),
            cls="deals-action-bar",
        )

        body = Div(
            action_bar,
            Div(Div(NotStr(html), cls="deals-email-preview"), cls="deals-content"),
            cls="companies-wrap",
        )
    else:
        body = Div(
            Div(
                Div(
                    Span("◉", cls="deals-empty-icon"),
                    H2("No digest available", cls="deals-empty-title"),
                    P("The daily digest hasn't been generated yet. Click Generate to build one now — "
                      "this takes about 60 seconds as it researches Baltic M&A deals, generates investment "
                      "theses, and picks a featured company for a deep dive.",
                      cls="deals-empty-text"),
                    Button("Generate", onclick="generateDeals()", cls="deals-btn deals-btn-gen deals-gen-big",
                           type="button", id="deals-gen-btn"),
                    Span(id="deals-status", cls="deals-status"),
                    cls="deals-empty-inner",
                ),
                cls="deals-empty",
            ),
            cls="companies-wrap",
        )

    return _deals_shell(session, [header, body])


# ── Generate on demand ──────────────────────────────────────────────

@ar("/app/deals/generate", methods=["POST"])
async def deals_generate():
    """Build digest on demand, cache it, return JSON."""
    from utils.digest import build_digest, render_email_html, cache_digest, render_blog_html, archive_digest

    try:
        digest = build_digest()
        html = render_email_html(digest)
        cache_digest(digest, html)
        blog_html = render_blog_html(digest)
        archive_digest(digest, blog_html)
        n = len(digest.get("companies", []))
        return JSONResponse({"ok": True, "companies": n})
    except Exception as e:
        log.exception("Digest generation failed")
        return JSONResponse({"ok": False, "error": str(e)})


# ── Send to specific email ──────────────────────────────────────────

@ar("/app/deals/send", methods=["POST"])
async def deals_send(request: Request):
    """Send the cached digest to a specific email address."""
    from utils.digest import get_cached_digest, send_digest_email

    try:
        body = await request.json()
        email = body.get("email", "").strip()
    except Exception:
        email = ""

    if not email:
        return JSONResponse({"ok": False, "error": "No email provided"})

    cached = get_cached_digest()
    if not cached or not cached.get("html"):
        return JSONResponse({"ok": False, "error": "No digest available — generate one first"})

    result = send_digest_email(cached["html"], to_email=email)
    return JSONResponse(result)


# ── PDF tearsheet ────────────────────────────────────────────────────

@ar("/app/deals/pdf")
async def deals_pdf():
    """Return the cached digest as a downloadable PDF tearsheet."""
    from utils.digest import get_cached_digest
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
        HRFlowable,
    )

    cached = get_cached_digest()
    if not cached or not cached.get("digest"):
        return JSONResponse({"error": "No digest available — generate one first"}, status_code=404)

    digest = cached["digest"]
    companies = digest.get("companies", [])
    featured = digest.get("featured", {})
    deep_dive = digest.get("deep_dive", "")
    today = cached.get("cached_at", date.today().isoformat())
    today_display = today

    INK = HexColor("#0F172A")
    INK_MUTED = HexColor("#475569")
    ACCENT = HexColor("#F59E0B")
    NAVY = HexColor("#0B1220")
    RULE = HexColor("#CBD5E1")

    ss = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold",
                                fontSize=22, leading=26, textColor=INK, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", parent=ss["Normal"], fontName="Helvetica",
                                   fontSize=11, textColor=INK_MUTED, spaceAfter=12),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                             fontSize=14, leading=18, textColor=INK, spaceAfter=6, spaceBefore=14),
        "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontName="Helvetica-Bold",
                             fontSize=12, leading=16, textColor=INK, spaceAfter=4, spaceBefore=10),
        "body": ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica",
                               fontSize=9.5, leading=13, textColor=INK, spaceAfter=3),
        "thesis": ParagraphStyle("thesis", parent=ss["BodyText"], fontName="Helvetica-Oblique",
                                 fontSize=9, leading=12.5, textColor=INK_MUTED, spaceAfter=2,
                                 leftIndent=6),
        "deal": ParagraphStyle("deal", parent=ss["BodyText"], fontName="Helvetica",
                               fontSize=8.5, leading=11, textColor=HexColor("#1E40AF"),
                               spaceAfter=2),
        "bullet": ParagraphStyle("bullet", parent=ss["BodyText"], fontName="Helvetica",
                                 fontSize=9.5, leading=13, textColor=INK,
                                 leftIndent=14, bulletIndent=0, spaceAfter=2),
        "caption": ParagraphStyle("caption", parent=ss["Italic"], fontName="Helvetica-Oblique",
                                  fontSize=8, leading=10, textColor=INK_MUTED),
        "featured_name": ParagraphStyle("featured_name", parent=ss["Heading2"],
                                        fontName="Helvetica-Bold", fontSize=13, textColor=ACCENT,
                                        spaceAfter=2, spaceBefore=4),
    }

    fid = hashlib.sha1(f"digest-{today}".encode()).hexdigest()[:16]
    out = CACHE_DIR / f"{fid}.pdf"

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(INK_MUTED)
        canvas.drawString(2 * cm, 1.0 * cm, f"LiquidRound · Daily Deals · {today_display}")
        canvas.drawRightString(A4[0] - 2 * cm, 1.0 * cm, f"Page {doc.page}")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(2 * cm, 1.3 * cm, A4[0] - 2 * cm, 1.3 * cm)
        canvas.restoreState()

    def _header(canvas, doc):
        _footer(canvas, doc)
        if doc.page == 1:
            canvas.saveState()
            canvas.setFillColor(NAVY)
            canvas.rect(0, A4[1] - 1.6 * cm, A4[0], 1.6 * cm, fill=True, stroke=False)
            canvas.setFont("Helvetica-Bold", 16)
            canvas.setFillColor(ACCENT)
            canvas.drawString(2 * cm, A4[1] - 1.15 * cm, "LiquidRound")
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(HexColor("#94A3B8"))
            canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.15 * cm,
                                   f"Baltic ECM & M&A Daily Digest — {today_display}")
            canvas.restoreState()

    doc = BaseDocTemplate(
        str(out), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2.2 * cm, bottomMargin=1.8 * cm,
        title=f"LiquidRound Daily Deals — {today_display}",
        author="LiquidRound · Predictive Labs Ltd",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=_header)])

    story = []
    story.append(Spacer(1, 6))

    _INLINE_RE = [
        (re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
        (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"), r"<i>\1</i>"),
        (re.compile(r"`([^`]+)`"), r"<font face='Courier'>\1</font>"),
    ]

    def _inline(text):
        out = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for rx, repl in _INLINE_RE:
            out = rx.sub(repl, out)
        return out

    FLAGS = {"Estonia": "EE", "Lithuania": "LT", "Latvia": "LV"}

    if companies:
        story.append(Paragraph(f"Daily Company Scan — {len(companies)} Companies", styles["h2"]))
        story.append(Spacer(1, 4))

        for i, c in enumerate(companies):
            is_featured = (c.get("name") == featured.get("name"))
            flag = FLAGS.get(c.get("country", ""), "")
            label = f"<b>{flag} {_inline(c.get('name', 'N/A'))}</b>"
            if is_featured:
                label += '  <font color="#F59E0B"><b>[DEEP DIVE]</b></font>'

            story.append(Paragraph(label, styles["body"]))

            meta = f"{c.get('sector', '')} · {c.get('country', '')}"
            ds = c.get("deal_size_estimate", "")
            if ds and ds != "undisclosed":
                meta += f" · {ds}"
            story.append(Paragraph(meta, styles["caption"]))

            if c.get("description"):
                story.append(Paragraph(_inline(c["description"]), styles["body"]))

            if c.get("deal_context"):
                story.append(Paragraph(f"Deal angle: {_inline(c['deal_context'])}", styles["deal"]))

            if c.get("thesis"):
                story.append(Paragraph(f"Thesis: {_inline(c['thesis'])}", styles["thesis"]))

            story.append(Spacer(1, 6))
            if i < len(companies) - 1:
                story.append(HRFlowable(width="100%", thickness=0.3, color=RULE,
                                        spaceAfter=6, spaceBefore=0))

    if featured and deep_dive:
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT,
                                spaceAfter=8, spaceBefore=4))
        f_flag = FLAGS.get(featured.get("country", ""), "")
        story.append(Paragraph(
            f"Deep Dive — {f_flag} {_inline(featured.get('name', 'N/A'))}",
            styles["featured_name"],
        ))
        meta = f"{featured.get('sector', '')} · {featured.get('country', '')} · {featured.get('deal_context', '')}"
        story.append(Paragraph(meta, styles["caption"]))
        story.append(Spacer(1, 4))

        for raw in deep_dive.splitlines():
            line = raw.strip()
            if not line:
                story.append(Spacer(1, 3))
            elif line.startswith("## "):
                story.append(Paragraph(_inline(line[3:]), styles["h3"]))
            elif line.startswith("# "):
                story.append(Paragraph(_inline(line[2:]), styles["h2"]))
            elif line.startswith("- ") or line.startswith("* "):
                story.append(Paragraph("• " + _inline(line[2:]), styles["bullet"]))
            elif line.startswith("> "):
                story.append(Paragraph(f"<i>{_inline(line[2:])}</i>", styles["body"]))
            else:
                story.append(Paragraph(_inline(line), styles["body"]))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.3, color=RULE, spaceAfter=6))
    story.append(Paragraph(
        "Generated by LiquidRound AI · Predictive Labs Ltd. "
        "AI-generated analysis for informational purposes only. Not investment advice.",
        styles["caption"],
    ))

    try:
        doc.build(story)
    except Exception as e:
        log.exception("Digest PDF build failed")
        return JSONResponse({"error": str(e)}, status_code=500)

    fname = f"LiquidRound-Daily-Deals-{today}.pdf"
    return FileResponse(
        str(out), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ── Client-side JS ──────────────────────────────────────────────────

_DEALS_JS = """
async function generateDeals() {
    var btn = document.getElementById('deals-gen-btn');
    var status = document.getElementById('deals-status');
    btn.disabled = true;
    btn.textContent = 'Generating…';
    status.textContent = 'Building digest (researching deals, generating theses)… ~60s';
    status.className = 'deals-status';
    try {
        var resp = await fetch('/app/deals/generate', {method: 'POST'});
        var data = await resp.json();
        if (data.ok) {
            status.textContent = 'Done! Reloading…';
            status.className = 'deals-status success';
            setTimeout(function() { window.location.reload(); }, 500);
        } else {
            status.textContent = data.error || 'Generation failed';
            status.className = 'deals-status error';
            btn.disabled = false;
            btn.textContent = 'Generate';
        }
    } catch(err) {
        status.textContent = 'Generation failed';
        status.className = 'deals-status error';
        btn.disabled = false;
        btn.textContent = 'Generate';
    }
}

async function sendDealsEmail() {
    var btn = document.getElementById('deals-send-btn');
    var status = document.getElementById('deals-status');
    var emailInput = document.getElementById('deals-email');
    var email = emailInput ? emailInput.value.trim() : '';
    if (!email) { status.textContent = 'Enter an email address'; status.className = 'deals-status error'; return; }
    btn.disabled = true;
    btn.textContent = 'Sending…';
    status.textContent = '';
    status.className = 'deals-status';
    try {
        var resp = await fetch('/app/deals/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: email})
        });
        var data = await resp.json();
        if (data.ok) {
            status.textContent = 'Sent to ' + data.to;
            status.className = 'deals-status success';
        } else {
            status.textContent = data.error || 'Send failed';
            status.className = 'deals-status error';
        }
    } catch(err) {
        status.textContent = 'Send failed';
        status.className = 'deals-status error';
    }
    btn.disabled = false;
    btn.textContent = 'Send Email';
}

function downloadDealsPDF() {
    window.location.href = '/app/deals/pdf';
}
"""


# ── Legacy standalone preview ────────────────────────────────────────

@ar("/app/digest", methods=["GET"])
async def digest_preview():
    """Generate and preview the daily digest (takes ~30-60s for LLM calls)."""
    from utils.digest import build_digest, render_email_html

    digest = build_digest()
    html = render_email_html(digest)

    n = len(digest.get("companies", []))
    featured = digest.get("featured", {})
    featured_name = featured.get("name", "N/A") if featured else "N/A"

    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title("Daily Digest Preview · LiquidRound"),
            Link(rel="icon", type="image/svg+xml", href="/favicon.svg"),
            Link(rel="preconnect", href="https://fonts.googleapis.com"),
            Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
            Link(rel="stylesheet",
                 href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"),
            Script(src="https://cdn.tailwindcss.com"),
            Link(rel="stylesheet", href="/app.css"),
        ),
        Body(
            Div(
                Div(
                    Span("Daily Digest Preview", cls="text-lg font-bold text-gray-200"),
                    Span("·", cls="text-gray-500 mx-2"),
                    Span(f"{n} companies · Deep Dive: {featured_name}",
                         cls="text-sm text-gray-400"),
                    cls="flex items-center gap-1",
                ),
                Div(
                    Button("Send Email",
                           onclick="sendDigest()",
                           cls="text-xs bg-amber-600 hover:bg-amber-500 text-white px-4 py-2 rounded transition-colors"),
                    A("Back to chat", href="/app",
                      cls="text-xs text-gray-400 hover:text-amber-400 border border-gray-600 px-3 py-1.5 rounded transition-colors"),
                    Span(id="send-status", cls="text-xs text-gray-400 ml-2"),
                    cls="flex items-center gap-2",
                ),
                cls="flex items-center justify-between px-5 py-3 border-b border-gray-700",
            ),
            Div(
                NotStr(html),
                cls="overflow-y-auto",
                style="max-height: calc(100vh - 56px);",
            ),
            Script(NotStr("""
async function sendDigest() {
    var status = document.getElementById('send-status');
    status.textContent = 'Sending…';
    status.style.color = '#94a3b8';
    try {
        var resp = await fetch('/app/digest/send', {method: 'POST'});
        var data = await resp.json();
        if (data.ok) {
            status.textContent = 'Sent! (' + (data.message_id || '') + ')';
            status.style.color = '#F59E0B';
        } else {
            status.textContent = 'Error: ' + (data.error || 'unknown');
            status.style.color = '#EF4444';
        }
    } catch(err) {
        status.textContent = 'Send failed';
        status.style.color = '#EF4444';
    }
}
""")),
            style="background: var(--bg); color: var(--ink); font-family: 'Inter', sans-serif; height: 100vh; overflow: hidden;",
        ),
        lang="en",
    )


@ar("/app/digest/send", methods=["POST"])
async def digest_send(request):
    """Regenerate + send the digest via email to a specific address."""
    from utils.digest import build_digest, render_email_html, send_digest_email

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    to_email = body.get("email")
    if not to_email:
        return JSONResponse({"ok": False, "error": "email required"}, status_code=400)

    digest = build_digest()
    html = render_email_html(digest)
    result = send_digest_email(html, to_email=to_email)
    return JSONResponse(result)


@ar("/app/digest/send-all", methods=["POST"])
async def digest_send_all():
    """Build digest once, send to all opted-in users."""
    from utils.digest import send_digest_to_all

    result = send_digest_to_all()
    return JSONResponse(result)
