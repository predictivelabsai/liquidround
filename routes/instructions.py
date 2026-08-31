"""Skills page — edit + save per-agent system prompts.

/app/skills              → list all agent skills
/app/skills/<slug>       → WYSIWYG editor (default) + markdown toggle + version history
POST /app/skills/<slug>  → persist a personal or admin-controlled version

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
from utils.prompts import (
    count_prompt_versions,
    get_latest_prompt,
    get_prompt_version,
    get_prompt_versions,
    is_admin_protected_skill,
    prompt_scope_user_id,
    save_prompt_version,
)
from utils.security import is_admin

ar = APIRouter()

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "system"


def _scope_for(session, slug: str) -> str | None:
    user = session.get("user") or {}
    return prompt_scope_user_id(slug, user.get("user_id"))


def _can_edit(session, slug: str) -> bool:
    return not is_admin_protected_skill(slug) or is_admin(session)


def _skill_access_error(slug: str) -> JSONResponse:
    return JSONResponse(
        {
            "ok": False,
            "error": f"{AGENTS_BY_SLUG[slug].name} is managed by an administrator",
        },
        status_code=403,
    )


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
        protected = is_admin_protected_skill(a.slug)
        editable = _can_edit(session, a.slug)
        try:
            version_count = count_prompt_versions(
                a.slug,
                user_id=_scope_for(session, a.slug),
            )
        except Exception:
            version_count = 0
        if protected:
            state_label = "Admin controlled" if not editable else "Admin default"
        elif version_count:
            state_label = f"Your versions · {version_count}"
        else:
            state_label = "Personal"
        items.append(A(
            Div(
                Span(a.icon, cls="instr-icon"),
                Div(
                    Div(a.name, cls="instr-name"),
                    Div(a.one_liner, cls="instr-sub"),
                ),
                Span(state_label if exists else "Missing default", cls="instr-size"),
                cls=f"instr-row{' instr-row-locked' if protected and not editable else ''}",
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
                        Span(f"{len(AGENTS)} skills", cls="chat-header-agent"),
                        cls="chat-header-left",
                    ),
                    cls="chat-header",
                ),
                Div(
                    P(
                        "Personalize each agent for your workflow. Your edits are private to "
                        "your account and take effect on your next chat; sensitive operational "
                        "skills are marked Admin controlled.",
                        cls="instr-intro",
                    ),
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

@ar("/app/skills/{slug}", methods=["GET"])
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
    protected = is_admin_protected_skill(slug)
    editable = _can_edit(session, slug)
    scope_user_id = _scope_for(session, slug)

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
        content = get_latest_prompt(slug, user_id=scope_user_id)
    except Exception:
        content = None
    if content is None:
        content = path.read_text() if path.exists() else ""
    try:
        vc = count_prompt_versions(slug, user_id=scope_user_id)
    except Exception:
        vc = 0

    if protected:
        access_note = Div(
            Span("Admin controlled", cls="instr-access-label"),
            Span(
                "This operational skill is shared across the workspace. "
                + ("You can edit the global default." if editable else "You can review it, but only an administrator can change it."),
                cls="instr-access-copy",
            ),
            cls="instr-access-note instr-access-admin",
        )
    else:
        personal_copy = (
            "This personal version is active for your account. Further edits and "
            "version history remain private to you."
            if vc
            else "Edits and version history are private to your account. Until you "
            "save, this agent uses the workspace default."
        )
        access_note = Div(
            Span("Your skill", cls="instr-access-label"),
            Span(personal_copy, cls="instr-access-copy"),
            cls="instr-access-note",
        )

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
                    access_note,
                    Div(
                        Button("Editor", cls="instr-tab active", id="tab-editor",
                               onclick="switchTab('editor')"),
                        Button("Markdown", cls="instr-tab", id="tab-markdown",
                               onclick="switchTab('markdown')"),
                        *(
                            [Button("History", cls="instr-tab", id="tab-history",
                                    onclick="switchTab('history')")]
                            if editable else []
                        ),
                        cls="instr-tab-bar",
                    ),
                    Textarea(content, name="content", id="instr-markdown-src",
                             style="display:none"),
                    Div(id="instr-editor-pane", cls="instr-pane"),
                    Div(
                        Textarea(content, id="instr-markdown-textarea",
                                 cls="instr-textarea", spellcheck="false", rows="28",
                                 readonly=not editable),
                        id="instr-markdown-pane", cls="instr-pane", style="display:none",
                    ),
                    Div(id="instr-history-pane", cls="instr-pane", style="display:none"),
                    Div(
                        *(
                            [Div(id="save-status", cls="save-status"),
                             Button("Save personal version" if not protected else "Save admin default",
                                    type="button", cls="chat-send instr-save",
                                    onclick="savePrompt()")]
                            if editable else [Span("Read only", cls="instr-readonly-label")]
                        ),
                        A("Cancel", href="/app/skills", cls="back-to-chat-btn"),
                        cls="instr-actions",
                    ),
                    Input(type="hidden", id="instr-slug", value=slug),
                    Input(type="hidden", id="instr-editable", value="true" if editable else "false"),
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
    if slug not in AGENTS_BY_SLUG:
        return JSONResponse({"ok": False, "error": "Unknown agent"}, status_code=404)
    if not _can_edit(session, slug):
        return _skill_access_error(slug)

    data = await request.json()
    content = (data.get("content") or "").strip()
    if not content:
        return JSONResponse({"ok": False, "error": "Skill content cannot be empty"}, status_code=400)
    if len(content) > 100_000:
        return JSONResponse({"ok": False, "error": "Skill content is too large"}, status_code=413)

    try:
        user = session.get("user") or {}
        scope_user_id = _scope_for(session, slug)
        changed_by = user.get("email", "web-editor")
        version_id = save_prompt_version(
            slug,
            content,
            changed_by=changed_by,
            user_id=scope_user_id,
        )
        vc = count_prompt_versions(slug, user_id=scope_user_id)
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
def api_prompt_versions(session, slug: str):
    if slug not in AGENTS_BY_SLUG:
        return JSONResponse({"error": "Unknown agent"}, status_code=404)
    if not _can_edit(session, slug):
        return _skill_access_error(slug)
    try:
        versions = get_prompt_versions(slug, user_id=_scope_for(session, slug))
    except Exception:
        versions = []
    return JSONResponse({"slug": slug, "versions": versions})


@ar("/app/api/prompt-version/{version_id}")
def api_prompt_version(session, version_id: int):
    user = session.get("user") or {}
    if not user.get("user_id"):
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    try:
        # Ordinary users may only access their own versions. Administrators
        # may additionally access global versions for protected skills.
        ver = get_prompt_version(version_id, user_id=user["user_id"])
        if not ver and is_admin(session):
            global_ver = get_prompt_version(version_id, user_id=None)
            if global_ver and is_admin_protected_skill(global_ver["slug"]):
                ver = global_ver
    except Exception:
        ver = None
    if not ver:
        return JSONResponse({"error": "Version not found"}, status_code=404)
    return JSONResponse(ver)


@ar("/app/api/prompt-versions/{slug}/revert", methods=["POST"])
async def api_revert_prompt(request: Request, session, slug: str):
    if slug not in AGENTS_BY_SLUG:
        return JSONResponse({"ok": False, "error": "Unknown agent"}, status_code=404)
    if not _can_edit(session, slug):
        return _skill_access_error(slug)
    data = await request.json()
    version_id = data.get("version_id")
    if not version_id:
        return JSONResponse({"ok": False, "error": "Missing version_id"})

    try:
        scope_user_id = _scope_for(session, slug)
        ver = get_prompt_version(version_id, user_id=scope_user_id)
    except Exception:
        ver = None
    if not ver or ver["slug"] != slug:
        return JSONResponse({"ok": False, "error": "Version not found or slug mismatch"})

    try:
        actor = (session.get("user") or {}).get("email", "web-editor")
        save_prompt_version(
            slug,
            ver["content"],
            changed_by=f"{actor}:revert-from-v{version_id}",
            user_id=scope_user_id,
        )
        vc = count_prompt_versions(slug, user_id=scope_user_id)
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": f"Prompt revert failed: {exc}"},
            status_code=500,
        )

    try:
        from agents.base import cached_agent
        cached_agent.cache_clear()
    except Exception:
        pass

    return JSONResponse({"ok": True, "version_count": vc, "content": ver["content"]})
