"""Landing-page routes — `/`, `/platform`, `/agents`, `/agents/<slug>`,
`/how-it-works`, `/pricing`, `/contact`.

Mounted BEFORE main.py's routes, so `/` here intercepts before the chat app.
The chat app is reachable at `/app` (see main.py `@rt("/app")`).
"""
from __future__ import annotations

from fasthtml.common import *
from fasthtml.core import APIRouter

from agents.registry import AGENTS, AGENTS_BY_SLUG, AGENTS_BY_CATEGORY, CATEGORIES, by_slug
from components.landing import (
    BG, BG_ELEV, INK, INK_MUTED, BUY, SELL, CTA, LINE,
    landing_page, hero, stats_bar, pillars_section,
    agent_grid_section, how_it_works_section, cta_section,
    landing_head, landing_nav, landing_footer, agent_card,
)

ar = APIRouter()


@ar("/")
def landing_home():
    return landing_page(
        hero(),
        stats_bar(),
        pillars_section(),
        how_it_works_section(),
        cta_section(),
        active="home",
        title="LiquidRound — Your ECM Agent Squad for M&A and IPO",
    )


@ar("/platform")
def landing_platform():
    return landing_page(
        Div(
            Div(
                H1("The platform.",
                   cls="text-4xl md:text-5xl font-bold tightest text-center mb-4",
                   style=f"color:{INK};"),
                P("Your AI ECM / IB analyst squad — 22 specialists across 5 workflow categories (sourcing, underwriting, diligence, capital, portfolio). ECM stands for Equity Capital Markets. Same app for buyers and sellers.",
                  cls="text-lg text-center max-w-2xl mx-auto mb-12",
                  style=f"color:{INK_MUTED};"),
                cls="max-w-4xl mx-auto px-6 pt-20 pb-8 text-center",
            ),
        ),
        pillars_section(),
        Div(
            Div(
                H2("What you get.",
                   cls="text-2xl font-bold tightest text-center mb-3",
                   style=f"color:{INK};"),
                P("An AI junior-analyst team that does the grind — you keep the judgement.",
                  cls="text-sm text-center mb-10", style=f"color:{INK_MUTED};"),
                Div(
                    *[Div(
                        Span(name, cls="text-sm font-semibold", style=f"color:{INK};"),
                        P(blurb, cls="text-xs mt-1 leading-relaxed", style=f"color:{INK_MUTED};"),
                        cls="card rounded-lg p-4",
                    ) for name, blurb in [
                        ("Real-time market data",
                         "Company profiles, financials, multiples, precedents — refreshed on demand."),
                        ("Real-time deep research",
                         "Semantic and web search across filings, news and industry reports with citations."),
                        ("Investment memo drafting",
                         "IC-ready memos and LP updates in your firm's voice — ready to preview as PDF."),
                        ("Pitch deck & CIM drafting",
                         "Blind teasers and confidential info memoranda from a single brief."),
                        ("BYOD — bring your own data",
                         "Upload pitch books, term sheets, data-room files; agents read and cite them."),
                        ("One workspace, both sides",
                         "Switch between Buyer-Led and Seller-Led in one click. Pipelines, docs, scores — all in view."),
                    ]],
                    cls="grid grid-cols-1 md:grid-cols-3 gap-4",
                ),
                cls="max-w-6xl mx-auto px-6 py-20",
            ),
        ),
        cta_section(),
        active="platform",
        title="Platform — LiquidRound",
    )


@ar("/agents")
def landing_agents():
    return landing_page(
        Div(
            Div(
                Span("◈", cls="mono mr-2", style=f"color:{CTA}"),
                Span("ECM Agent Squad · 5 categories · both sides of the deal",
                     cls="text-xs mono uppercase tracking-widest", style=f"color:{INK_MUTED}"),
                cls="flex items-center justify-center mb-6 pt-20",
            ),
            H1("The ECM Agent Squad.",
               cls="text-4xl md:text-5xl font-bold tightest text-center mb-4",
               style=f"color:{INK};"),
            P(
                "22 AI ECM / IB analysts — M&A and IPO, buyer and seller. Click any card for details and example prompts.",
                cls="text-center mb-4 max-w-2xl mx-auto", style=f"color:{INK_MUTED};",
            ),
            cls="max-w-4xl mx-auto px-6",
        ),
        agent_grid_section(),
        cta_section(),
        active="agents",
        title="ECM Agent Squad — LiquidRound",
    )


