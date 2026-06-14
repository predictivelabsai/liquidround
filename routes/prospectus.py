"""Prospectus Builder — upload/pick a company doc, extract standardized prospectus
sections with the LLM, edit them, and generate a PDF (ported from `ipogate`).

/app/prospectus               → page: source picker + IPO 101
POST /app/prospectus/extract  → run LLM extraction, return editable form
POST /app/prospectus/generate → assemble markdown -> PDF, return inline viewer
"""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile

from fasthtml.common import (
    APIRouter, Div, Span, H2, H3, P, A, Button, Form, Input, Textarea, Select,
    Option, Label, Title, Script, Details, Summary, Iframe, NotStr,
)
from starlette.requests import Request

from utils.prospectus import (
    SECTIONS, FIELDS, LONG_FIELDS, SECTION_HELP, extract_prospectus, prospectus_to_markdown,
)

log = logging.getLogger(__name__)
ar = APIRouter()

_PARSE_EXT = (".pdf", ".xlsx", ".xls", ".pptx", ".ppt")


def _get_user(session):
    user = session.get("user")
    return (user.get("user_id"), user.get("email")) if user else (None, None)


def _user_docs(uid: str) -> list[dict]:
    if not uid:
        return []
    try:
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, filename, content_type FROM liquidround.data_room "
                "WHERE user_id = %s ORDER BY uploaded_at DESC",
                (uid,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        log.exception("Failed to load data room docs")
        return []


# ── IPO 101 + form fragments ────────────────────────────────────────────────

def _ipo_101() -> Details:
    items = [Div(Span(SECTIONS[k], cls="ipo-pl-name"), P(v, cls="ipo-pl-summary"), cls="prospectus-help-item")
             for k, v in SECTION_HELP.items()]
    return Details(
        Summary("📚 IPO 101 — what each prospectus section means", cls="ipo-section-title"),
        Div(*items, cls="prospectus-help"),
        cls="ipo-card",
    )


def _field_input(section: str, field: str, value: str):
    name = f"{section}.{field}"
    label = field.replace("_", " ").title()
    ctl = (Textarea(value or "", name=name, rows="3", cls="ipo-filter-select")
           if field in LONG_FIELDS else
           Input(type="text", name=name, value=value or "", cls="ipo-filter-select"))
    return Div(Label(label, cls="ipo-filter-label"), ctl, cls="prospectus-field")


def _extracted_form(data: dict) -> Form:
    section_blocks = []
    for key, title in SECTIONS.items():
        sect = data.get(key) or {}
        fields = [_field_input(key, f, str(sect.get(f, "") or "")) for f in FIELDS[key]]
        section_blocks.append(Details(
            Summary(title, cls="ipo-section-title"),
            Div(*fields, cls="prospectus-grid"),
            cls="ipo-card", open=(key in ("basic_information", "share_offering_details")),
        ))
    return Form(
        *section_blocks,
        Div(
            Button("📄 Generate prospectus PDF", type="submit", cls="ipo-refresh-btn"),
            Span("", id="prospectus-gen-ind", cls="ipo-indicator htmx-indicator"),
            cls="prospectus-actions",
        ),
        Div(id="prospectus-output"),
        hx_post="/app/prospectus/generate",
        hx_target="#prospectus-output",
        hx_swap="innerHTML",
        **{"hx-indicator": "#prospectus-gen-ind"},
    )


# ── routes ───────────────────────────────────────────────────────────────────

@ar("/app/prospectus")
def prospectus_page(session):
    from components.chat_shell import left_pane, right_pane

    uid, email = _get_user(session)
    docs = [d for d in _user_docs(uid) if d["filename"].lower().endswith(_PARSE_EXT)]

    sessions_list = []
    if uid:
        try:
            from utils.database import db_service
            convs = db_service.get_user_conversations(uid, limit=20) or []
            sessions_list = [{"id": c["id"], "title": c.get("conversation_title") or c.get("user_query", "Untitled")}
                             for c in convs]
        except Exception:
            pass

    if not uid:
        picker = Div(P("Sign in and upload a document in the Data Room to build a prospectus.",
                       cls="ipo-empty-sub"), cls="ipo-empty")
    elif not docs:
        picker = Div(
            P("No PDF / XLSX / PPTX documents found.", cls="ipo-empty-title"),
            P(A("Upload one in the Data Room →", href="/app/dataroom", cls="ipo-pl-link"),
              cls="ipo-empty-sub"),
            cls="ipo-empty",
        )
    else:
        picker = Form(
            Div(
                Label("Source document", cls="ipo-filter-label"),
                Select(*[Option(d["filename"][:60], value=str(d["id"])) for d in docs],
                       name="doc_id", cls="ipo-filter-select"),
                cls="prospectus-field",
            ),
            Button("✨ Extract sections", type="submit", cls="ipo-refresh-btn"),
            Span("", id="prospectus-ext-ind", cls="ipo-indicator htmx-indicator"),
            hx_post="/app/prospectus/extract",
            hx_target="#prospectus-form",
            hx_swap="innerHTML",
            **{"hx-indicator": "#prospectus-ext-ind"},
            cls="prospectus-picker",
        )

    header = Div(
        Div(
            Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
            Span("Prospectus Builder", cls="chat-header-title"),
            Span("·", cls="chat-header-dot"),
            Span("Doc → IPO prospectus", cls="chat-header-agent"),
            cls="chat-header-left",
        ),
        cls="chat-header",
    )

    return (
        Title("Prospectus Builder · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(user_email=email, sessions=sessions_list, current_sid="",
                      current_path="/app/prospectus",
                      current_currency=session.get("currency", "EUR"),
                      current_role=session.get("role", "buyer")),
            Div(
                header,
                Div(
                    Div(
                        H2("Build an IPO prospectus from a document", cls="text-ink"),
                        P("Pick a company document — the AI extracts the standard prospectus "
                          "sections, you edit them, then export a formatted PDF.",
                          cls="text-ink-muted"),
                        cls="ipo-hero",
                    ),
                    picker,
                    _ipo_101(),
                    Div(id="prospectus-form"),
                    cls="ipo-wrap",
                ),
                cls="center-pane",
            ),
            right_pane(),
            cls="app pane-closed",
        ),
        Script(src="/chat.js"),
    )


