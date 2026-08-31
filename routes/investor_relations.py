"""Investor Relations workspace — researched press-release drafting and export."""
from __future__ import annotations

import json
import re
import uuid
from datetime import date
from pathlib import Path

from fasthtml.common import (
    APIRouter, Title, Script, Div, Span, H1, H2, P, A, Button, Form,
    Input, Textarea, Select, Option, Label, NotStr, Details, Summary,
)
from starlette.requests import Request
from starlette.responses import Response, JSONResponse, FileResponse
from starlette.responses import RedirectResponse

ar = APIRouter()


@ar("/app/investor-relations")
def investor_relations_home():
    return RedirectResponse("/app/investor-relations/press-release", status_code=307)


def _field(label: str, control, help_text: str = ""):
    return Div(
        Label(label, cls="ir-label"),
        control,
        P(help_text, cls="ir-help") if help_text else "",
        cls="ir-field",
    )


def _shell(session, body):
    from components.chat_shell import left_pane, right_pane

    user = session.get("user") or {}
    return (
        Title("Press Release Creator · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(
                user_email=user.get("email"),
                sessions=[],
                current_sid="",
                current_path="/app/investor-relations/press-release",
                current_currency=session.get("currency", "EUR"),
                current_role=session.get("role", "buyer"),
            ),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
                        Span("Investor Relations", cls="chat-header-title"),
                        Span("·", cls="chat-header-dot"),
                        Span("Press Release Creator", cls="chat-header-agent"),
                        cls="chat-header-left",
                    ),
                    cls="chat-header",
                ),
                body,
                cls="center-pane pipeline-center",
            ),
            right_pane(),
            cls="app",
        ),
        Script(src="/chat.js?v=4"),
        Script(src="/investor-relations.js?v=1"),
    )


@ar("/app/investor-relations/press-release")
def press_release_creator(session):
    release_types = (
        "Corporate update", "Earnings / financial results", "M&A transaction",
        "Partnership", "Executive appointment", "Funding", "Product launch",
        "Market expansion", "ESG / sustainability", "Other",
    )
    body = Div(
        Div(
            H1("Create a researched press release", cls="ir-title"),
            P("Give the agent a topic and any facts you already have. It will research current primary sources, draft the release, and flag anything that still needs verification.",
              cls="ir-intro"),
            Form(
                _field(
                    "Topic *",
                    Textarea(name="topic", required=True, rows="3", cls="ir-input",
                             placeholder="e.g. Acme opens a new manufacturing facility in Tallinn"),
                    "The only required field.",
                ),
                Div(
                    _field("Company", Input(name="company", cls="ir-input", placeholder="Company name or website")),
                    _field("Release type", Select(*[Option(x, value=x) for x in release_types],
                                                  name="release_type", cls="ir-input")),
                    cls="ir-grid",
                ),
                _field("Approved facts and figures", Textarea(name="key_facts", rows="4", cls="ir-input",
                                                              placeholder="Dates, amounts, locations, milestones and claims approved for disclosure…"),
                       "Unknown facts remain visibly marked for verification."),
                Details(
                    Summary("Optional drafting, compliance and distribution details", cls="ir-advanced-summary"),
                    Div(
                    _field("Language", Select(Option("English", value="English"),
                                               Option("Estonian", value="Estonian"),
                                               Option("Finnish", value="Finnish"),
                                               Option("Swedish", value="Swedish"),
                                               Option("German", value="German"),
                                               Option("French", value="French"),
                                               name="language", cls="ir-input")),
                    _field("Tone", Select(Option("Investor relations", value="Investor relations"),
                                           Option("Corporate", value="Corporate"),
                                           Option("Concise / wire style", value="Concise wire style"),
                                           Option("Technical", value="Technical"),
                                           name="tone", cls="ir-input")),
                        cls="ir-grid",
                    ),
                    _field("Audience", Input(name="audience", cls="ir-input",
                                             placeholder="Investors, customers, media, employees…")),
                    Div(
                    _field("Quote guidance", Textarea(name="quotes", rows="3", cls="ir-input",
                                                      placeholder="Approved quote, speaker and title — or points for a draft quote")),
                    _field("Company boilerplate", Textarea(name="boilerplate", rows="3", cls="ir-input",
                                                           placeholder="Paste an approved boilerplate, or let the agent research one")),
                        cls="ir-grid",
                    ),
                    Div(
                    _field("Investor contact", Input(name="investor_contact", cls="ir-input",
                                                     placeholder="Name, email, phone")),
                    _field("Media contact", Input(name="media_contact", cls="ir-input",
                                                  placeholder="Name, email, phone")),
                        cls="ir-grid",
                    ),
                    _field("Additional instructions", Textarea(name="instructions", rows="3", cls="ir-input",
                                                               placeholder="Target length, embargo, exchange requirements, links…")),
                    cls="ir-advanced",
                ),
                Button("Research and draft release", type="submit", cls="chat-send ir-generate"),
                P("Research can take up to a minute. Legal/compliance review is still required before publication.",
                  cls="ir-help"),
                hx_post="/app/investor-relations/press-release/generate",
                hx_target="#ir-result",
                hx_swap="innerHTML",
                hx_indicator="#ir-loading",
                cls="ir-form",
            ),
            Div("Researching sources and drafting…", id="ir-loading", cls="htmx-indicator ir-loading"),
            Div(id="ir-result"),
            cls="ir-wrap",
        ),
        cls="ir-scroll",
    )
    return _shell(session, body)