@ar("/agents/{slug}")
def landing_agent_detail(slug: str):
    spec = by_slug(slug)
    if spec is None:
        return landing_page(
            Div(
                H1("Agent not found", cls="text-3xl font-bold text-center py-20", style=f"color:{INK};"),
                A("← back to the ECM Agent Squad", href="/agents",
                  cls="block text-center", style=f"color:{CTA}"),
            ),
            title="Not found — LiquidRound",
        )
    # Find category metadata
    cat_meta = next((c for c in CATEGORIES if c["key"] == spec.category), None)
    cat_name = cat_meta["name"] if cat_meta else spec.category
    audience_color = {"buyer": BUY, "seller": SELL, "shared": CTA}[spec.audience]
    audience_label = spec.audience.upper()

    # Other agents in same category for sidebar
    siblings = [a for a in AGENTS_BY_CATEGORY.get(spec.category, []) if a.slug != spec.slug]

    return landing_page(
        Div(
            Div(
                # Breadcrumb
                Div(
                    A("← All agents", href="/agents", cls="text-xs", style=f"color:{INK_MUTED};"),
                    Span(" / ", cls="text-xs mx-2", style=f"color:{LINE};"),
                    Span(cat_name, cls="text-xs", style=f"color:{INK_MUTED};"),
                    cls="pt-16 pb-4",
                ),
                # Header
                Div(
                    Span(spec.icon, cls="text-4xl mono mr-4", style=f"color:{CTA};"),
                    Div(
                        H1(spec.name, cls="text-3xl font-bold tightest", style=f"color:{INK};"),
                        Div(
                            Span(spec.prefix, cls="mono text-xs mr-3 px-2 py-0.5 rounded",
                                 style=f"color:{INK_MUTED}; background:rgba(255,255,255,0.05); border:1px solid {LINE};"),
                            Span(audience_label, cls="mono text-xs px-2 py-0.5 rounded",
                                 style=f"color:{audience_color}; border:1px solid {audience_color};"),
                        ),
                    ),
                    cls="flex items-center mb-6",
                ),
                P(spec.one_liner, cls="text-lg tighter mb-6", style=f"color:{INK};"),
                P(spec.description, cls="text-sm leading-relaxed mb-8", style=f"color:{INK_MUTED};"),

                # Example prompts
                H2("Example prompts", cls="text-sm mono uppercase tracking-widest mb-3", style=f"color:{CTA};"),
                Ul(
                    *[Li(
                        Span(p, cls="text-sm mono"),
                        cls="card rounded-lg p-3 mb-2",
                        style=f"color:{INK};",
                    ) for p in spec.example_prompts],
                    cls="list-none pl-0 mb-10",
                ),

                # CTA
                Div(
                    A(f"Try {spec.name} →",
                      href=f"/app?role={'buyer' if spec.audience=='buyer' else 'seller' if spec.audience=='seller' else 'buyer'}&agent={spec.slug}",
                      cls="rounded-lg px-5 py-2.5 text-sm font-semibold text-white no-underline",
                      style=f"background:{BUY};"),
                    cls="mb-16",
                ),

                # Related agents
                H2("Others in " + cat_name,
                   cls="text-sm mono uppercase tracking-widest mb-3",
                   style=f"color:{CTA};"),
                Div(
                    *[agent_card(a) for a in siblings],
                    cls="grid grid-cols-1 md:grid-cols-2 gap-3 mb-20",
                ),
                cls="max-w-3xl mx-auto px-6",
            ),
        ),
        active="agents",
        title=f"{spec.name} — LiquidRound",
    )