@ar("/app/prospectus/extract", methods=["POST"])
async def prospectus_extract(session, request: Request):
    uid, _ = _get_user(session)
    if not uid:
        return Div(P("Please sign in.", cls="ipo-empty-sub"))
    form = await request.form()
    doc_id = form.get("doc_id")
    if not doc_id:
        return Div(P("No document selected.", cls="ipo-empty-sub"))

    # load bytes from the data room
    try:
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT filename, data FROM liquidround.data_room WHERE id = %s AND user_id = %s",
                        (doc_id, uid))
            row = cur.fetchone()
        if not row:
            return Div(P("Document not found.", cls="ipo-empty-sub"))
        filename, data = row[0], bytes(row[1])
    except Exception:
        log.exception("Failed to load document")
        return Div(P("Could not load the document.", cls="ipo-empty-sub"))

    # parse -> text -> extract
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    try:
        from utils.document_parser import DocumentParser
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            parser = DocumentParser()
            parsed = parser.parse(tmp_path)
            text = parser.extract_all_text(parsed)
        finally:
            os.unlink(tmp_path)
    except Exception:
        log.exception("Document parse failed")
        return Div(P("Could not parse this document type.", cls="ipo-empty-sub"))

    extracted = extract_prospectus(text)
    return Div(
        H3("Review & edit prospectus sections", cls="ipo-section-title"),
        _extracted_form(extracted),
    )


@ar("/app/prospectus/generate", methods=["POST"])
async def prospectus_generate(session, request: Request):
    form = await request.form()
    data: dict = {k: {} for k in SECTIONS}
    for full_key, value in form.items():
        if "." in full_key:
            section, field = full_key.split(".", 1)
            if section in data:
                data[section][field] = value

    md = prospectus_to_markdown(data)
    company = (data.get("basic_information", {}) or {}).get("company_name", "") or "Company"

    try:
        from chat_memo_pdf import markdown_to_pdf, _session_dir
        fid = hashlib.sha1(md.encode("utf-8")).hexdigest()[:16]
        out = _session_dir(session) / f"{fid}.pdf"
        if not out.exists():
            markdown_to_pdf(md, out, title=f"{company} — Prospectus")
    except Exception:
        log.exception("Prospectus PDF render failed")
        return Div(P("Could not generate the PDF.", cls="ipo-empty-sub"))

    return Div(
        Div(
            Span("Prospectus generated.", cls="ipo-signup-ok"),
            A("⬇ Download PDF", href=f"/app/memo-pdf/file/{fid}", target="_blank", cls="ipo-pl-link"),
            cls="prospectus-output-bar",
        ),
        Iframe(src=f"/app/memo-pdf/file/{fid}", cls="prospectus-pdf"),
        cls="ipo-card",
    )
