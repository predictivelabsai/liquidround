"""Data Room — upload, list, and download deal documents.

Virtual folder tree grouped by company_slug. Untagged files go under "General".

/app/dataroom                  → folder tree + upload form
POST /app/dataroom/upload      → handle file upload
GET  /app/dataroom/{id}/download → download a file
POST /app/dataroom/{id}/delete  → delete a file
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict

from fasthtml.common import (
    APIRouter, Html, Head, Body, Meta, Title, Link, Script, NotStr,
    Div, Span, H2, P, A, Button, Form, Input, Select, Option, Label,
    Details, Summary,
)
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse

ar = APIRouter()
log = logging.getLogger(__name__)

DB_SCHEMA = os.getenv("COMPANY_DB_SCHEMA", "pehero")


def _fmt_size(size_bytes) -> str:
    if not size_bytes:
        return "—"
    if size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    if size_bytes >= 1_000:
        return f"{size_bytes / 1_000:.0f} KB"
    return f"{size_bytes} B"


_ICON_MAP = {
    "pdf": "📄", "word": "📝", "docx": "📝", "doc": "📝",
    "sheet": "📊", "excel": "📊", "xlsx": "📊", "csv": "📊",
    "presentation": "📋", "pptx": "📋",
    "image": "🖼", "png": "🖼", "jpg": "🖼", "jpeg": "🖼",
}


def _file_icon(content_type: str, filename: str = "") -> str:
    ct = (content_type or "").lower()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    for key, icon in _ICON_MAP.items():
        if key in ct or key == ext:
            return icon
    return "📎"


def _folder_node(folder_name: str, docs: list[dict], folder_id: str,
                 is_open: bool = False) -> Div:
    total_size = sum(d.get("size_bytes") or 0 for d in docs)
    file_rows = []
    for d in docs:
        file_rows.append(
            Div(
                Span(_file_icon(d["content_type"], d["filename"]), cls="dr-file-icon"),
                A(d["filename"], href=f"/app/dataroom/{d['id']}/download", cls="dr-file-name"),
                Span(_fmt_size(d["size_bytes"]), cls="dr-file-size"),
                Span(str(d["uploaded_at"])[:16] if d["uploaded_at"] else "", cls="dr-file-date"),
                Form(
                    Button("✕", type="submit", cls="dr-delete-btn", title="Delete"),
                    method="post", action=f"/app/dataroom/{d['id']}/delete",
                ),
                cls="dr-file-row",
            )
        )

    return Details(
        Summary(
            Span("▸", cls="dr-folder-arrow"),
            Span("📁", cls="dr-folder-icon"),
            Span(folder_name, cls="dr-folder-name"),
            Span(f"{len(docs)}", cls="dr-folder-count"),
            Span(_fmt_size(total_size), cls="dr-folder-size"),
            cls="dr-folder-toggle",
        ),
        Div(*file_rows, cls="dr-folder-files"),
        cls="dr-folder",
        open=is_open,
    )


def _company_display_name(slug: str) -> str:
    try:
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT name FROM {DB_SCHEMA}.companies WHERE slug = %s", (slug,))
            row = cur.fetchone()
            if row:
                return row[0] if isinstance(row, (list, tuple)) else row.get("name", slug)
    except Exception:
        pass
    return slug.replace("_", " ").title()


def _get_user_id(session) -> tuple[str | None, str | None]:
    user = session.get("user")
    if user:
        return user.get("user_id"), user.get("email")
    return None, None


@ar("/app/dataroom")
def dataroom_home(session):
    from components.chat_shell import left_pane, right_pane

    uid, email = _get_user_id(session)

    docs = []
    companies = []
    if uid:
        try:
            from utils.database import get_conn
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, filename, content_type, size_bytes, company_slug, uploaded_at "
                    "FROM liquidround.data_room WHERE user_id = %s ORDER BY uploaded_at DESC",
                    (uid,),
                )
                col_names = [desc[0] for desc in cur.description]
                for row in cur.fetchall():
                    docs.append(dict(zip(col_names, row)))
                cur.execute(f"SELECT slug, name FROM {DB_SCHEMA}.companies ORDER BY name LIMIT 100")
                co_cols = [desc[0] for desc in cur.description]
                for row in cur.fetchall():
                    companies.append(dict(zip(co_cols, row)))
        except Exception:
            log.exception("Failed to load data room")

    upload_form = Form(
        Div(
            Div(
                Label("File", cls="dr-label"),
                Input(type="file", name="file", required=True, cls="dr-file-input",
                      multiple=True,
                      accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.pptx,.ppt,.png,.jpg,.jpeg,.gif,.txt"),
                cls="dr-field",
            ),
            Div(
                Label("Company", cls="dr-label"),
                Select(
                    Option("General", value=""),
                    *[Option(c["name"][:40], value=c["slug"]) for c in companies],
                    name="company_slug", cls="dr-select",
                ),
                cls="dr-field",
            ),
            Button("Upload", type="submit", cls="dr-upload-btn"),
            cls="dr-upload-bar",
        ),
        method="post",
        action="/app/dataroom/upload",
        enctype="multipart/form-data",
    )

    folders: dict[str, list[dict]] = defaultdict(list)
    for d in docs:
        key = d["company_slug"] or "__general__"
        folders[key].append(d)

    folder_nodes = []
    company_keys = sorted([k for k in folders if k != "__general__"],
                          key=lambda k: _company_display_name(k).lower())
    for i, slug in enumerate(company_keys):
        name = _company_display_name(slug)
        folder_nodes.append(
            _folder_node(name, folders[slug], f"dr-{slug}", is_open=(i == 0))
        )
    if "__general__" in folders:
        folder_nodes.append(
            _folder_node("General", folders["__general__"],
                         "dr-general", is_open=not company_keys)
        )

    if docs:
        tree = Div(*folder_nodes, cls="dr-tree")
    else:
        tree = Div(P("No documents uploaded yet. Use the form above to add files.",
                     cls="search-empty"))

    sessions_list = []
    user = session.get("user")
    if user and user.get("user_id"):
        try:
            from utils.database import db_service
            convs = db_service.get_user_conversations(user["user_id"], limit=20) or []
            sessions_list = [{"id": c["id"], "title": c.get("conversation_title") or c.get("user_query", "Untitled")}
                             for c in convs]
        except Exception:
            pass

    return (
        Title("Data Room · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(
                user_email=email,
                sessions=sessions_list,
                current_sid="",
                current_path="/app/dataroom",
                current_currency=session.get("currency", "EUR"),
                current_role=session.get("role", "buyer"),
            ),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
                        Span("Data Room", cls="chat-header-title"),
                        Span("·", cls="chat-header-dot"),
                        Span(f"{len(docs)} files" if docs else "empty",
                             cls="chat-header-agent"),
                        cls="chat-header-left",
                    ),
                    Div(
                        A("⬇ PDF", href="/app/dataroom/pdf",
                          style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;"
                                "font-size:12px;font-weight:600;color:#F59E0B;"
                                "border:1px solid rgba(245,158,11,.4);border-radius:6px;"
                                "text-decoration:none;"),
                        cls="chat-header-actions",
                    ),
                    cls="chat-header",
                ),
                Div(
                    upload_form,
                    tree,
                    cls="companies-wrap",
                ),
                cls="center-pane pipeline-center",
            ),
            right_pane(),
            cls="app",
        ),
        Script(src="/chat.js?v=4"),
    )


@ar("/app/dataroom/upload", methods=["POST"])
async def dataroom_upload(request: Request):
    sess = request.session
    uid, _ = _get_user_id(sess)
    if not uid:
        return RedirectResponse("/app/dataroom", status_code=303)

    form = await request.form()
    company_slug = (form.get("company_slug") or "").strip() or None

    files = form.getlist("file")
    if not files:
        return RedirectResponse("/app/dataroom", status_code=303)

    from utils.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        for upload in files:
            if not hasattr(upload, "read"):
                continue
            data = await upload.read()
            if not data:
                continue
            from utils.security import UPLOAD_MAX_BYTES
            if len(data) > UPLOAD_MAX_BYTES:
                continue
            filename = os.path.basename(upload.filename or "untitled")[:255]
            if not filename or filename in {".", ".."}:
                continue
            content_type = upload.content_type or "application/octet-stream"
            cur.execute(
                "INSERT INTO liquidround.data_room (user_id, company_slug, filename, content_type, size_bytes, data) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (uid, company_slug, filename, content_type, len(data), data),
            )
        conn.commit()

    return RedirectResponse("/app/dataroom", status_code=303)


@ar("/app/dataroom/{doc_id}/download")
def dataroom_download(doc_id: int, session):
    uid, _ = _get_user_id(session)
    if not uid:
        return Response("Not authenticated", status_code=401)
    try:
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT filename, content_type, data FROM liquidround.data_room WHERE id = %s AND user_id = %s",
                (doc_id, uid),
            )
            row = cur.fetchone()
        if not row:
            return Response("Not found", status_code=404)
        filename = row[0] if isinstance(row, (list, tuple)) else row["filename"]
        content_type = row[1] if isinstance(row, (list, tuple)) else row["content_type"]
        data = row[2] if isinstance(row, (list, tuple)) else row["data"]
        return Response(
            content=bytes(data),
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception:
        return Response("Error", status_code=500)


@ar("/app/dataroom/{doc_id}/delete", methods=["POST"])
def dataroom_delete(doc_id: int, session):
    uid, _ = _get_user_id(session)
    if uid:
        try:
            from utils.database import get_conn
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM liquidround.data_room WHERE id = %s AND user_id = %s",
                            (doc_id, uid))
                conn.commit()
        except Exception:
            pass
    return RedirectResponse("/app/dataroom", status_code=303)


@ar("/app/dataroom/pdf")
async def dataroom_pdf(session):
    """Export data room document index as PDF."""
    from utils.page_pdf import build_pdf, pdf_filename, Section, Row
    from starlette.responses import FileResponse, JSONResponse
    from utils.database import get_conn

    user = session.get("user")
    if not user:
        return JSONResponse({"error": "Sign in required"}, status_code=401)

    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT filename, doc_type, company_slug, uploaded_at "
                "FROM liquidround.documents WHERE user_id = %s ORDER BY uploaded_at DESC",
                (user["user_id"],),
            )
            cols = [d[0] for d in cur.description]
            docs = [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        docs = []

    rows = [Row([
        d.get("filename", ""),
        (d.get("doc_type") or "general").replace("_", " ").title(),
        d.get("company_slug") or "General",
        str(d.get("uploaded_at", ""))[:10],
    ]) for d in docs]

    sections = [Section(f"Data Room — {len(docs)} documents",
                        headers=["Filename", "Type", "Company", "Uploaded"],
                        rows=rows)]
    path = build_pdf("Data Room", "Document index", sections)
    fname = pdf_filename("Data-Room")
    return FileResponse(str(path), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})
