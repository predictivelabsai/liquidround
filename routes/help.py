"""Help / User Guide page — renders docs/user_guide.md as a FastHTML page
with a sticky TOC at the top.

/app/help → rendered user guide
"""

from __future__ import annotations

import re
from pathlib import Path

from fasthtml.common import (
    APIRouter, Title, Script,
    Div, Span, H1, H2, H3, H4, P, A, Button, Img,
    Table, Thead, Tbody, Tr, Th, Td,
    Ul, Li, Hr, Nav, NotStr,
)

ar = APIRouter()
_GUIDE_PATH = Path(__file__).resolve().parent.parent / "docs" / "user_guide.md"


def _extract_toc(md: str) -> list[tuple[str, str]]:
    toc = []
    for line in md.split("\n"):
        line = line.strip()
        if line.startswith("## ") and not line.startswith("## Table of Contents"):
            title = line[3:]
            slug = _slugify(title)
            toc.append((title, slug))
    return toc


def _build_toc(toc: list[tuple[str, str]]) -> Nav:
    links = [A(title, href=f"#{slug}", cls="guide-toc-link") for title, slug in toc]
    return Nav(
        Div(*links, cls="guide-toc-links"),
        cls="guide-toc",
    )


def _md_to_components(md: str) -> list:
    import html as _html
    from fasthtml.common import Blockquote

    elements = []
    lines = md.split("\n")
    i = 0
    in_table = False
    table_rows = []
    in_list = False
    list_items = []
    in_code = False
    code_lines = []
    in_quote = False
    quote_lines = []
    skip_toc = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped == "## Table of Contents":
            skip_toc = True
            i += 1
            continue
        if skip_toc:
            if stripped.startswith("## ") and stripped != "## Table of Contents":
                skip_toc = False
            elif stripped.startswith("---"):
                skip_toc = False
                i += 1
                continue
            else:
                i += 1
                continue

        if stripped.startswith("```"):
            if in_code:
                from fasthtml.common import Pre, Code
                elements.append(Pre(Code("\n".join(code_lines)), cls="guide-code"))
                code_lines = []
                in_code = False
            else:
                if in_list:
                    elements.append(Ul(*list_items, cls="guide-list"))
                    list_items = []
                    in_list = False
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            if re.fullmatch(r"\|[\s\-:|]+\|", stripped):
                i += 1
                continue
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            if not in_table:
                if in_list:
                    elements.append(Ul(*list_items, cls="guide-list"))
                    list_items = []
                    in_list = False
                in_table = True
                table_rows = []
            table_rows.append(cells)
            i += 1
            continue

        if in_table:
            header = table_rows[0] if table_rows else []
            body = table_rows[1:] if len(table_rows) > 1 else []
            elements.append(
                Div(
                    Table(
                        Thead(Tr(*[Th(c) for c in header])) if header else None,
                        Tbody(*[Tr(*[Td(NotStr(_inline_md(c))) for c in row]) for row in body]),
                        cls="search-table",
                    ),
                    cls="guide-table-wrap",
                )
            )
            table_rows = []
            in_table = False

        m_num = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if m_num:
            if not in_list:
                in_list = True
            list_items.append(Li(NotStr(_inline_md(m_num.group(2)))))
            i += 1
            continue

        if stripped.startswith("- "):
            if not in_list:
                in_list = True
            list_items.append(Li(NotStr(_inline_md(stripped[2:]))))
            i += 1
            continue

        if in_list:
            elements.append(Ul(*list_items, cls="guide-list"))
            list_items = []
            in_list = False

        if stripped.startswith("> "):
            if not in_quote:
                in_quote = True
                quote_lines = []
            quote_lines.append(stripped[2:])
            i += 1
            continue
        if in_quote:
            elements.append(Blockquote(P(NotStr(_inline_md(" ".join(quote_lines))), cls="guide-p"),
                                       cls="guide-quote"))
            quote_lines = []
            in_quote = False

        if stripped.startswith("# ") and not stripped.startswith("## "):
            elements.append(H1(stripped[2:], cls="guide-h1"))
        elif stripped.startswith("### "):
            elements.append(H3(stripped[4:], cls="guide-h3", id=_slugify(stripped[4:])))
        elif stripped.startswith("## "):
            elements.append(H2(stripped[3:], cls="guide-h2", id=_slugify(stripped[3:])))
        elif stripped.startswith("#### "):
            elements.append(H4(stripped[5:], cls="guide-h4"))
        elif stripped == "---":
            elements.append(Hr(cls="guide-hr"))
        elif stripped.startswith("!["):
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
            if m:
                alt, src = m.group(1), m.group(2)
                if not src.startswith("http"):
                    src = f"/{src}"
                elements.append(Div(Img(src=src, alt=alt, cls="guide-img"), cls="guide-img-wrap"))
        elif stripped:
            elements.append(P(NotStr(_inline_md(stripped)), cls="guide-p"))

        i += 1

    if in_quote:
        elements.append(Blockquote(P(NotStr(_inline_md(" ".join(quote_lines))), cls="guide-p"),
                                   cls="guide-quote"))
    if in_list:
        elements.append(Ul(*list_items, cls="guide-list"))
    if in_table and table_rows:
        header = table_rows[0]
        body = table_rows[1:]
        elements.append(
            Table(
                Thead(Tr(*[Th(c) for c in header])),
                Tbody(*[Tr(*[Td(NotStr(_inline_md(c))) for c in row]) for row in body]),
                cls="search-table",
            )
        )

    return elements


