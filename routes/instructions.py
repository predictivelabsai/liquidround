"""Skills page — edit + save per-agent system prompts.

/app/skills              → list all agent skills
/app/skills/<slug>       → WYSIWYG editor (default) + markdown toggle + version history
POST /app/skills/<slug>  → persist to file + liquidround.prompt_versions

API:
GET  /app/api/prompt-versions/<slug>       → version list
GET  /app/api/prompt-version/<id>          → single version content
POST /app/api/prompt-versions/<slug>/revert → revert to version
"""

from __future__ import annotations

from pathlib import Path

from fasthtml.common import (
    APIRouter, Title, Script, Link, NotStr,
    Div, Span, H1, P, A, Button,
    Textarea, Input,
)
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import RedirectResponse

from agents.registry import AGENTS, AGENTS_BY_SLUG

ar = APIRouter()

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "system"


def _prompt_db_save(slug: str, content: str, changed_by: str = "web-editor") -> int:
    from utils.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO liquidround.prompt_versions (slug, content, changed_by, status) "
            "VALUES (%s, %s, %s, 'published') RETURNING id",
            (slug, content, changed_by),
        )
        row = cur.fetchone()
        conn.commit()
        return row[0] if isinstance(row, (list, tuple)) else row["id"]


def _prompt_db_count(slug: str) -> int:
    from utils.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM liquidround.prompt_versions WHERE slug = %s", (slug,)
        )
        row = cur.fetchone()
        return row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]


def _prompt_db_latest(slug: str) -> str | None:
    from utils.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT content FROM liquidround.prompt_versions "
            "WHERE slug = %s AND status = 'published' ORDER BY id DESC LIMIT 1",
            (slug,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return row[0] if isinstance(row, (list, tuple)) else row["content"]


def _prompt_db_list(slug: str, limit: int = 50) -> list[dict]:
    from utils.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM liquidround.prompt_versions WHERE slug = %s", (slug,)
        )
        row = cur.fetchone()
        total = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]

        cur.execute(
            "SELECT id, slug, content, changed_by, created_at "
            "FROM liquidround.prompt_versions WHERE slug = %s ORDER BY id DESC LIMIT %s",
            (slug, limit),
        )
        col_names = [desc[0] for desc in cur.description]
        rows = [dict(zip(col_names, r)) for r in cur.fetchall()]

        versions = []
        for i, r in enumerate(rows):
            versions.append({
                "id": r["id"],
                "version": total - i,
                "slug": r["slug"],
                "preview": (r["content"] or "")[:200],
                "changed_by": r["changed_by"] or "",
                "created_at": r["created_at"].isoformat() if r.get("created_at") else "",
            })
        return versions


def _prompt_db_get(version_id: int) -> dict | None:
    from utils.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, slug, content, changed_by, created_at "
            "FROM liquidround.prompt_versions WHERE id = %s",
            (version_id,),
        )
        col_names = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        if not row:
            return None
        r = dict(zip(col_names, row))
        return {
            "id": r["id"],
            "slug": r["slug"],
            "content": r["content"],
            "changed_by": r["changed_by"] or "",
            "created_at": r["created_at"].isoformat() if r.get("created_at") else "",
        }


# ── List page ──────────────────────────────────────────────────────────

@ar("/app/skills")
def instructions_home(session):
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

    items = []
    for a in AGENTS:
        path = PROMPTS_DIR / f"{a.slug}.md"
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        items.append(A(
            Div(
                Span(a.icon, cls="instr-icon"),
                Div(
                    Div(a.name, cls="instr-name"),
                    Div(a.one_liner, cls="instr-sub"),
                ),
                Span(f"{size}b" if exists else "missing", cls="instr-size"),
                cls="instr-row",
            ),
            href=f"/app/skills/{a.slug}",
            cls="instr-link",
        ))

    return (
        Title("Skills · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(
                user_email=email,
                sessions=sessions_list,
                current_sid="",
                current_path="/app/skills",
                current_currency=session.get("currency", "EUR"),
                current_role=session.get("role", "buyer"),
            ),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
                        Span("Skills", cls="chat-header-title"),
                        Span("·", cls="chat-header-dot"),
                        Span(f"{len(AGENTS)} agents", cls="chat-header-agent"),
                        cls="chat-header-left",
                    ),
                    cls="chat-header",
                ),
                Div(
                    P("Manage the skills and operating instructions used by each agent. Changes take effect immediately.",
                      cls="instr-intro"),
                    *items,
                    cls="instr-list",
                ),
                cls="center-pane pipeline-center",
            ),
            right_pane(),
            cls="app",
        ),
        Script(src="/chat.js?v=4"),
    )


# ── Editor page ────────────────────────────────────────────────────────

