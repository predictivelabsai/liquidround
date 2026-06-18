"""Lead-magnet tool UI components — Comparables, Buyer Match, Valuation.

Uses the landing palette. Renders multi-step wizard forms with HTMX.
"""
from __future__ import annotations

from fasthtml.common import *
from components.landing import (
    BG, BG_ELEV, INK, INK_MUTED, CTA, LINE, BUY, SELL,
    landing_head, landing_nav, landing_footer,
)

# ───── Shared layouts ──────────────────────────────────────────────────

def tool_page(*sections, title: str = "Tool", active: str = "tools", lang: str = "en"):
    """Full-page shell for public /tools/* pages."""
    return (
        *landing_head(f"{title} — LiquidRound"),
        Script("""
            function toggleFaq(el) {
                const content = el.nextElementSibling;
                const arrow = el.querySelector('.faq-arrow');
                content.classList.toggle('hidden');
                arrow.textContent = content.classList.contains('hidden') ? '+' : '−';
            }
        """),
        landing_nav(active=active, lang=lang),
        Main(*sections),
        landing_footer(),
    )


def tool_hero(heading: str, subtext: str):
    return Div(
        Div(
            Span("◈ Free Tool", cls="mono text-xs tracking-widest mb-4 block", style=f"color:{CTA}"),
            H1(heading, cls="text-3xl sm:text-4xl md:text-5xl font-bold tightest mb-4", style=f"color:{INK}"),
            P(subtext, cls="text-base max-w-2xl mx-auto", style=f"color:{INK_MUTED}"),
            cls="text-center",
        ),
        cls="max-w-4xl mx-auto px-6 pt-16 pb-8",
    )


# ───── Step 1: URL input ──────────────────────────────────────────────

def url_input_step(tool_name: str, action_url: str):
    """Step 1 form: Enter company URL."""
    return Div(
        Form(
            Div(
                Label("Enter your company website", cls="text-sm font-medium mb-2 block", style=f"color:{INK}"),
                Div(
                    Input(
                        name="url",
                        type="text",
                        placeholder="e.g. https://meliva.ee",
                        required=True,
                        cls="flex-1 rounded-lg px-4 py-3 text-sm",
                        style=f"background:{BG}; color:{INK}; border:1px solid {LINE}; outline:none;",
                    ),
                    Button(
                        "Next →",
                        type="submit",
                        cls="rounded-lg px-6 py-3 text-sm font-semibold text-white cursor-pointer",
                        style=f"background:{CTA};",
                    ),
                    cls="flex gap-3",
                ),
                P("No email or sign-up necessary. 100% confidential.",
                  cls="text-xs mt-3", style=f"color:{INK_MUTED}"),
                cls="max-w-xl mx-auto",
            ),
            hx_post=action_url,
            hx_target="#tool-content",
            hx_swap="innerHTML",
            hx_indicator="#loading-indicator",
        ),
        Div(id="loading-indicator", cls="htmx-indicator mt-6 text-center",
            style=f"color:{CTA}"),
        cls="card rounded-lg p-8 max-w-2xl mx-auto",
    )


def loading_animation():
    """Animated progress shown during scraping + analysis."""
    return Div(
        Div(
            Div(cls="animate-spin rounded-full h-8 w-8 border-2 border-t-transparent mx-auto mb-4",
                style=f"border-color:{CTA}; border-top-color:transparent;"),
            Div("Analyzing company website...",
                id="loading-status",
                cls="text-sm font-medium mb-2", style=f"color:{INK}"),
            Div(cls="w-full rounded-full h-1.5 overflow-hidden", style=f"background:{LINE}",
                children=[
                    Div(cls="h-full rounded-full animate-pulse", style=f"background:{CTA}; width:60%")
                ]),
            cls="text-center py-8",
        ),
        cls="card rounded-lg p-8 max-w-2xl mx-auto",
    )


# ───── Company profile card ──────────────────────────────────────────

