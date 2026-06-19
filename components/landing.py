"""Landing-page FastHTML components.

Dark navy hero, two role CTAs, agent directory, platform/how-it-works pages.
Colors intentionally distinct from sibling PEHero project (parchment + forest).
"""
from __future__ import annotations

from fasthtml.common import *
from utils.config import VERSION

# ───── Palette ──────────────────────────────────────────────────────────
BG        = "#0B1220"   # deep navy
BG_ELEV   = "#111A2E"   # elevated panels
INK       = "#E5E7EB"   # near-white text
INK_MUTED = "#94A3B8"   # slate-400
BUY       = "#3B82F6"   # blue-500
SELL      = "#10B981"   # emerald-500
CTA       = "#F59E0B"   # amber-500 accents
LINE      = "#1E293B"   # slate-800


# ───── Shared chrome ────────────────────────────────────────────────────

_OG_DESC = "AI-powered M&A, IPO readiness, and public markets intelligence. A squad of specialist AI analysts in one chat-first workspace."

def landing_head(title: str = "LiquidRound"):
    """<head> contents for all landing pages."""
    return (
        Title(title),
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Meta(name="theme-color", content=BG),
        Meta(name="description", content=_OG_DESC),
        Meta(property="og:type", content="website"),
        Meta(property="og:site_name", content="LiquidRound"),
        Meta(property="og:title", content=title),
        Meta(property="og:description", content=_OG_DESC),
        Meta(property="og:image", content="https://liquidround.ai/og-image.png"),
        Meta(name="twitter:card", content="summary_large_image"),
        Meta(name="twitter:title", content=title),
        Meta(name="twitter:description", content=_OG_DESC),
        Link(rel="icon", type="image/svg+xml", href="/favicon.svg"),
        Link(rel="icon", type="image/png", sizes="32x32", href="/favicon.png"),
        Link(rel="alternate icon", type="image/x-icon", href="/favicon.ico"),
        Link(rel="apple-touch-icon", sizes="180x180", href="/apple-touch-icon.png"),
        Script(src="https://cdn.tailwindcss.com"),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        Link(href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap", rel="stylesheet"),
        Style(f"""
            html {{ overflow-x: hidden; overflow-y: auto; scrollbar-width: none; }}
            html::-webkit-scrollbar {{ display: none; }}
            html, body {{ background: {BG}; color: {INK}; font-family: 'Inter', system-ui, sans-serif; letter-spacing: -0.01em; margin: 0; }}
            .mono {{ font-family: 'JetBrains Mono', ui-monospace, monospace; }}
            .tighter {{ letter-spacing: -0.025em; }}
            .tightest {{ letter-spacing: -0.04em; }}
            .hero-gradient {{
              background: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(59,130,246,0.12), transparent 70%);
            }}
            .cta-glow-buy  {{ box-shadow: 0 0 40px rgba(59,130,246,0.35); }}
            .cta-glow-sell {{ box-shadow: 0 0 40px rgba(16,185,129,0.30); }}
            a {{ transition: color .15s ease, opacity .15s ease; }}
            .nav-link:hover {{ color: {CTA}; }}
            .card {{ background: {BG_ELEV}; border: 1px solid {LINE}; }}
            .card:hover {{ border-color: {CTA}; }}
        """),
    )


def _lang_dropdown(lang: str = "en"):
    """Flag-emoji language selector dropdown."""
    from utils.i18n import LANGUAGES
    current_flag = LANGUAGES.get(lang, LANGUAGES["en"])["flag"]
    options = [
        A(
            Span(info["flag"], cls="mr-2"),
            Span(info["native"], cls="text-xs"),
            href=f"/set-lang/{code}",
            cls="flex items-center gap-1 px-3 py-1.5 rounded text-sm no-underline",
            style=f"color:{INK_MUTED};" + (f" font-weight:600; color:{CTA};" if code == lang else ""),
        )
        for code, info in LANGUAGES.items()
    ]
    return Div(
        Button(current_flag,
               cls="text-base leading-none px-1.5 py-1 rounded cursor-pointer bg-transparent",
               style=f"border:1px solid transparent;",
               onclick="this.nextElementSibling.classList.toggle('hidden')",
               type="button"),
        Div(*options,
            cls="hidden absolute right-0 top-full mt-1 rounded-lg shadow-lg z-50 py-1 min-w-[130px] flex flex-col",
            style=f"background:{BG_ELEV}; border:1px solid {LINE};"),
        Script("document.addEventListener('click',e=>{if(!e.target.closest('.lang-dd'))document.querySelectorAll('.lang-dd .hidden')||(document.querySelectorAll('.lang-dd>div:last-child').forEach(m=>m.classList.add('hidden')))})"),
        cls="relative lang-dd",
    )


def landing_nav(active: str = "home", lang: str = "en"):
    """Top nav bar — common to all landing pages."""
    from utils.i18n import t
    def link(href: str, label: str, key: str):
        is_active = key == active
        cls = "text-sm nav-link " + ("text-white font-medium" if is_active else "text-slate-400")
        return A(label, href=href, cls=cls)

    nav_items = [
        ("platform", "/platform", t("nav_platform", lang)),
        ("agents",   "/agents",   t("nav_agents", lang)),
        ("tools",    None,        t("nav_tools", lang)),  # dropdown, no direct href
        ("industries", "/industries", t("nav_industries", lang)),
        ("pricing",  "/pricing",  t("nav_pricing", lang)),
    ]

    tools_active = active == "tools"
    tools_cls = "text-sm nav-link cursor-pointer " + ("text-white font-medium" if tools_active else "text-slate-400")
    tools_dropdown = Div(
        Span(t("nav_tools", lang),
             cls=tools_cls,
             onclick="this.nextElementSibling.classList.toggle('hidden')",
             ),
        Div(
            A("Market Comps", href="/tools/comparables",
              cls="block px-4 py-2 text-sm no-underline hover:opacity-80",
              style=f"color:{INK_MUTED};"),
            A("Find Buyers", href="/tools/match",
              cls="block px-4 py-2 text-sm no-underline hover:opacity-80",
              style=f"color:{INK_MUTED};"),
            A("Valuation", href="/tools/valuation",
              cls="block px-4 py-2 text-sm no-underline hover:opacity-80",
              style=f"color:{INK_MUTED};"),
            cls="hidden absolute left-0 top-full mt-1 rounded-lg shadow-lg z-50 py-1 min-w-[160px] flex flex-col",
            style=f"background:{BG_ELEV}; border:1px solid {LINE};",
        ),
        Script("document.addEventListener('click',e=>{if(!e.target.closest('.tools-dd'))document.querySelectorAll('.tools-dd>div:last-child').forEach(m=>m.classList.add('hidden'))})"),
        cls="relative tools-dd",
    )

    # ── Mobile hamburger + drawer (adapted from kanvas) ──
    bar_cls = f"block w-5 h-0.5 mb-1 transition-all"
    hamburger = Button(
        Span(cls=bar_cls, style=f"background:{INK};"),
        Span(cls=bar_cls, style=f"background:{INK};"),
        Span(cls=f"block w-5 h-0.5 transition-all", style=f"background:{INK};"),
        cls="lg:hidden flex flex-col justify-center items-center p-2 bg-transparent border-none cursor-pointer",
        id="mobile-menu-btn",
        aria_label="Open menu",
        onclick="document.getElementById('mobile-menu').classList.toggle('hidden')",
    )

    mobile_links = []
    for key, href, label in nav_items:
        is_active = key == active
        link_color = INK if is_active else INK_MUTED
        if key == "tools":
            mobile_links.append(
                Div(
                    Span(label, cls="block px-4 py-3 text-sm font-medium cursor-pointer",
                         style=f"color:{link_color};",
                         onclick="this.nextElementSibling.classList.toggle('hidden')"),
                    Div(
                        A("Market Comps", href="/tools/comparables",
                          cls="block px-6 py-2 text-sm no-underline", style=f"color:{INK_MUTED};"),
                        A("Find Buyers", href="/tools/match",
                          cls="block px-6 py-2 text-sm no-underline", style=f"color:{INK_MUTED};"),
                        A("Valuation", href="/tools/valuation",
                          cls="block px-6 py-2 text-sm no-underline", style=f"color:{INK_MUTED};"),
                        cls="hidden",
                    ),
                )
            )
        else:
            mobile_links.append(
                A(label, href=href,
                  cls="block px-4 py-3 text-sm no-underline",
                  style=f"color:{link_color};")
            )
    mobile_links.append(
        A(t("nav_sign_in", lang), href="/signin",
          cls="block px-4 py-3 text-sm font-medium no-underline",
          style=f"color:{CTA};")
    )

    mobile_menu = Div(
        *mobile_links,
        id="mobile-menu",
        cls="hidden lg:hidden",
        style=f"background:{BG_ELEV}; border-top:1px solid {LINE};",
    )

    return Div(
        Div(
            A(
                Div(
                    Span("◈", cls="text-xl mr-2", style=f"color:{CTA}"),
                    Span("LiquidRound", cls="text-base font-semibold tighter"),
                    Span(f"v{VERSION}", cls="ml-2 text-[10px] px-1.5 py-0.5 rounded mono hidden sm:inline", style=f"color:#64748b; background:transparent;"),
                    cls="flex items-center",
                ),
                href="/", cls="text-white no-underline",
            ),
            Div(
                link("/platform", t("nav_platform", lang), "platform"),
                link("/agents", t("nav_agents", lang), "agents"),
                tools_dropdown,
                link("/industries", t("nav_industries", lang), "industries"),
                link("/pricing", t("nav_pricing", lang), "pricing"),
                cls="hidden lg:flex items-center gap-6",
            ),
            Div(
                _lang_dropdown(lang),
                A(t("nav_sign_in", lang),
                  href="/signin",
                  cls="hidden sm:inline-flex text-sm px-3 py-1.5 rounded-md font-medium cursor-pointer no-underline ml-3",
                  style=f"background:{BG_ELEV}; color:{INK}; border:1px solid {LINE};"),
                hamburger,
                cls="flex items-center gap-2",
            ),
            cls="max-w-6xl mx-auto flex items-center justify-between px-4 sm:px-6 py-4",
        ),
        mobile_menu,
        cls="border-b sticky top-0 z-40 backdrop-blur",
        style=f"border-color:{LINE}; background: rgba(11,18,32,0.85);",
    )


def landing_footer():
    return Div(
        Div(
            Div(
                Span("LiquidRound", cls="text-sm font-semibold tighter"),
                Span("© 2026 Predictive Labs Ltd.", cls="ml-3 text-xs text-slate-500"),
                cls="flex items-center",
            ),
            Div(
                A("Contact", href="/contact", cls="text-xs text-slate-400 nav-link"),
                Span("·", cls="text-xs text-slate-600 mx-2"),
                A("Platform", href="/platform", cls="text-xs text-slate-400 nav-link"),
                Span("·", cls="text-xs text-slate-600 mx-2"),
                A("Tools", href="/tools/comparables", cls="text-xs text-slate-400 nav-link"),
                Span("·", cls="text-xs text-slate-600 mx-2"),
                A("Industries", href="/industries", cls="text-xs text-slate-400 nav-link"),
                Span("·", cls="text-xs text-slate-600 mx-2"),
                A("ECM Squad", href="/agents", cls="text-xs text-slate-400 nav-link"),
                cls="flex items-center flex-wrap gap-y-1 justify-center sm:justify-end",
            ),
            cls="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3",
        ),
        cls="border-t mt-20",
        style=f"border-color:{LINE};",
    )


# ───── Home-page sections ───────────────────────────────────────────────

def hero():
    """Main hero with two role CTAs + product GIF below."""
    return Div(
        Div(
            # Eyebrow
            Div(
                Span("◈", cls="mono mr-2", style=f"color:{CTA}"),
                Span("AI Investment Banking · Both sides of every deal",
                     cls="text-xs mono uppercase tracking-widest", style=f"color:{INK_MUTED}"),
                cls="flex items-center justify-center mb-6 md:mb-8",
            ),
            # Headline
            H1(
                Span("Your AI "),
                Span("ECM / IB ", style=f"color:{CTA};"),
                Span("analyst squad "),
                Span("for M&A ", style=f"color:{BUY}"),
                Span("and "),
                Span("IPO.", style=f"color:{SELL}"),
                cls="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold tightest text-center mb-4 md:mb-6",
                style=f"color:{INK};",
            ),
            # Sub — explicitly spells out ECM, mentions BYOD, memo/pitch drafting
            P(
                Span("ECM = ", cls="mono", style=f"color:{CTA};"),
                Span("Equity Capital Markets", cls="mono", style=f"color:{INK};"),
                Span(". A squad of specialist AI analysts — ",
                     style=f"color:{INK_MUTED};"),
                Span("buyer-led ", style=f"color:{BUY};"),
                Span("sourcing and diligence, ", style=f"color:{INK_MUTED};"),
                Span("seller-led ", style=f"color:{SELL};"),
                Span("positioning and IPO readiness. ", style=f"color:{INK_MUTED};"),
                Span("Real-time market data, ", style=f"color:{INK};"),
                Span("investment-memo and pitch-deck drafting, and ",
                     style=f"color:{INK_MUTED};"),
                Span("BYOD ", style=f"color:{CTA};"),
                Span("— bring your own pitch books, CIMs and term sheets.",
                     style=f"color:{INK_MUTED};"),
                cls="text-base md:text-lg lg:text-xl text-center max-w-3xl mx-auto mb-8 md:mb-10 leading-relaxed px-2",
            ),
            # Two CTAs
            Div(
                A(
                    Span("Buyer-Led", cls="text-base font-semibold"),
                    Span(" →", cls="ml-2 text-base"),
                    href="/signin?role=buyer",
                    cls="cta-glow-buy rounded-lg px-6 py-3 inline-flex items-center text-white no-underline tracking-tight cursor-pointer",
                    style=f"background:{BUY};",
                ),
                A(
                    Span("Seller-Led", cls="text-base font-semibold"),
                    Span(" →", cls="ml-2 text-base"),
                    href="/signin?role=seller",
                    cls="cta-glow-sell rounded-lg px-6 py-3 inline-flex items-center text-white no-underline tracking-tight cursor-pointer",
                    style=f"background:{SELL};",
                ),
                cls="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-4",
            ),
            # Sub-CTA text
            P(
                "Same app, different default view. Switch anytime in ",
                A("Configuration", href="/signin", style=f"color:{CTA}"),
                ".",
                cls="text-center text-xs mb-16",
                style=f"color:{INK_MUTED};",
            ),
            # Product demo GIF
            Div(
                Div(
                    Img(src="/liquidround.gif", alt="LiquidRound product demo",
                        cls="w-full rounded-lg",
                        style=f"border:1px solid {LINE}; background:{BG_ELEV};"),
                    P(
                        Span("● ", style=f"color:{CTA}"),
                        Span("Product tour — ", cls="text-xs mono uppercase tracking-widest"),
                        Span("profile, triage, valuation, IC memo", cls="text-xs", style=f"color:{INK_MUTED};"),
                        cls="text-center mt-3 mono", style=f"color:{INK};",
                    ),
                    cls="max-w-4xl mx-auto",
                ),
                cls="px-6",
            ),
            cls="max-w-4xl mx-auto px-4 sm:px-6 pt-12 md:pt-20 pb-10 md:pb-12 text-center",
        ),
        cls="hero-gradient",
    )


def stats_bar():
    items = [
        ("AI Squad", "specialist analysts"),
        ("2", "sides of every deal"),
        ("M&A + IPO", "buyer and seller"),
        ("BYOD", "bring your own pitch books"),
    ]
    return Div(
        Div(
            *[Div(
                Div(val, cls="text-2xl font-bold tightest", style=f"color:{INK};"),
                Div(label, cls="text-xs mono uppercase tracking-widest mt-1", style=f"color:{INK_MUTED};"),
                cls="text-center",
            ) for val, label in items],
            cls="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8 max-w-4xl mx-auto px-4 sm:px-6 py-10 md:py-12",
        ),
        cls="border-y", style=f"border-color:{LINE};",
    )


def category_pillar(icon: str, title: str, blurb: str, audience_note: str = ""):
    """A single category pillar card on the home / platform page."""
    return Div(
        Span(icon, cls="text-3xl mono", style=f"color:{CTA};"),
        H3(title, cls="text-base font-semibold mt-3 tighter", style=f"color:{INK};"),
        P(blurb, cls="text-sm mt-2 leading-relaxed", style=f"color:{INK_MUTED};"),
        P(audience_note, cls="text-xs mono uppercase tracking-widest mt-3", style=f"color:{CTA};") if audience_note else "",
        cls="card rounded-lg p-5 transition",
    )


def pillars_section():
    from agents.registry import CATEGORIES
    # audience emphasis per category
    emph = {
        "sourcing": "buyer + seller",
        "underwriting": "buyer + seller",
        "diligence": "mostly buyer",
        "capital": "buyer memos · seller CIMs",
        "portfolio": "buyer integration · shared research",
    }
    return Div(
        Div(
            H2("One system. Every stage. Both sides.",
               cls="text-3xl md:text-4xl font-bold tightest text-center mb-4",
               style=f"color:{INK};"),
            P("Your AI ECM / IB analyst squad spans 5 workflow categories.",
              cls="text-center mb-12", style=f"color:{INK_MUTED};"),
            Div(
                *[category_pillar(c["icon"], c["name"], c["blurb"], emph.get(c["key"], ""))
                  for c in CATEGORIES],
                cls="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4",
            ),
            cls="max-w-6xl mx-auto px-4 sm:px-6 py-14 md:py-20",
        ),
    )


def agent_card(spec, href_base: str = "/agents"):
    audience_color = {"buyer": BUY, "seller": SELL, "shared": CTA}[spec.audience]
    audience_label = {"buyer": "buyer", "seller": "seller", "shared": "shared"}[spec.audience]
    return A(
        Div(
            Div(
                Span(spec.icon, cls="text-xl mono", style=f"color:{CTA};"),
                Span(spec.prefix, cls="text-xs mono ml-auto px-1.5 py-0.5 rounded",
                     style=f"color:{INK_MUTED}; background:rgba(255,255,255,0.03); border:1px solid {LINE};"),
                cls="flex items-center mb-3",
            ),
            H3(spec.name, cls="text-sm font-semibold tighter", style=f"color:{INK};"),
            P(spec.one_liner, cls="text-xs mt-1.5 leading-relaxed", style=f"color:{INK_MUTED};"),
            Div(
                Span(audience_label, cls="text-[10px] mono uppercase tracking-widest"),
                cls="mt-3 inline-block px-2 py-0.5 rounded",
                style=f"color:{audience_color}; border:1px solid {audience_color};",
            ),
            cls="card rounded-lg p-4 h-full agent-card",
        ),
        href=f"{href_base}/{spec.slug}",
        cls="no-underline block",
    )


def agent_grid_section():
    from agents.registry import CATEGORIES, AGENTS_BY_CATEGORY
    sections = []
    for cat in CATEGORIES:
        agents_in_cat = AGENTS_BY_CATEGORY.get(cat["key"], [])
        sections.append(Div(
            Div(
                Span(cat["icon"], cls="text-2xl mono mr-3", style=f"color:{CTA};"),
                Div(
                    H3(cat["name"], cls="text-lg font-semibold tighter", style=f"color:{INK};"),
                    P(cat["blurb"], cls="text-xs", style=f"color:{INK_MUTED};"),
                ),
                cls="flex items-center mb-4",
            ),
            Div(
                *[agent_card(a) for a in agents_in_cat],
                cls="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3",
            ),
            cls="mb-12",
        ))
    return Div(
        Div(
            H2("Every role already defined.",
               cls="text-3xl md:text-4xl font-bold tightest text-center mb-4",
               style=f"color:{INK};"),
            P("A squad of AI ECM / IB analysts — each with a defined role and a one-word prefix. Talk to them directly or let the router pick.",
              cls="text-center mb-12", style=f"color:{INK_MUTED};"),
            *sections,
            cls="max-w-6xl mx-auto px-4 sm:px-6 py-14 md:py-20",
        ),
    )


def how_it_works_section():
    steps = [
        ("1. Choose your side", "Buyer-Led if you're acquiring. Seller-Led if you're exiting. The app adapts its default view; you can switch anytime.", BUY),
        ("2. Ask a question, paste a prefix, or upload a doc", "The router sends your message to the right analyst — profile:, triage:, memo:, ipo: — across your ECM / IB squad. Upload a pitch book or CIM (BYOD) and the analysts read, cite and draft from it.", CTA),
        ("3. Preview the memo", "Research results, valuation comps and scoring matrices all land in the right pane. Click Preview PDF on any memo to render a polished document instantly.", SELL),
    ]
    return Div(
        Div(
            H2("From question to IC memo in hours, not weeks.",
               cls="text-3xl md:text-4xl font-bold tightest text-center mb-12",
               style=f"color:{INK};"),
            Div(
                *[Div(
                    Div(label.split(".")[0] + ".",
                        cls="text-4xl font-bold tightest mb-3",
                        style=f"color:{color};"),
                    H3(label.split(". ", 1)[1],
                       cls="text-lg font-semibold tighter mb-2",
                       style=f"color:{INK};"),
                    P(body, cls="text-sm leading-relaxed",
                      style=f"color:{INK_MUTED};"),
                    cls="card rounded-lg p-6",
                ) for label, body, color in steps],
                cls="grid grid-cols-1 md:grid-cols-3 gap-4",
            ),
            cls="max-w-6xl mx-auto px-4 sm:px-6 py-14 md:py-20",
        ),
    )


def cta_section():
    return Div(
        Div(
            H2("Both sides of the deal. One platform.",
               cls="text-3xl md:text-4xl font-bold tightest text-center mb-4",
               style=f"color:{INK};"),
            P("Sign in. Pick your role. Get to work.",
              cls="text-center mb-10", style=f"color:{INK_MUTED};"),
            Div(
                A("Buyer-Led →",
                  href="/signin?role=buyer",
                  cls="cta-glow-buy rounded-lg px-6 py-3 text-base font-semibold text-white no-underline cursor-pointer",
                  style=f"background:{BUY};"),
                A("Seller-Led →",
                  href="/signin?role=seller",
                  cls="cta-glow-sell rounded-lg px-6 py-3 text-base font-semibold text-white no-underline cursor-pointer",
                  style=f"background:{SELL};"),
                cls="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4",
            ),
            cls="max-w-4xl mx-auto px-4 sm:px-6 py-14 md:py-20 text-center",
        ),
    )




# ───── Page shells ──────────────────────────────────────────────────────

def landing_page(*sections, active: str = "home", title: str = "LiquidRound", lang: str = "en"):
    """Wrap sections with head + nav + footer."""
    return (
        *landing_head(title),
        landing_nav(active=active, lang=lang),
        Main(*sections),
        landing_footer(),
    )
