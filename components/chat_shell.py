"""3-pane chat shell for /app — ported faithfully from pehero/chat/components.py.

Composes left_pane (Sessions / Agents / Workspace / Configuration),
center_pane (header + messages + welcome hero + chat input + sample cards),
and right_pane (artifact canvas, filled by SSE artifact_show events).

Uses the navy+amber palette defined in static/app.css. The JS in
static/chat.js drives SSE streaming and all interactive behavior
(toggleGroup, updateSampleCards, setCurrency, setRole, etc.).
"""
from __future__ import annotations

import json
from fasthtml.common import (
    Div, Span, Button, A, P, H1, H3, H4, NotStr,
    Form, Textarea, Input, Hr, Table, Thead, Tbody, Tr, Th, Td,
    Script,
)

from agents.registry import AGENTS, AGENTS_BY_CATEGORY, AGENTS_BY_SLUG, CATEGORIES

CURRENCIES = ("EUR", "GBP", "USD")
CURRENCY_SYMBOLS = {"EUR": "€", "GBP": "£", "USD": "$"}


# ───── Small atoms ───────────────────────────────────────────────────

def message_bubble(role: str, content: str, agent_slug: str | None = None):
    """Render one persisted message (user or assistant)."""
    header = None
    if role == "assistant" and agent_slug:
        spec = AGENTS_BY_SLUG.get(agent_slug)
        label = spec.name if spec else agent_slug
        header = Div(
            Span(spec.icon if spec else "◆", cls="msg-agent-icon"),
            Span(label, cls="msg-agent-label"),
            cls="msg-agent",
        )
    return Div(
        header,
        Div(NotStr(_content_html(content)), cls="msg-bubble"),
        cls=f"msg msg-{role}",
    )


def _content_html(content: str) -> str:
    """Trivial dependency-free markdown-ish renderer."""
    import html, re
    safe = html.escape(content or "")
    safe = re.sub(r"```(.*?)```", lambda m: f"<pre>{m.group(1)}</pre>", safe, flags=re.DOTALL)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"(?m)^- (.*)$", r"<li>\1</li>", safe)
    safe = re.sub(r"(<li>.*?</li>\n?)+", r"<ul>\g<0></ul>", safe, flags=re.DOTALL)
    safe = safe.replace("\n", "<br>")
    return safe


# ───── Left pane sections ────────────────────────────────────────────

def sessions_list(sessions: list[dict] | None, current_sid: str = ""):
    if not sessions:
        return Div(P("No sessions yet — send a message to start.", cls="sessions-empty"))
    items = []
    for s in sessions:
        is_active = str(s.get("id", "")) == str(current_sid)
        title = s.get("title") or s.get("user_query") or "Untitled session"
        items.append(Button(
            Span(cls=f"chat-dot{' active' if is_active else ''}"),
            Span(title[:48] + ("…" if len(title) > 48 else ""), cls="chat-session-title"),
            cls=f"chat-history-item{' active' if is_active else ''}",
            onclick=f"window.location.href='/app?sid={s.get('id','')}'",
            type="button",
        ))
    return Div(*items, cls="session-list")


def agent_browser():
    """All 22 agents grouped by the 5 categories — collapsible."""
    groups = []
    for cat in CATEGORIES:
        agents = AGENTS_BY_CATEGORY.get(cat["key"], [])
        buttons = [
            Button(
                Span(a.icon, cls="aitem-icon"),
                Span(a.name, cls="aitem-name"),
                Span(a.prefix, cls="aitem-prefix"),
                cls="agent-item",
                onclick=f"fillChat({a.prefix + ' '!r})",
                title=a.one_liner,
                type="button",
            )
            for a in agents
        ]
        groups.append(Div(
            Button(
                Span(cat["icon"], cls="cat-icon"),
                Span(cat["name"], cls="cat-name"),
                Span(str(len(agents)), cls="cat-count"),
                Span("▸", cls="cat-arrow"),
                cls="cat-toggle",
                onclick=f"toggleGroup('cat-{cat['key']}')",
                id=f"btn-cat-{cat['key']}",
                type="button",
            ),
            Div(*buttons, cls="agent-list", id=f"cat-{cat['key']}"),
            cls="agent-group",
        ))
    return Div(*groups, cls="agent-browser")