def _inline_md(text: str) -> str:
    import html as _html
    text = _html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r'<code class="guide-inline-code">\1</code>', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" class="guide-link">\1</a>', text)
    return text


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _render_guide(session, current_path="/app/user-guide"):
    from components.chat_shell import left_pane, right_pane

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

    md = _GUIDE_PATH.read_text() if _GUIDE_PATH.exists() else "# User Guide\n\nContent coming soon."
    toc = _extract_toc(md)
    toc_nav = _build_toc(toc)
    content = _md_to_components(md)

    return (
        Title("User Guide · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(
                user_email=email,
                sessions=sessions_list,
                current_sid="",
                current_path=current_path,
                current_currency=session.get("currency", "EUR"),
                current_role=session.get("role", "buyer"),
            ),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
                        Span("User Guide", cls="chat-header-title"),
                        Span("·", cls="chat-header-dot"),
                        Span("LiquidRound", cls="chat-header-agent"),
                        cls="chat-header-left",
                    ),
                    Div(
                        A("⬇ PDF", href="/app/user-guide/pdf",
                          style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;"
                                "font-size:12px;font-weight:600;color:#F59E0B;"
                                "border:1px solid rgba(245,158,11,.4);border-radius:6px;"
                                "text-decoration:none;"),
                        cls="chat-header-actions",
                    ),
                    cls="chat-header",
                ),
                Div(
                    toc_nav,
                    Div(*content, cls="guide-content"),
                    cls="companies-wrap",
                ),
                cls="center-pane pipeline-center",
            ),
            right_pane(),
            cls="app",
        ),
        Script(src="/chat.js?v=4"),
    )


@ar("/app/user-guide")
def user_guide_page(session):
    return _render_guide(session, current_path="/app/user-guide")


@ar("/app/help")
def help_page(session):
    return _render_guide(session, current_path="/app/help")


@ar("/app/user-guide/pdf")
async def user_guide_pdf():
    """Export the user guide as PDF."""
    from utils.page_pdf import build_pdf, pdf_filename, Section
    from starlette.responses import FileResponse

    md = _GUIDE_PATH.read_text() if _GUIDE_PATH.exists() else "User guide not available."
    sections = [Section("LiquidRound User Guide", text=md)]
    path = build_pdf("User Guide", "ECM / IB Analyst Squad documentation", sections)
    fname = pdf_filename("User-Guide")
    return FileResponse(str(path), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})