@ar("/how-it-works")
def landing_how():
    return landing_page(
        Div(
            H1("How it works.",
               cls="text-4xl md:text-5xl font-bold tightest text-center pt-20 mb-4",
               style=f"color:{INK};"),
            P("Three steps from landing page to IC memo.",
              cls="text-center mb-12", style=f"color:{INK_MUTED};"),
        ),
        how_it_works_section(),
        cta_section(),
        active="how",
        title="How it works — LiquidRound",
    )


@ar("/pricing")
def landing_pricing():
    tiers = [
        ("Starter", "Free", "For solo advisors exploring LiquidRound.",
         ["Full ECM Agent Squad (22 analysts)", "Real-time market data & research", "Up to 20 queries / day", "Community support"], False),
        ("Team", "From $499 / month", "For boutique M&A and IB teams.",
         ["Everything in Starter", "Unlimited queries", "BYOD: pitch books, CIMs, term sheets", "Memo + pitch-deck drafting", "Team pipelines", "Priority support"], True),
        ("Enterprise", "Contact us", "For institutional platforms.",
         ["Everything in Team", "SSO + audit logs", "Custom agents & prompts", "Dedicated infra", "SLA"], False),
    ]
    return landing_page(
        Div(
            H1("Start with synthetic data. Scale on real deals.",
               cls="text-4xl md:text-5xl font-bold tightest text-center pt-20 mb-4",
               style=f"color:{INK};"),
            P("No procurement. No waiting on vendor review.",
              cls="text-center mb-16", style=f"color:{INK_MUTED};"),
            Div(
                *[Div(
                    (Div(Span("MOST POPULAR", cls="mono text-[10px] tracking-widest px-2 py-0.5 rounded"),
                         style=f"color:{BG}; background:{CTA};", cls="inline-block mb-3") if highlight else ""),
                    H3(name, cls="text-lg font-semibold tighter", style=f"color:{INK};"),
                    Div(price, cls="text-3xl font-bold tightest my-3", style=f"color:{INK};"),
                    P(desc, cls="text-sm mb-5", style=f"color:{INK_MUTED};"),
                    Ul(*[Li(f"✓ {item}", cls="text-sm py-1", style=f"color:{INK};") for item in items],
                       cls="list-none pl-0 mb-6"),
                    A("Get started →", href="/app?role=buyer",
                      cls="block text-center rounded-lg px-4 py-2 text-sm font-semibold text-white no-underline",
                      style=f"background:{CTA if highlight else LINE};"),
                    cls="card rounded-lg p-6" + (" ring-2" if highlight else ""),
                    style=(f"border-color:{CTA}" if highlight else ""),
                ) for name, price, desc, items, highlight in tiers],
                cls="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-5xl mx-auto px-6 pb-20",
            ),
        ),
        active="pricing",
        title="Pricing — LiquidRound",
    )


@ar("/contact")
def landing_contact():
    return landing_page(
        Div(
            H1("Talk to us.",
               cls="text-4xl md:text-5xl font-bold tightest text-center pt-20 mb-4",
               style=f"color:{INK};"),
            P("Predictive Labs Ltd — ",
              A("hello@predictivelabs.ai", href="mailto:hello@predictivelabs.ai",
                style=f"color:{CTA};"),
              cls="text-center mb-16", style=f"color:{INK_MUTED};"),
            Div(
                P("LiquidRound is built by Predictive Labs Ltd, a small team shipping AI for M&A and private markets.",
                  cls="text-sm mb-4", style=f"color:{INK_MUTED};"),
                P("For sales, partnerships, or engineering roles — drop a line.",
                  cls="text-sm", style=f"color:{INK_MUTED};"),
                cls="max-w-xl mx-auto px-6 pb-20 text-center card rounded-lg p-8 mt-8",
            ),
        ),
        active="contact",
        title="Contact — LiquidRound",
    )