def company_profile_card(profile: dict):
    """Right-panel company info card after scraping."""
    tags = profile.get("products", [])[:6]
    markets = profile.get("end_markets", [])[:4]
    return Div(
        Div(
            H3(profile.get("name", "Company"), cls="text-lg font-semibold tighter", style=f"color:{INK}"),
            P(profile.get("description", ""), cls="text-sm mt-2 leading-relaxed", style=f"color:{INK_MUTED}"),
            cls="mb-4",
        ),
        Div(
            Span("Sector: ", cls="text-xs font-medium", style=f"color:{INK_MUTED}"),
            Span(profile.get("sector", "—"), cls="text-xs font-semibold", style=f"color:{CTA}"),
            cls="mb-2",
        ) if profile.get("sector") else "",
        Div(
            Span("Sub-sector: ", cls="text-xs font-medium", style=f"color:{INK_MUTED}"),
            Span(profile.get("sub_sector", "—"), cls="text-xs", style=f"color:{INK}"),
            cls="mb-3",
        ) if profile.get("sub_sector") else "",
        Div(
            Span("Products & Services", cls="text-xs font-medium mb-1 block", style=f"color:{INK_MUTED}"),
            Div(
                *[Span(t, cls="text-xs px-2 py-0.5 rounded-full mr-1 mb-1 inline-block",
                        style=f"background:{BG}; color:{INK}; border:1px solid {LINE}") for t in tags],
            ),
            cls="mb-3",
        ) if tags else "",
        Div(
            Span("End Markets", cls="text-xs font-medium mb-1 block", style=f"color:{INK_MUTED}"),
            Div(
                *[Span(m, cls="text-xs px-2 py-0.5 rounded-full mr-1 mb-1 inline-block",
                        style=f"background:{BG}; color:{INK}; border:1px solid {LINE}") for m in markets],
            ),
        ) if markets else "",
        cls="card rounded-lg p-5",
    )


# ───── Financial inputs (Step 2) ──────────────────────────────────────

def _eur_input(name: str, label: str, placeholder: str = "0"):
    return Div(
        Label(label, cls="text-xs font-medium mb-1 block", style=f"color:{INK_MUTED}"),
        Div(
            Span("€", cls="text-sm font-medium px-3 flex items-center",
                 style=f"color:{INK_MUTED}; background:{BG}; border:1px solid {LINE}; border-right:none; border-radius:0.5rem 0 0 0.5rem;"),
            Input(name=name, type="number", step="1000", placeholder=placeholder,
                  cls="flex-1 px-3 py-2.5 text-sm",
                  style=f"background:{BG}; color:{INK}; border:1px solid {LINE}; border-left:none; border-radius:0 0.5rem 0.5rem 0; outline:none;"),
            cls="flex",
        ),
    )


def comps_financial_form(profile: dict, action_url: str):
    """Step 2 for Comparables: revenue, pre-tax profit, owner salary."""
    return Div(
        Div(
            company_profile_card(profile),
            cls="mb-6",
        ),
        Form(
            Input(type="hidden", name="url", value=profile.get("url", "")),
            Input(type="hidden", name="company_data", value=__import__("json").dumps(profile)),
            H3("Financial Information", cls="text-base font-semibold mb-4", style=f"color:{INK}"),
            Div(
                _eur_input("revenue", "Annual Revenue (EUR)", "1,000,000"),
                _eur_input("pretax_profit", "Pre-Tax Profit (EUR)", "200,000"),
                _eur_input("owner_salary", "Owner Salary (EUR)", "80,000"),
                cls="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6",
            ),
            Button("Get Market Comps →", type="submit",
                   cls="rounded-lg px-6 py-3 text-sm font-semibold text-white cursor-pointer",
                   style=f"background:{CTA};"),
            hx_post=action_url,
            hx_target="#tool-content",
            hx_swap="innerHTML",
            hx_indicator="#loading-indicator",
        ),
        Div(id="loading-indicator", cls="htmx-indicator mt-4 text-center", style=f"color:{CTA}"),
        cls="card rounded-lg p-6 max-w-3xl mx-auto",
    )


