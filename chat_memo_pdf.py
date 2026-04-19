"""Memo → PDF preview pipeline + PDF.js viewer routes.

Ported from pehero/chat/memo_pdf.py with LiquidRound's navy+amber palette.

Flow:
  1. After an IC Memo / Teaser / Bid assistant response, the client POSTs the
     rendered markdown to /app/memo-pdf/render. We save it as a reportlab
     PDF in a session-scoped cache and return a file_id.
  2. The right-pane iframe loads Mozilla's hosted PDF.js viewer pointed at
     /app/memo-pdf/file/<file_id> with #search=&phrase=true to highlight.
  3. Subsequent "show me the deal size" / "where is the EBITDA bridge"
     chat turns re-navigate the iframe via /app/memo-pdf/highlight — no
     LLM round-trip.

One directory per browser session; hashed (sha1) content addresses mean
identical memos share a cached PDF.
"""
from __future__ import annotations

import hashlib
import logging
import re
import uuid
from pathlib import Path
from urllib.parse import quote

from fasthtml.core import APIRouter
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
)
from starlette.responses import (
    FileResponse, JSONResponse, RedirectResponse,
)

log = logging.getLogger(__name__)

ar = APIRouter()

CACHE_DIR = Path("/tmp/liquidround-memo-pdf")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# LiquidRound brand palette (navy + amber) — PDFs render on white paper so
# use dark-on-light for body but the accent stays amber.
INK       = HexColor("#0F172A")   # slate-900 (body ink on white)
INK_MUTED = HexColor("#475569")   # slate-600
ACCENT    = HexColor("#F59E0B")   # amber-500
RULE      = HexColor("#CBD5E1")   # slate-300


def _session_dir(session) -> Path:
    """One directory per browser session so PDFs don't leak across users."""
    sess_id = session.get("memo_pdf_session")
    if not sess_id:
        sess_id = uuid.uuid4().hex
        session["memo_pdf_session"] = sess_id
    d = CACHE_DIR / sess_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── markdown → PDF ───────────────────────────────────────────────────

def _styles():
    ss = getSampleStyleSheet()
    return {
        "h1":      ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                                  fontSize=20, leading=24, textColor=ACCENT,
                                  spaceAfter=8, spaceBefore=4),
        "h2":      ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                                  fontSize=14, leading=18, textColor=INK,
                                  spaceAfter=6, spaceBefore=10),
        "h3":      ParagraphStyle("h3", parent=ss["Heading3"], fontName="Helvetica-Bold",
                                  fontSize=12, leading=16, textColor=INK,
                                  spaceAfter=4, spaceBefore=8),
        "body":    ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica",
                                  fontSize=10.5, leading=15, textColor=INK,
                                  alignment=TA_LEFT, spaceAfter=4),
        "bullet":  ParagraphStyle("bullet", parent=ss["BodyText"], fontName="Helvetica",
                                  fontSize=10.5, leading=15, textColor=INK,
                                  leftIndent=14, bulletIndent=0, spaceAfter=2),
        "caption": ParagraphStyle("caption", parent=ss["Italic"], fontName="Helvetica-Oblique",
                                  fontSize=8.5, leading=11, textColor=INK_MUTED),
    }


# Minimal inline markdown → reportlab mini-HTML (Platypus accepts <b>, <i>, <font>).
_INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
    (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"), r"<i>\1</i>"),
    (re.compile(r"`([^`]+)`"), r"<font face='Courier'>\1</font>"),
]


def _inline(text: str) -> str:
    out = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for rx, repl in _INLINE:
        out = rx.sub(repl, out)
    return out


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(INK_MUTED)
    canvas.drawString(2 * cm, 1.2 * cm, "LiquidRound · memo (generated)")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.restoreState()