def config_section(current_currency: str = "EUR", current_role: str = "buyer"):
    """Currency selector + role toggle."""
    currency_pills = [
        Button(
            Span(CURRENCY_SYMBOLS[c], cls="cfg-sym"),
            Span(c, cls="cfg-code"),
            cls=f"cfg-chip{' active' if c == current_currency else ''}",
            onclick=f"setCurrency({c!r})",
            type="button",
            **{"data-code": c},
        )
        for c in CURRENCIES
    ]
    role_pills = [
        Button(
            Span(label, cls="cfg-code"),
            cls=f"cfg-role-chip role-{code}{' active' if code == current_role else ''}",
            onclick=f"setRole({code!r})",
            type="button",
            **{"data-role": code},
        )
        for code, label in [("buyer", "Buyer"), ("seller", "Seller"), ("both", "Both")]
    ]
    return Div(
        Div(Span("Currency", cls="cfg-label"),
            Span("affects agents + displays", cls="cfg-help"),
            cls="cfg-row"),
        Div(*currency_pills, cls="cfg-pills"),
        Div(Span("Default view", cls="cfg-label"),
            Span("buyer / seller / both", cls="cfg-help"),
            cls="cfg-row", style="margin-top:.7rem;"),
        Div(*role_pills, cls="cfg-role-pills"),
        cls="config-section",
    )


def bottom_nav(current_path: str = ""):
    items = [
        ("Companies",    "/app/companies",     "⊞"),
        ("Pipelines",    "/pipeline/target",   "◆"),
        ("Valuation",    "/app/valuation",     "◎"),
        ("Analytics",    "/app/analytics",     "◇"),
        ("Data Room",    "/app/dataroom",      "◈"),
        ("Documents",    "/page/documents",    "▦"),
        ("Deal history", "/page/deals",        "∑"),
        ("Instructions", "/app/instructions",  "✎"),
        ("Help",         "/app/help",          "?"),
        ("Settings",     None,                 "⚙"),
    ]
    links = []
    for label, href, icon in items:
        active = href and current_path.startswith(href)
        if href:
            links.append(A(
                Span(icon, cls="bottom-nav-icon"),
                Span(label, cls="bottom-nav-label"),
                href=href,
                cls=f"bottom-nav-link{' active' if active else ''}",
            ))
        else:
            # Settings opens via the chat "settings" command
            links.append(Button(
                Span(icon, cls="bottom-nav-icon"),
                Span(label, cls="bottom-nav-label"),
                cls="bottom-nav-link",
                onclick="fillChat('settings'); sendMessage(null);",
                type="button",
            ))
    return Div(*links, cls="bottom-nav")


def left_pane(*, user_email: str | None = None, sessions: list[dict] | None = None,
              current_sid: str = "", current_path: str = "",
              current_currency: str = "EUR", current_role: str = "buyer"):
    """Composes the full left pane — pehero-faithful."""
    if user_email:
        signin_block = Div(
            Span("◇", cls="user-mark"),
            Span(user_email, cls="user-email"),
            Button("Sign out", cls="sign-out-btn", onclick="signOut()", type="button"),
            cls="signed-in-bar",
        )
    else:
        signin_block = Button(
            Span("◇", cls="user-mark"),
            Span("Sign in", cls="sign-in-text"),
            cls="sign-in-btn", onclick="showSignIn()", type="button",
        )

    return Div(
        # Brand header
        Div(
            A(Span("◆", cls="brand-mark"), Span("LiquidRound"),
              href="/", cls="brand-link"),
            Span("Beta", cls="brand-badge"),
            cls="left-header",
        ),
        # Body: sessions / agents / workspace / configuration
        Div(
            Div(
                Button("+ New chat", cls="new-chat-btn", onclick="newChat()", type="button"),
                Div(Span("Sessions", cls="section-label")),
                sessions_list(sessions, current_sid),
                cls="sessions-section",
            ),
            Hr(cls="left-hr"),
            Div(
                Div(Span("Agents", cls="section-label")),
                agent_browser(),
                cls="agents-section",
            ),
            Hr(cls="left-hr"),
            Div(
                Div(Span("Workspace", cls="section-label")),
                bottom_nav(current_path),
                cls="workspace-section",
            ),
            Hr(cls="left-hr"),
            Div(
                Div(Span("Training", cls="section-label")),
                Div(
                    A(
                        Span("🏦", cls="bottom-nav-icon"),
                        Span("Deal Street", cls="bottom-nav-label"),
                        href="/app/training",
                        cls=f"bottom-nav-link{' active' if current_path.startswith('/app/training') else ''}",
                    ),
                    cls="bottom-nav",
                ),
                cls="training-section",
            ),
            Hr(cls="left-hr"),
            Div(
                Div(Span("Configuration", cls="section-label")),
                config_section(current_currency=current_currency, current_role=current_role),
                cls="config-wrap",
            ),
            cls="left-body",
        ),
        Div(signin_block, cls="left-footer"),
        cls="left-pane", id="left-pane",
    )