def valuation_financial_form(profile: dict, action_url: str):
    """Step 2 for Valuation: revenue, pre-tax profit, owner salary."""
    return Div(
        Div(company_profile_card(profile), cls="mb-6"),
        Form(
            Input(type="hidden", name="url", value=profile.get("url", "")),
            Input(type="hidden", name="company_data", value=__import__("json").dumps(profile)),
            H3("Financial Information", cls="text-base font-semibold mb-4", style=f"color:{INK}"),
            Div(
                _eur_input("revenue", "Annual Revenue (EUR)", "1,000,000"),
                _eur_input("pretax_profit", "Pre-Tax Profit (EUR)", "200,000"),
                _eur_input("owner_salary", "Owner Salary (EUR)", "80,000"),
                cls="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6",
            ),
            Button("Get Valuation →", type="submit",
                   cls="rounded-lg px-6 py-3 text-sm font-semibold text-white cursor-pointer",
                   style=f"background:{CTA};"),
            hx_post=action_url,
            hx_target="#tool-content",
            hx_swap="innerHTML",
            hx_indicator="#loading-indicator",
        ),
        Div(id="loading-indicator", cls="htmx-indicator mt-4 text-center", style=f"color:{CTA}"),
        cls="card rounded-lg p-6 max-w-3xl mx-auto",
    )


def buyer_match_financial_form(profile: dict, action_url: str):
    """Step 2 for Find Buyers: revenue range + profit range."""
    def _select(name, label, options):
        return Div(
            Label(label, cls="text-xs font-medium mb-1 block", style=f"color:{INK_MUTED}"),
            Select(
                *[Option(lbl, value=val) for val, lbl in options],
                name=name,
                cls="w-full rounded-lg px-3 py-2.5 text-sm",
                style=f"background:{BG}; color:{INK}; border:1px solid {LINE}; outline:none;",
            ),
        )

    rev_options = [
        ("0-500000", "Under €500K"),
        ("500000-1000000", "€500K – €1M"),
        ("1000000-5000000", "€1M – €5M"),
        ("5000000-20000000", "€5M – €20M"),
        ("20000000-100000000", "€20M – €100M"),
        ("100000000+", "€100M+"),
    ]
    profit_options = [
        ("negative", "Loss-making"),
        ("0-100000", "Under €100K"),
        ("100000-500000", "€100K – €500K"),
        ("500000-2000000", "€500K – €2M"),
        ("2000000+", "€2M+"),
    ]

    return Div(
        Div(company_profile_card(profile), cls="mb-6"),
        Form(
            Input(type="hidden", name="url", value=profile.get("url", "")),
            Input(type="hidden", name="company_data", value=__import__("json").dumps(profile)),
            H3("Company Size", cls="text-base font-semibold mb-4", style=f"color:{INK}"),
            Div(
                _select("revenue_range", "Annual Revenue (EUR)", rev_options),
                _select("profit_range", "Annual Profit (EUR)", profit_options),
                cls="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6",
            ),
            Button("Find Buyers →", type="submit",
                   cls="rounded-lg px-6 py-3 text-sm font-semibold text-white cursor-pointer",
                   style=f"background:{CTA};"),
            hx_post=action_url,
            hx_target="#tool-content",
            hx_swap="innerHTML",
            hx_indicator="#loading-indicator",
        ),
        Div(id="loading-indicator", cls="htmx-indicator mt-4 text-center", style=f"color:{CTA}"),
        cls="card rounded-lg p-6 max-w-3xl mx-auto",
    )


# ───── Result sections ───────────────────────────────────────────────

def _section_card(title: str, *content):
    return Div(
        H3(title, cls="text-base font-semibold mb-3", style=f"color:{INK}"),
        *content,
        cls="card rounded-lg p-5 mb-4",
    )


def _kv_row(label: str, value: str, highlight: bool = False):
    return Div(
        Span(label, cls="text-xs", style=f"color:{INK_MUTED}"),
        Span(value, cls="text-sm font-semibold", style=f"color:{CTA if highlight else INK}"),
        cls="flex justify-between py-1.5 border-b", style=f"border-color:{LINE}",
    )


