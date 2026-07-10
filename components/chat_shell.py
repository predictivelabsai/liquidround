"""3-pane chat shell for /app — ported faithfully from pehero/chat/components.py.

Composes left_pane (Sessions / Agents / Workspace / Settings),
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
from utils.config import VERSION


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

_ICON_SHARE = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'
_ICON_CHECK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'


def sessions_list(sessions: list[dict] | None, current_sid: str = ""):
    if not sessions:
        return Div(P("No sessions yet — send a message to start.", cls="sessions-empty"))
    items = []
    for s in sessions:
        sid = s.get("id", "")
        is_active = str(sid) == str(current_sid)
        title = s.get("title") or s.get("user_query") or "Untitled session"
        items.append(Div(
            Button(
                Span(cls=f"chat-dot{' active' if is_active else ''}"),
                Span(title[:48] + ("…" if len(title) > 48 else ""), cls="chat-session-title"),
                cls=f"chat-history-item{' active' if is_active else ''}",
                onclick=f"window.location.href='/app?sid={sid}'",
                type="button",
            ),
            Button(
                NotStr(_ICON_SHARE),
                cls="session-share-btn",
                title="Copy share link",
                onclick=f"shareSession(event,'{sid}',this)",
                type="button",
            ),
            cls="session-row",
        ))
    return Div(*items, cls="session-list")


def _agent_freeform(spec):
    """Pick the best free-form example for an agent (no prefix)."""
    for p in spec.example_prompts:
        if ":" not in p[:12]:
            return p
    if spec.example_prompts:
        return spec.example_prompts[0]
    return spec.prefix + " "


def agent_browser():
    """All 23 agents grouped by 6 categories — collapsible."""
    groups = []
    for cat in CATEGORIES:
        agents = AGENTS_BY_CATEGORY.get(cat["key"], [])
        buttons = [
            Button(
                Span(a.icon, cls="aitem-icon"),
                Span(a.name, cls="aitem-name"),
                Span(a.prefix, cls="aitem-prefix"),
                cls="agent-item",
                onclick=f"fillChat({_agent_freeform(a)!r})",
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


_WORKSPACE_ITEMS = [
    ("Companies",    "/app/companies",     "⊞"),
    ("Pipelines",    "/pipeline/target",   "◆"),
    ("Daily Radar",  "/app/deals",         "◉"),
    ("Deal Radar",   "/app/deal-radar",    "⊕"),
    ("Methodology",  "/app/methodology",   "◎"),
    ("Data Coverage","/app/data-coverage", "◈"),
    ("Valuation",    "/app/valuation",     "◇"),
    ("Analytics",    "/app/analytics",     "△"),
    ("Data Room",    "/app/dataroom",      "▣"),
    ("Documents",    "/page/documents",    "▦"),
    ("Deal history", "/page/deals",        "∑"),
    ("Instructions", "/app/instructions",  "✎"),
    ("User Guide",   "/app/user-guide",    "?"),
]


def _workspace_links(current_path: str = ""):
    return [
        A(Span(icon, cls="bottom-nav-icon"), Span(label, cls="bottom-nav-label"),
          href=href, cls=f"bottom-nav-link{' active' if href and current_path.startswith(href) else ''}")
        for label, href, icon in _WORKSPACE_ITEMS
    ]


def bottom_nav(current_path: str = ""):
    return Div(*_workspace_links(current_path), cls="bottom-nav")


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
            Span(f"v{VERSION}", cls="brand-version"),
            cls="left-header",
        ),
        # Body: sessions / agents / workspace / settings
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
                Button(
                    Span("🔧", cls="cat-icon"),
                    Span("Tools", cls="cat-name"),
                    Span("3", cls="cat-count"),
                    Span("▸", cls="cat-arrow"),
                    cls="cat-toggle",
                    onclick="toggleGroup('sec-tools')",
                    id="btn-sec-tools",
                    type="button",
                ),
                Div(
                    A(Span("📊", cls="bottom-nav-icon"), Span("Market Comps", cls="bottom-nav-label"),
                      href="/tools/comparables",
                      cls=f"bottom-nav-link{' active' if current_path == '/tools/comparables' else ''}"),
                    A(Span("🔍", cls="bottom-nav-icon"), Span("Find Buyers", cls="bottom-nav-label"),
                      href="/tools/match",
                      cls=f"bottom-nav-link{' active' if current_path == '/tools/match' else ''}"),
                    A(Span("💰", cls="bottom-nav-icon"), Span("Valuation", cls="bottom-nav-label"),
                      href="/tools/valuation",
                      cls=f"bottom-nav-link{' active' if current_path == '/tools/valuation' else ''}"),
                    cls="agent-list", id="sec-tools",
                ),
                cls="agent-group",
            ),
            Hr(cls="left-hr"),
            Div(
                Button(
                    Span("◧", cls="cat-icon"),
                    Span("Public Markets", cls="cat-name"),
                    Span("4", cls="cat-count"),
                    Span("▸", cls="cat-arrow"),
                    cls="cat-toggle",
                    onclick="toggleGroup('sec-public-markets')",
                    id="btn-sec-public-markets",
                    type="button",
                ),
                Div(
                    A(Span("◧", cls="bottom-nav-icon"), Span("IPO Map", cls="bottom-nav-label"),
                      href="/app/ipo-map",
                      cls=f"bottom-nav-link{' active' if current_path.startswith('/app/ipo-map') else ''}"),
                    A(Span("◨", cls="bottom-nav-icon"), Span("IPO Pipeline", cls="bottom-nav-label"),
                      href="/app/ipo-pipeline",
                      cls=f"bottom-nav-link{' active' if current_path.startswith('/app/ipo-pipeline') else ''}"),
                    A(Span("◇", cls="bottom-nav-icon"), Span("SPACs", cls="bottom-nav-label"),
                      href="/app/spacs",
                      cls=f"bottom-nav-link{' active' if current_path.startswith('/app/spacs') else ''}"),
                    A(Span("◰", cls="bottom-nav-icon"), Span("Prospectus", cls="bottom-nav-label"),
                      href="/app/prospectus",
                      cls=f"bottom-nav-link{' active' if current_path.startswith('/app/prospectus') else ''}"),
                    cls="agent-list", id="sec-public-markets",
                ),
                cls="agent-group",
            ),
            Hr(cls="left-hr"),
            Div(
                Button(
                    Span("◉", cls="cat-icon"),
                    Span("Hedge Funds", cls="cat-name"),
                    Span("4", cls="cat-count"),
                    Span("▸", cls="cat-arrow"),
                    cls="cat-toggle",
                    onclick="toggleGroup('sec-hedge-funds')",
                    id="btn-sec-hedge-funds",
                    type="button",
                ),
                Div(
                    A(Span("◉", cls="bottom-nav-icon"), Span("Fund Treemap", cls="bottom-nav-label"),
                      href="/app/hedgefunds",
                      cls=f"bottom-nav-link{' active' if current_path.startswith('/app/hedgefunds') else ''}"),
                    A(Span("▤", cls="bottom-nav-icon"), Span("Top Holdings", cls="bottom-nav-label"),
                      href="/app?q=hedgefunds%3A+top+funds+by+AUM",
                      onclick="if(window.fillChat){fillChat('hedgefunds: top funds by AUM'); sendMessage(null); return false;}",
                      cls="bottom-nav-link"),
                    A(Span("≡", cls="bottom-nav-icon"), Span("Popular Securities", cls="bottom-nav-label"),
                      href="/app?q=hedgefunds%3A+most+popular+securities+across+all+funds",
                      onclick="if(window.fillChat){fillChat('hedgefunds: most popular securities across all funds'); sendMessage(null); return false;}",
                      cls="bottom-nav-link"),
                    A(Span("⚠", cls="bottom-nav-icon"), Span("Activist Filings", cls="bottom-nav-label"),
                      href="/app?q=hedgefunds%3A+recent+activist+filings",
                      onclick="if(window.fillChat){fillChat('hedgefunds: recent activist filings'); sendMessage(null); return false;}",
                      cls="bottom-nav-link"),
                    cls="agent-list", id="sec-hedge-funds",
                ),
                cls="agent-group",
            ),
            Hr(cls="left-hr"),
            Div(
                Button(
                    Span("◆", cls="cat-icon"),
                    Span("Workspace", cls="cat-name"),
                    Span("10", cls="cat-count"),
                    Span("▸", cls="cat-arrow"),
                    cls="cat-toggle",
                    onclick="toggleGroup('sec-workspace')",
                    id="btn-sec-workspace",
                    type="button",
                ),
                Div(
                    *_workspace_links(current_path),
                    cls="agent-list", id="sec-workspace",
                ),
                cls="agent-group",
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
                Button(
                    Span("?", cls="cat-icon"),
                    Span("Help", cls="cat-name"),
                    Span("3", cls="cat-count"),
                    Span("▸", cls="cat-arrow"),
                    cls="cat-toggle",
                    onclick="toggleGroup('sec-help')",
                    id="btn-sec-help",
                    type="button",
                ),
                Div(
                    A(Span("⚙", cls="bottom-nav-icon"), Span("Profile / Account", cls="bottom-nav-label"),
                      href="/profile",
                      cls=f"bottom-nav-link{' active' if current_path.startswith('/profile') else ''}"),
                    A(Span("?", cls="bottom-nav-icon"), Span("User Guide", cls="bottom-nav-label"),
                      href="/app/user-guide",
                      cls=f"bottom-nav-link{' active' if current_path.startswith('/app/user-guide') or current_path.startswith('/app/help') else ''}"),
                    A(Span("⌨", cls="bottom-nav-icon"), Span("Shortcuts", cls="bottom-nav-label"),
                      href="#", onclick="toggleGroup('sec-shortcuts'); return false;",
                      cls="bottom-nav-link"),
                    cls="agent-list", id="sec-help",
                ),
                cls="agent-group",
            ),
            Div(
                Div(
                    *[A(Span(a.prefix, cls="bottom-nav-icon",
                          style="font-family:'JetBrains Mono',monospace; font-size:.65rem; width:auto; min-width:3rem;"),
                        Span(a.name, cls="bottom-nav-label"),
                        href="#",
                        onclick=f"fillChat({a.prefix + ' '!r}); return false;",
                        cls="bottom-nav-link",
                      ) for a in AGENTS],
                    cls="agent-list", id="sec-shortcuts",
                ),
                cls="agent-group",
            ),
            cls="left-body",
        ),
        Div(signin_block, cls="left-footer"),
        cls="left-pane", id="left-pane",
    )


# ───── Center pane ───────────────────────────────────────────────────

def welcome_hero(current_role: str = "buyer"):
    """Empty-state hero with free-form questions + shortcut examples."""
    if current_role == "seller":
        questions = [
            ("Find strategic buyers for a Baltic veterinary chain", "buyer_scanner"),
            ("What are the key risks in Lietuvos Veterinarija's data room?", "vdr_auditor"),
            ("Is Ignitis Group ready for an IPO?", "ipo_readiness"),
            ("What are the top hedge funds holding healthcare stocks?", "hedge_fund_analyst"),
        ]
        shortcuts = [
            ("teaser: blind teaser for Lietuvos Veterinarija", "teaser_designer"),
            ("dcf: Grigeo at 9% WACC", "dcf_valuer"),
            ("research: Baltic healthcare M&A 2026", "research_analyst"),
        ]
        sub = "Your AI ECM / IB analyst squad for sell-side M&A and IPO readiness."
    else:
        questions = [
            ("Find founder-owned vet clinics in the Baltics with EUR 4M+ EBITDA", "target_scanner"),
            ("What's a fair valuation for Grigeo at 9% WACC?", "dcf_valuer"),
            ("Draft the investment committee memo for InMedica", "ic_memo_writer"),
            ("Which hedge funds hold the most Apple shares?", "hedge_fund_analyst"),
        ]
        shortcuts = [
            ("triage: Baltic vet chain, EUR 4M EBITDA, 25% growth", "deal_triage"),
            ("dcf: Grigeo at 9% WACC, 2.5% terminal growth", "dcf_valuer"),
            ("memo: draft the IC memo for InMedica", "ic_memo_writer"),
        ]
        sub = "Your AI ECM / IB analyst squad for buy-side M&A. Type a prompt — the router picks the right analyst."

    return Div(
        Div(
            Span("◆", cls="hero-mark"),
            H1(Span("Liquid"), Span("Round", cls="accent"), cls="welcome-title"),
            P(NotStr("<strong>ECM</strong> = Equity Capital Markets. "), sub, cls="welcome-sub"),
            cls="welcome-head",
        ),
        # Ask a question (free-form)
        Div(
            Span("Ask a question", cls="sugg-section-label"),
            Div(
                *[Button(
                    Span(AGENTS_BY_SLUG[slug].icon if slug in AGENTS_BY_SLUG else "◆", cls="sugg-icon"),
                    Span(text, cls="sugg-text"),
                    cls="suggestion-chip",
                    onclick=f"fillChat({text!r})",
                    type="button",
                ) for text, slug in questions],
                cls="suggestions",
            ),
        ),
        # Try a shortcut (prefix commands)
        Div(
            Span("Try a shortcut", cls="sugg-section-label"),
            Div(
                *[Button(
                    Span(AGENTS_BY_SLUG[slug].icon if slug in AGENTS_BY_SLUG else "◆", cls="sugg-icon"),
                    Span(text, cls="sugg-text"),
                    cls="suggestion-chip shortcut-chip",
                    onclick=f"fillChat({text!r})",
                    type="button",
                ) for text, slug in shortcuts],
                cls="suggestions",
            ),
        ),
        id="welcome-hero",
        cls="welcome-hero",
    )


def sample_cards(current_agent_slug: str | None = None):
    """Example-prompt buttons under the chat input — free-form first, then shortcuts."""
    if current_agent_slug and current_agent_slug in AGENTS_BY_SLUG:
        spec = AGENTS_BY_SLUG[current_agent_slug]
        # Split into free-form questions and shortcuts
        freeform = [p for p in spec.example_prompts if ":" not in p[:12]]
        shortcuts = [p for p in spec.example_prompts if ":" in p[:12]]
        label = f"Try with {spec.name}"
    else:
        freeform = [
            "Find founder-owned vet clinics in the Baltics",
            "What's a fair valuation for Grigeo?",
        ]
        shortcuts = [
            "triage: Baltic vet chain, EUR 4M EBITDA, 25% growth",
            "dcf: Grigeo at 9% WACC, 2.5% terminal growth",
            "memo: draft the IC memo for InMedica",
        ]
        label = "Try a prompt"

    all_prompts = (freeform[:2] + shortcuts[:2]) if not current_agent_slug else (freeform[:2] + shortcuts[:1])
    chips = [
        Button(
            Span(p, cls="sample-card-text"),
            cls="sample-card",
            onclick=f"fillChat({p!r}); sendMessage(null);",
            title=p,
            type="button",
        )
        for p in all_prompts
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

    _icon_clipboard = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
    _icon_share = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'

    header_actions = [
        Button(NotStr(_icon_clipboard), Span("Copy", cls="action-label"),
               id="copy-chat-btn", cls="chat-action-btn",
               onclick="copyChat()", type="button"),
    ]
    if not readonly:
        header_actions.append(
            Button(NotStr(_icon_share), Span("Share", cls="action-label"),
                   id="share-chat-btn", cls="chat-action-btn",
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