@ar("/app/skills/{slug}")
def instruction_edit(session, slug: str):
    from components.chat_shell import left_pane, right_pane

    spec = AGENTS_BY_SLUG.get(slug)
    if not spec:
        return Title("Not found"), Div(
            H1("Agent not found"),
            A("Back", href="/app/skills"),
            style="padding:2rem; color:var(--ink);",
        )

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

    path = PROMPTS_DIR / f"{slug}.md"
    try:
        content = _prompt_db_latest(slug)
    except Exception:
        content = None
    if content is None:
        content = path.read_text() if path.exists() else ""
    try:
        vc = _prompt_db_count(slug)
    except Exception:
        vc = 0

    return (
        Title(f"Edit — {spec.name} · LiquidRound"),
        Link(rel="stylesheet", href="https://cdn.quilljs.com/2.0.3/quill.snow.css"),
        Script(src="https://cdn.quilljs.com/2.0.3/quill.js"),
        Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(
                user_email=email,
                sessions=sessions_list,
                current_sid="",
                current_path="/app/skills",
                current_currency=session.get("currency", "EUR"),
                current_role=session.get("role", "buyer"),
            ),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
                        A("← Skills", href="/app/skills", cls="back-to-chat-btn"),
                        Span("·", cls="chat-header-dot"),
                        Span(spec.name, cls="chat-header-title"),
                        Span(f"v{vc}", cls="instr-version-badge", id="version-badge") if vc else
                        Span("", cls="instr-version-badge", id="version-badge"),
                        cls="chat-header-left",
                    ),
                    cls="chat-header",
                ),
                Div(
                    P(spec.one_liner, cls="instr-sub-big"),
                    Div(
                        Button("Editor", cls="instr-tab active", id="tab-editor",
                               onclick="switchTab('editor')"),
                        Button("Markdown", cls="instr-tab", id="tab-markdown",
                               onclick="switchTab('markdown')"),
                        Button("History", cls="instr-tab", id="tab-history",
                               onclick="switchTab('history')"),
                        cls="instr-tab-bar",
                    ),
                    Textarea(content, name="content", id="instr-markdown-src",
                             style="display:none"),
                    Div(id="instr-editor-pane", cls="instr-pane"),
                    Div(
                        Textarea(content, id="instr-markdown-textarea",
                                 cls="instr-textarea", spellcheck="false", rows="28"),
                        id="instr-markdown-pane", cls="instr-pane", style="display:none",
                    ),
                    Div(id="instr-history-pane", cls="instr-pane", style="display:none"),
                    Div(
                        Div(id="save-status", cls="save-status"),
                        Button("Save", type="button", cls="chat-send instr-save",
                               onclick="savePrompt()"),
                        A("Cancel", href="/app/skills", cls="back-to-chat-btn"),
                        cls="instr-actions",
                    ),
                    Input(type="hidden", id="instr-slug", value=slug),
                    cls="instr-edit",
                ),
                cls="center-pane pipeline-center",
            ),
            right_pane(),
            cls="app",
        ),
        Script(src="/chat.js?v=4"),
        Script(src="/instructions.js"),
    )


# ── Save endpoint ──────────────────────────────────────────────────────

@ar("/app/skills/{slug}", methods=["POST"])
async def instruction_save(request: Request, session, slug: str):
    from utils.security import is_admin
    if not is_admin(session):
        return JSONResponse({"ok": False, "error": "Administrator access required"}, status_code=403)
    data = await request.json()
    content = data.get("content") or ""

    if slug not in AGENTS_BY_SLUG:
        return JSONResponse({"ok": False, "error": "Unknown agent"})

    try:
        changed_by = (session.get("user") or {}).get("email", "admin")
        version_id = _prompt_db_save(slug, content, changed_by=changed_by)
        vc = _prompt_db_count(slug)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"Prompt save failed: {exc}"}, status_code=500)

    try:
        from agents.base import cached_agent
        cached_agent.cache_clear()
    except Exception:
        pass

    return JSONResponse({"ok": True, "version_count": vc, "version_id": version_id})


# Legacy bookmarks remain valid while Skills is the canonical URL.
@ar("/app/instructions")
def instructions_legacy():
    return RedirectResponse("/app/skills", status_code=308)


@ar("/app/instructions/{slug}")
def instruction_legacy(slug: str):
    return RedirectResponse(f"/app/skills/{slug}", status_code=308)


# ── Version API ────────────────────────────────────────────────────────

@ar("/app/api/prompt-versions/{slug}")
def api_prompt_versions(slug: str):
    try:
        versions = _prompt_db_list(slug)
    except Exception:
        versions = []
    return JSONResponse({"slug": slug, "versions": versions})


@ar("/app/api/prompt-version/{version_id}")
def api_prompt_version(version_id: int):
    try:
        ver = _prompt_db_get(version_id)
    except Exception:
        ver = None
    if not ver:
        return JSONResponse({"error": "Version not found"}, status_code=404)
    return JSONResponse(ver)


@ar("/app/api/prompt-versions/{slug}/revert", methods=["POST"])
async def api_revert_prompt(request: Request, session, slug: str):
    from utils.security import is_admin
    if not is_admin(session):
        return JSONResponse({"ok": False, "error": "Administrator access required"}, status_code=403)
    data = await request.json()
    version_id = data.get("version_id")
    if not version_id:
        return JSONResponse({"ok": False, "error": "Missing version_id"})

    try:
        ver = _prompt_db_get(version_id)
    except Exception:
        ver = None
    if not ver or ver["slug"] != slug:
        return JSONResponse({"ok": False, "error": "Version not found or slug mismatch"})

    if slug not in AGENTS_BY_SLUG:
        return JSONResponse({"ok": False, "error": "Unknown agent"})

    try:
        actor = (session.get("user") or {}).get("email", "admin")
        _prompt_db_save(slug, ver["content"], changed_by=f"{actor}:revert-from-v{version_id}")
        vc = _prompt_db_count(slug)
    except Exception:
        vc = 0

    try:
        from agents.base import cached_agent
        cached_agent.cache_clear()
    except Exception:
        pass

    return JSONResponse({"ok": True, "version_count": vc, "content": ver["content"]})