def comps_results(profile: dict, financials: dict, sector_data: dict):
    """Market Comps results page."""
    name = profile.get("name", "Company")
    sector = profile.get("sector", "Technology")
    revenue = financials.get("revenue", 0)
    pretax = financials.get("pretax_profit", 0)
    owner_salary = financials.get("owner_salary", 0)
    sde = pretax + owner_salary

    rev_mult = sector_data.get("ev_revenue", 1.0)
    ebitda_mult = sector_data.get("ev_ebitda", 8.0)
    ebit_mult = sector_data.get("ev_ebit", 10.0)

    val_revenue = revenue * rev_mult
    val_ebitda = sde * ebitda_mult
    val_low = min(val_revenue, val_ebitda) * 0.85
    val_high = max(val_revenue, val_ebitda) * 1.15

    return Div(
        Div(company_profile_card(profile), cls="mb-6"),
        _section_card(
            f"Sector M&A Snapshot — {sector}",
            _kv_row("EV / Revenue multiple", f"{rev_mult:.1f}x"),
            _kv_row("EV / EBITDA multiple", f"{ebitda_mult:.1f}x"),
            _kv_row("EV / EBIT multiple", f"{ebit_mult:.1f}x") if ebit_mult else "",
            P(f"Based on Damodaran sector data for {sector}.",
              cls="text-xs mt-3", style=f"color:{INK_MUTED}"),
        ),
        _section_card(
            "Your Company Metrics",
            _kv_row("Annual Revenue", f"€{revenue:,.0f}"),
            _kv_row("Pre-Tax Profit", f"€{pretax:,.0f}"),
            _kv_row("Owner Salary / SDE", f"€{sde:,.0f}"),
        ),
        _section_card(
            "Estimated Valuation Range",
            _kv_row("Revenue-based (EV/Revenue)", f"€{val_revenue:,.0f}"),
            _kv_row("Earnings-based (EV/EBITDA)", f"€{val_ebitda:,.0f}"),
            Div(
                Div(
                    Span("Estimated Range", cls="text-xs", style=f"color:{INK_MUTED}"),
                    Div(
                        Span(f"€{val_low:,.0f}", cls="text-lg font-bold", style=f"color:{BUY}"),
                        Span(" — ", style=f"color:{INK_MUTED}"),
                        Span(f"€{val_high:,.0f}", cls="text-lg font-bold", style=f"color:{SELL}"),
                    ),
                    cls="mt-2",
                ),
                cls="mt-4 pt-4 border-t", style=f"border-color:{LINE}",
            ),
        ),
        lead_capture_form("comparables", profile),
        cls="max-w-3xl mx-auto",
    )


def buyer_results(profile: dict, buyers: list[dict], total_count: int = 5):
    """Find Buyers results with partial gating."""
    visible = buyers[:3]
    blurred = buyers[3:]

    def buyer_card(b, blurred=False):
        style_extra = "filter: blur(4px); pointer-events: none;" if blurred else ""
        return Div(
            Div(
                Div(
                    H4(b.get("name", "Buyer"), cls="text-sm font-semibold", style=f"color:{INK}"),
                    Span(b.get("type", "strategic").replace("_", " ").title(),
                         cls="text-[10px] mono px-1.5 py-0.5 rounded ml-2",
                         style=f"color:{CTA}; border:1px solid {CTA};"),
                    cls="flex items-center",
                ),
                Span(b.get("country", ""), cls="text-xs", style=f"color:{INK_MUTED}"),
                cls="flex justify-between items-start mb-2",
            ),
            P(b.get("rationale", ""), cls="text-xs leading-relaxed", style=f"color:{INK_MUTED}"),
            Div(
                A(b.get("website", ""), href=b.get("website", "#"),
                  cls="text-xs", style=f"color:{BUY}",
                  target="_blank") if b.get("website") else "",
                cls="mt-2",
            ),
            cls="card rounded-lg p-4 mb-3",
            style=style_extra,
        )

    return Div(
        Div(company_profile_card(profile), cls="mb-6"),
        _section_card(
            f"Matched Buyers ({total_count} found)",
            *[buyer_card(b) for b in visible],
        ),
        Div(
            *[buyer_card(b, blurred=True) for b in blurred],
            Div(
                P("Sign up to see all matched buyers",
                  cls="text-sm font-medium text-center", style=f"color:{INK}"),
                A("Get Started →", href="/app?role=seller",
                  cls="inline-block mt-2 rounded-lg px-6 py-2 text-sm font-semibold text-white no-underline",
                  style=f"background:{CTA};"),
                cls="text-center py-6",
            ),
            cls="relative",
        ) if blurred else "",
        lead_capture_form("match", profile),
        cls="max-w-3xl mx-auto",
    )