def _research_text(result: dict) -> tuple[str, list[dict]]:
    sources = []
    for group in ("tavily", "exa"):
        for item in result.get(group, {}).get("results", [])[:6]:
            sources.append({
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "content": item.get("content") or item.get("snippet") or "",
            })
    context = "\n\n".join(
        f"SOURCE: {s['title']}\nURL: {s['url']}\nEXCERPT: {s['content'][:1200]}"
        for s in sources
    )
    return context, sources


@ar("/app/investor-relations/press-release/generate", methods=["POST"])
async def generate_release(request: Request):
    form = await request.form()
    data = {k: str(form.get(k, "")).strip() for k in (
        "topic", "company", "release_type", "language", "tone", "audience",
        "key_facts", "quotes", "boilerplate", "investor_contact",
        "media_contact", "instructions",
    )}
    if not data["topic"]:
        return Div(P("Please enter a topic.", cls="ir-error"))

    from utils.research_tools import research_tools
    query = " ".join(x for x in (data["company"], data["topic"], "official announcement investor relations") if x)
    try:
        research = await research_tools.deep_research(query)
    except Exception as exc:
        research = {"error": str(exc)}
    context, sources = _research_text(research)

    from agents.base import load_system_prompt
    from utils.llm_factory import create_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    brief = json.dumps(data, ensure_ascii=False, indent=2)
    prompt = (
        f"Today is {date.today().isoformat()}.\n\nGUIDED BRIEF:\n{brief}\n\n"
        f"WEB RESEARCH:\n{context or 'No web results were available. Use placeholders for unverified facts.'}\n\n"
        "Draft the complete press release now. Include source URLs in the verification notes."
    )
    try:
        llm = create_llm(temperature=0.2)
        response = await llm.ainvoke([
            SystemMessage(content=load_system_prompt(
                "press_release_writer",
                user_id=((request.session.get("user") or {}).get("user_id")),
            )),
            HumanMessage(content=prompt),
        ])
        markdown = str(response.content).strip()
    except Exception as exc:
        return Div(
            P("The release could not be generated. Please try again.", cls="ir-error"),
            P(str(exc), cls="ir-help"),
        )

    request.session["press_release_draft"] = markdown
    request.session["press_release_title"] = data["company"] or data["topic"][:60]
    source_links = [
        A(s["title"] or s["url"], href=s["url"], target="_blank", rel="noopener", cls="ir-source")
        for s in sources if s["url"]
    ]
    return Div(
        Div(
            H2("Draft release", cls="ir-result-title"),
            Div(
                Button("Copy", type="button", onclick="copyRelease()", cls="ir-action"),
                Form(Input(type="hidden", name="markdown", value=markdown),
                     Button("Markdown", type="submit", cls="ir-action"),
                     action="/app/investor-relations/press-release/markdown", method="post"),
                Form(Input(type="hidden", name="markdown", value=markdown),
                     Input(type="hidden", name="title", value=data["company"] or "Press Release"),
                     Button("Word", type="submit", cls="ir-action"),
                     action="/app/export/docx", method="post"),
                Form(Input(type="hidden", name="markdown", value=markdown),
                     Button("PDF", type="submit", cls="ir-action"),
                     action="/app/investor-relations/press-release/pdf", method="post"),
                Button("Save to workspace", type="button", cls="ir-action ir-save",
                       hx_post="/app/investor-relations/press-release/save",
                       hx_target="#ir-save-status", hx_swap="innerHTML"),
                Span(id="ir-save-status", cls="ir-save-status"),
                cls="ir-actions",
            ),
            cls="ir-result-head",
        ),
        Textarea(markdown, id="ir-release-markdown", cls="ir-output", rows="28"),
        Div(P("Research sources", cls="ir-label"), *source_links, cls="ir-sources") if source_links else "",
        cls="ir-result",
    )


def _safe_name(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-")[:60] or "press-release"


@ar("/app/investor-relations/press-release/markdown", methods=["POST"])
async def export_markdown(request: Request):
    form = await request.form()
    markdown = str(form.get("markdown", ""))
    return Response(markdown, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="press-release.md"'})


@ar("/app/investor-relations/press-release/pdf", methods=["POST"])
async def export_pdf(request: Request):
    form = await request.form()
    markdown = str(form.get("markdown", ""))
    title = request.session.get("press_release_title", "Press Release")
    from chat_memo_pdf import markdown_to_pdf, _session_dir
    fid = uuid.uuid4().hex
    path = _session_dir(request.session) / f"{fid}.pdf"
    markdown_to_pdf(markdown, path, title=title)
    return FileResponse(path, media_type="application/pdf",
                        filename=f"{_safe_name(title)}.pdf")


@ar("/app/investor-relations/press-release/save", methods=["POST"])
async def save_release(request: Request):
    markdown = request.session.get("press_release_draft", "")
    title = request.session.get("press_release_title", "Press Release")
    user = request.session.get("user") or {}
    uid = user.get("user_id")
    if not markdown:
        return Span("Nothing to save.", cls="ir-error")
    if not uid:
        return Span("Sign in to save.", cls="ir-error")

    filename = f"{_safe_name(title)}.md"
    try:
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO liquidround.data_room "
                "(user_id, company_slug, filename, content_type, size_bytes, data) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (uid, "investor-relations", filename, "text/markdown",
                 len(markdown.encode("utf-8")), markdown.encode("utf-8")),
            )
            conn.commit()
    except Exception:
        return Span("Could not save to workspace.", cls="ir-error")
    return Span("Saved to Data Room.", cls="ir-success")