# ───── Center pane ───────────────────────────────────────────────────

def welcome_hero(current_role: str = "buyer"):
    """Empty-state hero with a curated 6-pack of example prompts."""
    # Prompts tilted to match the active role
    if current_role == "seller":
        prompts = [
            ("buyers: SaaS EUR 15M revenue, EU", "buyer_scanner"),
            ("teaser: blind teaser for NovaTech", "teaser_designer"),
            ("ipo: Ignitis Group readiness", "ipo_readiness"),
            ("legal: open litigation risks", "legal_reviewer"),
            ("dcf: Harju Elekter 9% WACC", "dcf_valuer"),
            ("research: Nordic M&A 2026", "research_analyst"),
        ]
        sub = "Your AI ECM / IB analyst squad for sell-side M&A and IPO readiness. Upload your pitch book and they'll read, cite and draft from it."
    else:
        prompts = [
            ("triage: Nordic SaaS, EUR 8M EBITDA, 20% growth", "deal_triage"),
            ("profile: SAP.DE", "company_profiler"),
            ("dcf: Harju Elekter at 9% WACC", "dcf_valuer"),
            ("memo: draft the IC memo for Meridian", "ic_memo_writer"),
            ("vdr: audit the data room for NovaTech", "vdr_auditor"),
            ("research: Baltic renewable M&A", "research_analyst"),
        ]
        sub = "Your AI ECM / IB analyst squad for buy-side M&A. Type a prompt — the router picks the right analyst."

    return Div(
        Div(
            Span("◆", cls="hero-mark"),
            H1(Span("Liquid"), Span("Round", cls="accent"), cls="welcome-title"),
            P(NotStr("<strong>ECM</strong> = Equity Capital Markets. "), sub, cls="welcome-sub"),
            cls="welcome-head",
        ),
        Div(
            *[Button(
                Span(AGENTS_BY_SLUG[slug].icon if slug in AGENTS_BY_SLUG else "◆", cls="sugg-icon"),
                Span(text, cls="sugg-text"),
                cls="suggestion-chip",
                onclick=f"fillChat({text!r})",
                type="button",
            ) for text, slug in prompts],
            cls="suggestions",
        ),
        id="welcome-hero",
        cls="welcome-hero",
    )


def sample_cards(current_agent_slug: str | None = None):
    """3 example-prompt buttons under the chat input (pehero-style)."""
    if current_agent_slug and current_agent_slug in AGENTS_BY_SLUG:
        spec = AGENTS_BY_SLUG[current_agent_slug]
        prompts = list(spec.example_prompts[:3])
        label = f"Try with {spec.name}"
    else:
        prompts = [
            "triage: Nordic SaaS, EUR 8M EBITDA, 20% growth",
            "dcf: Harju Elekter at 9% WACC, 2.5% terminal growth",
            "memo: draft the IC memo for Meridian Healthcare",
        ]
        label = "Try a prompt"

    chips = [
        Button(
            Span(p, cls="sample-card-text"),
            cls="sample-card",
            onclick=f"fillChat({p!r}); sendMessage(null);",
            title=p,
            type="button",
        )
        for p in prompts
    ]
    return Div(
        Span(label, cls="sample-cards-label", id="sample-cards-label"),
        Div(*chips, id="sample-cards-row", cls="sample-cards-row"),
        id="sample-cards",
        cls="sample-cards",
    )