def valuation_results(profile: dict, financials: dict, sector_data: dict, value_drivers: list[dict] = None):
    """3-step valuation results: Comps → Drivers → Range."""
    name = profile.get("name", "Company")
    sector = profile.get("sector", "Technology")
    revenue = financials.get("revenue", 0)
    pretax = financials.get("pretax_profit", 0)
    owner_salary = financials.get("owner_salary", 0)
    sde = pretax + owner_salary

    rev_mult = sector_data.get("ev_revenue", 1.0)
    ebitda_mult = sector_data.get("ev_ebitda", 8.0)

    val_revenue = revenue * rev_mult
    val_sde = sde * ebitda_mult
    val_mid = (val_revenue + val_sde) / 2
    val_low = val_mid * 0.75
    val_high = val_mid * 1.25

    drivers = value_drivers or []
    positive = [d for d in drivers if d.get("direction") == "positive"]
    negative = [d for d in drivers if d.get("direction") == "negative"]

    return Div(
        Div(company_profile_card(profile), cls="mb-6"),
        # Step 1: Deal Comps
        _section_card(
            "Step 1: Deal Comparables",
            _kv_row("Sector", sector),
            _kv_row("EV/Revenue multiple", f"{rev_mult:.1f}x"),
            _kv_row("EV/EBITDA multiple", f"{ebitda_mult:.1f}x"),
            P("Multiples sourced from Damodaran industry benchmarks.",
              cls="text-xs mt-3", style=f"color:{INK_MUTED}"),
        ),
        # Step 2: Value Drivers
        _section_card(
            "Step 2: Value Drivers",
            Div(
                *[Div(
                    Span("▲ ", style=f"color:{SELL}"),
                    Span(d.get("label", ""), cls="text-xs", style=f"color:{INK}"),
                    cls="py-1",
                ) for d in positive],
                *[Div(
                    Span("▼ ", style="color:#EF4444"),
                    Span(d.get("label", ""), cls="text-xs", style=f"color:{INK}"),
                    cls="py-1",
                ) for d in negative],
            ) if drivers else P("Value driver analysis requires company-specific data.",
                                cls="text-xs", style=f"color:{INK_MUTED}"),
        ),
        # Step 3: Valuation Range
        _section_card(
            "Step 3: Valuation Range",
            _kv_row("Revenue-based valuation", f"€{val_revenue:,.0f}"),
            _kv_row("SDE/EBITDA-based valuation", f"€{val_sde:,.0f}"),
            Div(
                Div(
                    Span("Estimated Enterprise Value", cls="text-xs", style=f"color:{INK_MUTED}"),
                    Div(
                        Span(f"€{val_low:,.0f}", cls="text-xl font-bold", style=f"color:{BUY}"),
                        Span(" — ", cls="text-lg", style=f"color:{INK_MUTED}"),
                        Span(f"€{val_high:,.0f}", cls="text-xl font-bold", style=f"color:{SELL}"),
                    ),
                    P(f"Midpoint: €{val_mid:,.0f}", cls="text-xs mt-1", style=f"color:{INK_MUTED}"),
                    cls="mt-2",
                ),
                cls="mt-4 pt-4 border-t", style=f"border-color:{LINE}",
            ),
            P("This is an indicative range based on sector benchmarks. A formal valuation "
              "requires detailed financial analysis, adjusted EBITDA, and market-specific factors.",
              cls="text-xs mt-4 leading-relaxed", style=f"color:{INK_MUTED}"),
        ),
        lead_capture_form("valuation", profile),
        cls="max-w-3xl mx-auto",
    )


# ───── Lead capture form ──────────────────────────────────────────────

