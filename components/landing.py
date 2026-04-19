"""Landing-page FastHTML components.

Dark navy hero, two role CTAs, agent directory, platform/how-it-works pages.
Colors intentionally distinct from sibling PEHero project (parchment + forest).
"""
from __future__ import annotations

from fasthtml.common import *

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

def landing_head(title: str = "LiquidRound"):
    """<head> contents for all landing pages."""
    return (
        Title(title),
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Meta(name="theme-color", content=BG),
        Script(src="https://cdn.tailwindcss.com"),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        Link(href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap", rel="stylesheet"),
        Style(f"""
            html, body {{ background: {BG}; color: {INK}; font-family: 'Inter', system-ui, sans-serif; letter-spacing: -0.01em; }}
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


def landing_nav(active: str = "home"):
    """Top nav bar — common to all landing pages."""
    def link(href: str, label: str, key: str):
        is_active = key == active
        cls = "text-sm nav-link " + ("text-white font-medium" if is_active else "text-slate-400")
        return A(label, href=href, cls=cls)
    return Div(
        Div(
            A(
                Div(
                    Span("◈", cls="text-xl mr-2", style=f"color:{CTA}"),
                    Span("LiquidRound", cls="text-base font-semibold tighter"),
                    Span("beta", cls="ml-2 text-[10px] px-1.5 py-0.5 rounded mono", style=f"color:{CTA}; border:1px solid {CTA}; background:transparent;"),
                    cls="flex items-center",
                ),
                href="/", cls="text-white no-underline",
            ),
            Div(
                link("/platform", "Platform", "platform"),
                link("/agents", "ECM Squad", "agents"),
                link("/how-it-works", "How it works", "how"),
                link("/pricing", "Pricing", "pricing"),
                A("Open the app",
                  href="/app",
                  cls="ml-2 text-sm px-3 py-1.5 rounded-md font-medium",
                  style=f"background:{BG_ELEV}; color:{INK}; border:1px solid {LINE};"),
                cls="flex items-center gap-6",
            ),
            cls="max-w-6xl mx-auto flex items-center justify-between px-6 py-4",
        ),
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
                A("ECM Squad", href="/agents", cls="text-xs text-slate-400 nav-link"),
                cls="flex items-center",
            ),
            cls="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between",
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
                Span("Your ECM Agent Squad · Both sides of every deal",
                     cls="text-xs mono uppercase tracking-widest", style=f"color:{INK_MUTED}"),
                cls="flex items-center justify-center mb-8",
            ),
            # Headline
            H1(
                Span("Your ECM Agent Squad "),
                Span("for M&A ", style=f"color:{BUY}"),
                Span("and "),
                Span("IPO.", style=f"color:{SELL}"),
                cls="text-5xl md:text-6xl font-bold tightest text-center mb-6",
                style=f"color:{INK};",
            ),
            # Sub — explicitly spells out ECM
            P(
                Span("ECM = ", cls="mono", style=f"color:{CTA};"),
                Span("Equity Capital Markets", cls="mono", style=f"color:{INK};"),
                Span(". Twenty-two specialist AI agents working both sides of every deal — ",
                     style=f"color:{INK_MUTED};"),
                Span("buyer-led ", style=f"color:{BUY};"),
                Span("sourcing and diligence, ", style=f"color:{INK_MUTED};"),
                Span("seller-led ", style=f"color:{SELL};"),
                Span("positioning and IPO readiness.", style=f"color:{INK_MUTED};"),
                cls="text-lg md:text-xl text-center max-w-3xl mx-auto mb-10 leading-relaxed",
            ),
            # Two CTAs
            Div(
                A(
                    Span("Buyer-Led", cls="text-base font-semibold"),
                    Span(" →", cls="ml-2 text-base"),
                    href="/app?role=buyer",
                    cls="cta-glow-buy rounded-lg px-6 py-3 inline-flex items-center text-white no-underline tracking-tight",
                    style=f"background:{BUY};",
                ),
                A(
                    Span("Seller-Led", cls="text-base font-semibold"),
                    Span(" →", cls="ml-2 text-base"),
                    href="/app?role=seller",
                    cls="cta-glow-sell rounded-lg px-6 py-3 inline-flex items-center text-white no-underline tracking-tight",
                    style=f"background:{SELL};",
                ),
                cls="flex items-center justify-center gap-4 mb-4",
            ),
            # Sub-CTA text
            P(
                "Same app, different default view. Switch anytime in ",
                A("Configuration", href="/app?role=buyer#settings", style=f"color:{CTA}"),
                ".",
                cls="text-center text-xs mb-16",
                style=f"color:{INK_MUTED};",
            ),
            # Product demo GIF
            Div(
                Div(
                    Img(src="/static/liquidround.gif", alt="LiquidRound product demo",
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
            cls="max-w-4xl mx-auto px-6 pt-20 pb-12 text-center",
        ),
        cls="hero-gradient",
    )


def stats_bar():
    items = [
        ("22", "in the ECM squad"),
        ("2", "sides of every deal"),
        ("M&A + IPO", "both workflows"),
        ("Real-time", "yfinance + EXA + Tavily"),
    ]
    return Div(
        Div(
            *[Div(
                Div(val, cls="text-2xl font-bold tightest", style=f"color:{INK};"),
                Div(label, cls="text-xs mono uppercase tracking-widest mt-1", style=f"color:{INK_MUTED};"),
                cls="text-center",
            ) for val, label in items],
            cls="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto px-6 py-12",
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
            P("Your ECM Agent Squad spans 5 workflow categories.",
              cls="text-center mb-12", style=f"color:{INK_MUTED};"),
            Div(
                *[category_pillar(c["icon"], c["name"], c["blurb"], emph.get(c["key"], ""))
                  for c in CATEGORIES],
                cls="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4",
            ),
            cls="max-w-6xl mx-auto px-6 py-20",
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
                cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3",
            ),
            cls="mb-12",
        ))
    return Div(
        Div(
            H2("Every role already defined.",
               cls="text-3xl md:text-4xl font-bold tightest text-center mb-4",
               style=f"color:{INK};"),
            P("The full ECM Agent Squad — prompts and prefixes pre-wired. Talk to them directly or let the router pick.",
              cls="text-center mb-12", style=f"color:{INK_MUTED};"),
            *sections,
            cls="max-w-6xl mx-auto px-6 py-20",
        ),
    )


def how_it_works_section():
    steps = [
        ("1. Choose your side", "Buyer-Led if you're acquiring. Seller-Led if you're exiting. The app adapts its default view; you can switch anytime.", BUY),
        ("2. Ask a question, paste a prefix, or upload a doc", "The router sends your message to the right specialist — profile:, triage:, memo:, ipo: — across your ECM squad. Or upload a PDF and we'll extract key terms.", CTA),
        ("3. Iterate in the canvas", "Research results, valuation comps, scoring matrices and documents all land in the right-pane canvas, ready to compose into a memo or CIM.", SELL),
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
            cls="max-w-6xl mx-auto px-6 py-20",
        ),
    )


def cta_section():
    return Div(
        Div(
            H2("Both sides of the deal. One platform.",
               cls="text-3xl md:text-4xl font-bold tightest text-center mb-4",
               style=f"color:{INK};"),
            P("Open the app. Pick your role. Get to work.",
              cls="text-center mb-10", style=f"color:{INK_MUTED};"),
            Div(
                A("Buyer-Led →",
                  href="/app?role=buyer",
                  cls="cta-glow-buy rounded-lg px-6 py-3 text-base font-semibold text-white no-underline",
                  style=f"background:{BUY};"),
                A("Seller-Led →",
                  href="/app?role=seller",
                  cls="cta-glow-sell rounded-lg px-6 py-3 text-base font-semibold text-white no-underline",
                  style=f"background:{SELL};"),
                cls="flex items-center justify-center gap-4",
            ),
            cls="max-w-4xl mx-auto px-6 py-20 text-center",
        ),
    )


# ───── Page shells ──────────────────────────────────────────────────────

def landing_page(*sections, active: str = "home", title: str = "LiquidRound"):
    """Wrap sections with head + nav + footer."""
    return (
        *landing_head(title),
        landing_nav(active=active),
        Main(*sections),
        landing_footer(),
    )