def markdown_to_pdf(markdown_text: str, out_path: Path, *, title: str = "IC memo") -> None:
    """Render a markdown string into a reportlab PDF at `out_path`."""
    styles = _styles()
    doc = BaseDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        title=title, author="LiquidRound",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=_footer)])

    story = []
    in_list: list[str] = []

    def flush_list():
        for item in in_list:
            story.append(Paragraph("• " + _inline(item), styles["bullet"]))
        in_list.clear()

    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_list()
            story.append(Spacer(1, 4))
            continue
        if line.startswith("# "):
            flush_list()
            story.append(Paragraph(_inline(line[2:].strip()), styles["h1"]))
        elif line.startswith("## "):
            flush_list()
            story.append(Paragraph(_inline(line[3:].strip()), styles["h2"]))
        elif line.startswith("### "):
            flush_list()
            story.append(Paragraph(_inline(line[4:].strip()), styles["h3"]))
        elif line.startswith("- ") or line.startswith("* "):
            in_list.append(line[2:].strip())
        else:
            flush_list()
            story.append(Paragraph(_inline(line), styles["body"]))

    flush_list()
    if not story:
        story.append(Paragraph("(empty memo)", styles["caption"]))
    doc.build(story)


# ── Routes ───────────────────────────────────────────────────────────

@ar("/app/memo-pdf/render", methods=["POST"])
async def memo_render(session, request):
    """Accept memo markdown, render a PDF, return a file_id + URLs."""
    form = await request.form()
    md = (form.get("markdown") or "").strip()
    title = (form.get("title") or "IC memo").strip()[:120]
    if not md:
        return JSONResponse({"error": "empty markdown"}, status_code=400)

    # Content-addressed id: identical memos share a cached PDF.
    fid = hashlib.sha1(md.encode("utf-8")).hexdigest()[:16]
    out = _session_dir(session) / f"{fid}.pdf"
    if not out.exists():
        try:
            markdown_to_pdf(md, out, title=title)
        except Exception as e:  # noqa: BLE001
            log.exception("memo pdf render failed")
            return JSONResponse({"error": str(e)}, status_code=500)

    session["memo_pdf_last_id"] = fid
    return JSONResponse({
        "ok": True,
        "file_id": fid,
        "view_url": f"/app/memo-pdf/view/{fid}",
        "file_url": f"/app/memo-pdf/file/{fid}",
        "title": title,
    })


@ar("/app/memo-pdf/file/{file_id}")
async def memo_file(session, file_id: str):
    """Serve the raw PDF (consumed by PDF.js viewer in the iframe)."""
    if not re.fullmatch(r"[a-f0-9]{8,64}", file_id):
        return JSONResponse({"error": "bad id"}, status_code=400)
    p = _session_dir(session) / f"{file_id}.pdf"
    if not p.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(str(p), media_type="application/pdf")


@ar("/app/memo-pdf/view/{file_id}")
async def memo_view(session, request, file_id: str, search: str = ""):
    """Redirect to Mozilla's hosted PDF.js viewer pointed at our /file/<id>."""
    if not re.fullmatch(r"[a-f0-9]{8,64}", file_id):
        return JSONResponse({"error": "bad id"}, status_code=400)

    base = str(request.base_url).rstrip("/")
    file_url = f"{base}/app/memo-pdf/file/{file_id}"
    viewer = ("https://mozilla.github.io/pdf.js/web/viewer.html"
              f"?file={quote(file_url, safe='')}")
    if search:
        viewer += f"#search={quote(search[:120])}&phrase=true"
    return RedirectResponse(url=viewer, status_code=302)


@ar("/app/memo-pdf/highlight", methods=["POST"])
async def memo_highlight(session, request):
    """Return a PDF.js viewer URL for the last-rendered memo + a search term.

    Client calls this when the user asks "show me the deal size"; the client
    then updates the iframe src — no LLM round-trip.
    """
    form = await request.form()
    search = (form.get("search") or "").strip()
    file_id = (form.get("file_id") or session.get("memo_pdf_last_id") or "").strip()
    if not file_id:
        return JSONResponse({"error": "no pdf rendered yet"}, status_code=400)
    if not re.fullmatch(r"[a-f0-9]{8,64}", file_id):
        return JSONResponse({"error": "bad id"}, status_code=400)

    base = str(request.base_url).rstrip("/")
    file_url = f"{base}/app/memo-pdf/file/{file_id}"
    url = ("https://mozilla.github.io/pdf.js/web/viewer.html"
           f"?file={quote(file_url, safe='')}")
    if search:
        url += f"#search={quote(search[:120])}&phrase=true"
    return JSONResponse({"ok": True, "file_id": file_id, "viewer_url": url, "search": search})