def lead_capture_form(tool: str, profile: dict):
    """Soft lead-capture form at bottom of results."""
    return Div(
        Div(
            Span("◈", cls="mono mr-2", style=f"color:{CTA}"),
            Span("Book a 15-minute call", cls="text-base font-semibold", style=f"color:{INK}"),
            cls="flex items-center mb-1",
        ),
        P("Speak with an M&A advisor about your company's potential.",
          cls="text-xs mb-5", style=f"color:{INK_MUTED}"),
        Form(
            Input(type="hidden", name="tool", value=tool),
            Input(type="hidden", name="company_url", value=profile.get("url", "")),
            Input(type="hidden", name="company_name", value=profile.get("name", "")),
            Div(
                Div(
                    Input(name="full_name", type="text", placeholder="Full Name", required=True,
                          cls="w-full rounded-lg px-3 py-2.5 text-sm",
                          style=f"background:{BG}; color:{INK}; border:1px solid {LINE}; outline:none;"),
                ),
                Div(
                    Input(name="email", type="email", placeholder="Email", required=True,
                          cls="w-full rounded-lg px-3 py-2.5 text-sm",
                          style=f"background:{BG}; color:{INK}; border:1px solid {LINE}; outline:none;"),
                ),
                cls="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3",
            ),
            Div(
                Div(
                    Input(name="phone", type="tel", placeholder="Phone (optional)",
                          cls="w-full rounded-lg px-3 py-2.5 text-sm",
                          style=f"background:{BG}; color:{INK}; border:1px solid {LINE}; outline:none;"),
                ),
                Div(
                    Select(
                        Option("Timeline", value="", disabled=True, selected=True),
                        Option("Immediately", value="immediately"),
                        Option("1-3 months", value="1-3 months"),
                        Option("3-6 months", value="3-6 months"),
                        Option("6-12 months", value="6-12 months"),
                        Option("Just exploring", value="exploring"),
                        name="timeline",
                        cls="w-full rounded-lg px-3 py-2.5 text-sm",
                        style=f"background:{BG}; color:{INK}; border:1px solid {LINE}; outline:none;",
                    ),
                ),
                cls="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4",
            ),
            Button("Book Call →", type="submit",
                   cls="rounded-lg px-6 py-2.5 text-sm font-semibold text-white cursor-pointer",
                   style=f"background:{CTA};"),
            hx_post="/tools/lead",
            hx_target="#lead-form-result",
            hx_swap="innerHTML",
        ),
        Div(id="lead-form-result"),
        cls="card rounded-lg p-6 mt-6",
    )


def lead_success():
    return Div(
        Div(
            Span("✓", cls="text-2xl mr-2", style=f"color:{SELL}"),
            Span("Thank you! We'll be in touch shortly.", cls="text-sm font-medium", style=f"color:{INK}"),
            cls="flex items-center",
        ),
        cls="py-4",
    )


# ───── Industry page components ──────────────────────────────────────

def industry_hero(industry: dict):
    from data.industries import ADVISORS
    return Div(
        Div(
            Span(industry["tagline"],
                 cls="mono text-xs tracking-widest mb-4 block",
                 style=f"color:{CTA}"),
            H1(industry["hero_heading"],
               cls="text-3xl sm:text-4xl md:text-5xl font-bold tightest mb-6",
               style=f"color:{INK}"),
            Div(
                A("Find Buyers →", href="/tools/match",
                  cls="rounded-lg px-6 py-3 text-sm font-semibold text-white no-underline mr-3",
                  style=f"background:{CTA};"),
                *[A(adv["label"], href=adv["url"],
                    cls="rounded-lg px-5 py-3 text-sm font-medium no-underline mr-3",
                    style=f"color:{INK}; border:1px solid {LINE};",
                    target="_blank")
                  for adv in ADVISORS.values()],
                cls="flex flex-wrap gap-2",
            ),
            cls="text-center max-w-3xl mx-auto",
        ),
        cls="px-6 pt-20 pb-12",
    )