def center_pane(*, messages: list[dict] | None = None,
                current_agent_slug: str | None = None,
                current_role: str = "buyer",
                readonly: bool = False):
    messages = messages or []
    has_messages = bool(messages)
    bubbles = [message_bubble(m["role"], m["content"], m.get("agent_slug")) for m in messages]

    input_placeholder = "Ask anything — or type a prefix like `triage:`, `memo:`, `dcf:`, `ipo:`."

    prompts_lookup = {a.slug: list(a.example_prompts[:6]) for a in AGENTS}
    names_lookup = {a.slug: a.name for a in AGENTS}

    header_actions = [
        Button("Copy", id="copy-chat-btn", cls="chat-action-btn",
               onclick="copyChat()", type="button"),
    ]
    if not readonly:
        header_actions.append(
            Button("Share", id="share-chat-btn", cls="chat-action-btn",
                   onclick="shareChat()", type="button"),
        )
        header_actions += [
            Button("News", id="news-btn", cls="news-toggle-btn",
                   onclick="toggleNewsPane()", type="button"),
            Button("Artifact", id="artifact-btn", cls="artifact-toggle-btn",
                   onclick="toggleArtifactPane()", type="button"),
        ]

    children = [
        Div(
            Div(
                Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
                Span("LiquidRound", cls="chat-header-title"),
                Span("·", cls="chat-header-dot"),
                Span(
                    AGENTS_BY_SLUG[current_agent_slug].name if current_agent_slug and current_agent_slug in AGENTS_BY_SLUG else "Shared" if readonly else "Auto-routed",
                    cls="chat-header-agent", id="current-agent-label",
                ),
                cls="chat-header-left",
            ),
            Div(*header_actions, cls="chat-header-actions"),
            cls="chat-header",
        ),
        Div(*bubbles, id="messages", cls="messages"),
    ]

    if not readonly:
        children.append(welcome_hero(current_role) if not has_messages else Div(id="welcome-hero", style="display:none"))
        children.append(Form(
            Textarea(
                id="chat-input", name="msg",
                cls="chat-textarea",
                placeholder=input_placeholder,
                rows="2",
                onkeydown="handleKey(event)",
                oninput="autoResize(this); onInputChange(this)",
            ),
            Button("Send", type="submit", cls="chat-send", id="send-btn"),
            id="chat-form",
            cls="chat-form",
            onsubmit="sendMessage(event)",
        ))
        children.append(sample_cards(current_agent_slug))
        children.append(NotStr(f'<script id="agent-prompts-data" type="application/json">{json.dumps(prompts_lookup)}</script>'))
        children.append(NotStr(f'<script id="agent-names-data" type="application/json">{json.dumps(names_lookup)}</script>'))

    return Div(*children, cls="center-pane")


# ───── Right pane ────────────────────────────────────────────────────

def right_pane():
    return Div(
        Div(
            Div(
                Div(
                    Button("Artifact", id="rpane-tab-artifact", cls="rpane-tab active",
                           onclick="switchRightTab('artifact')", type="button"),
                    Button("News", id="rpane-tab-news", cls="rpane-tab",
                           onclick="switchRightTab('news')", type="button"),
                    cls="rpane-tabs",
                ),
                Span("", id="artifact-subtitle", cls="right-subtitle"),
                cls="right-header-left",
            ),
            Button("✕", cls="right-close", onclick="closeRightPane()", type="button"),
            cls="right-header",
        ),
        # Artifact body
        Div(
            Div(
                Div("◈", cls="artifact-empty-icon"),
                P("Artifacts appear here as agents produce them — company profiles, "
                  "DCF tables, match-score matrices, deep-research citations, IC memo previews.",
                  cls="artifact-empty-text"),
                id="artifact-empty",
                cls="artifact-empty",
            ),
            Div(id="artifact-body", cls="artifact-body", style="display:none"),
            id="rpane-content-artifact", cls="right-body",
        ),
        # News body (HTMX auto-refresh)
        Div(
            Div(
                Div("◌", cls="news-loading-icon"),
                P("Loading news...", cls="news-loading-text"),
                id="news-loading",
                cls="news-loading",
            ),
            Div(id="news-body",
                hx_get="/app/news/html",
                hx_trigger="load, every 1800s",
                hx_swap="innerHTML",
                hx_indicator="#news-loading"),
            id="rpane-content-news", cls="right-body", style="display:none",
        ),
        id="right-pane", cls="right-pane",
    )