def industry_description(industry: dict):
    return Div(
        Div(
            P(industry["description"],
              cls="text-base leading-relaxed mb-6",
              style=f"color:{INK_MUTED}"),
            Ul(
                *[Li(f"✓ {b}", cls="text-sm py-1.5", style=f"color:{INK}")
                  for b in industry.get("bullets", [])],
                cls="list-none pl-0 mb-6",
            ),
            A("Get in touch →", href="/contact",
              cls="text-sm font-semibold no-underline",
              style=f"color:{CTA}"),
            cls="max-w-3xl mx-auto",
        ),
        cls="px-6 py-12",
    )


def industry_sub_sectors(industry: dict):
    subs = industry.get("sub_sectors", [])
    return Div(
        Div(
            H2("Sub-Sectors We Cover",
               cls="text-2xl font-bold tightest text-center mb-8",
               style=f"color:{INK}"),
            Div(
                *[Div(
                    Span(s["icon"], cls="text-2xl mb-2 block"),
                    H3(s["name"], cls="text-sm font-semibold mb-1", style=f"color:{INK}"),
                    P(s["description"], cls="text-xs leading-relaxed", style=f"color:{INK_MUTED}"),
                    cls="card rounded-lg p-5 text-center",
                ) for s in subs],
                cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4",
            ),
            cls="max-w-6xl mx-auto",
        ),
        cls="px-6 py-12",
    )


def industry_advisor_ctas():
    from data.industries import ADVISORS
    return Div(
        Div(
            H2("Work With a Local Advisor",
               cls="text-2xl font-bold tightest text-center mb-8",
               style=f"color:{INK}"),
            Div(
                *[Div(
                    Span({"lt": "🇱🇹", "ee": "🇪🇪"}.get(k, "🌍"), cls="text-3xl mb-3 block"),
                    H3(adv["label"], cls="text-sm font-semibold mb-2", style=f"color:{INK}"),
                    A("Visit →", href=adv["url"],
                      cls="text-xs font-medium no-underline",
                      style=f"color:{CTA}",
                      target="_blank"),
                    cls="card rounded-lg p-6 text-center",
                ) for k, adv in ADVISORS.items()],
                cls="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-lg mx-auto",
            ),
            cls="max-w-4xl mx-auto",
        ),
        cls="px-6 py-12",
    )


def industry_find_buyers_widget():
    return Div(
        Div(
            H2("Curious About Your Potential Buyers?",
               cls="text-2xl font-bold tightest text-center mb-3",
               style=f"color:{INK}"),
            P("Enter your company website to see matched buyers.",
              cls="text-sm text-center mb-6", style=f"color:{INK_MUTED}"),
            Form(
                Div(
                    Input(name="url", type="text", placeholder="https://your-company.com",
                          cls="flex-1 rounded-lg px-4 py-3 text-sm",
                          style=f"background:{BG}; color:{INK}; border:1px solid {LINE}; outline:none;"),
                    Button("Find Buyers →", type="submit",
                           cls="rounded-lg px-6 py-3 text-sm font-semibold text-white cursor-pointer",
                           style=f"background:{CTA};"),
                    cls="flex gap-3 max-w-lg mx-auto",
                ),
                action="/tools/match",
                method="get",
            ),
            cls="max-w-3xl mx-auto",
        ),
        cls="px-6 py-16",
    )


def industry_faqs(industry: dict):
    faqs = industry.get("faqs", [])
    return Div(
        Div(
            H2("Frequently Asked Questions",
               cls="text-2xl font-bold tightest text-center mb-8",
               style=f"color:{INK}"),
            Div(
                *[Div(
                    Div(
                        Span(faq["q"], cls="text-sm font-medium flex-1", style=f"color:{INK}"),
                        Span("+", cls="faq-arrow text-lg ml-3", style=f"color:{CTA}"),
                        cls="flex items-center justify-between cursor-pointer py-3",
                        onclick="toggleFaq(this)",
                    ),
                    Div(
                        P(faq["a"], cls="text-sm leading-relaxed pb-3", style=f"color:{INK_MUTED}"),
                        cls="hidden",
                    ),
                    cls="border-b", style=f"border-color:{LINE}",
                ) for faq in faqs],
                cls="max-w-2xl mx-auto",
            ),
            cls="max-w-4xl mx-auto",
        ),
        cls="px-6 py-12",
    )
