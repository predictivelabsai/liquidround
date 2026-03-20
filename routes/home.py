"""
Home route — main 3-pane view with sample buttons and chat.
"""
from fasthtml.common import *
from components.layout import Shell
from components.chat import ChatMessage, ChatInput, AgentProgress
from components.cards import MetricCard, TargetCard, ScoreCard

ar = APIRouter()


def _sample_buttons():
    """2 rows x 3 cols of sample M&A queries."""
    queries = [
        ("Find Fintech Targets", "Find fintech companies to acquire with $20-100M revenue"),
        ("Healthcare SaaS", "Looking for SaaS acquisition targets in healthcare"),
        ("Prepare for Sale", "Preparing to sell our B2B software company"),
        ("Find Strategic Buyers", "Need help finding buyers for our logistics business"),
        ("IPO Readiness", "Assessing IPO readiness for our tech company"),
        ("Score Acquisition", "Score the acquisition match between a PE firm and a cybersecurity startup"),
    ]
    buttons = []
    for label, query in queries:
        buttons.append(
            Button(
                label,
                hx_post="/chat",
                hx_vals=f'{{"msg": "{query}"}}',
                hx_target="#chat-messages",
                hx_swap="beforeend",
                hx_on__after_request="document.getElementById('right-pane').classList.remove('translate-x-full');",
                cls="bg-white border border-gray-200 rounded-lg px-4 py-3 text-sm text-gray-700 hover:border-blue-400 hover:bg-blue-50 transition-colors text-left",
            )
        )
    return Div(
        H2("Quick Start", cls="text-lg font-semibold text-gray-800 mb-3"),
        Div(*buttons, cls="grid grid-cols-3 gap-3"),
        cls="mb-6",
    )


@ar
def index():
    return Shell(
        Div(
            H1("LiquidRound", cls="text-3xl font-bold text-blue-800"),
            P("AI-Powered M&A and IPO Deal Flow Platform", cls="text-gray-500 mt-1"),
            cls="mb-8",
        ),
        _sample_buttons(),
        Div(
            H2("Chat", cls="text-lg font-semibold text-gray-800 mb-3"),
            Div(
                P("Welcome! Select a sample query above or type your own M&A question below.",
                  cls="text-sm text-gray-500 italic"),
                id="chat-messages",
                cls="bg-white rounded-lg border border-gray-200 p-4 min-h-64 max-h-96 overflow-y-auto space-y-2",
            ),
            ChatInput(),
            cls="mb-6",
        ),
        Div(id="workflow-progress", cls="mb-6"),
    )


@ar
def targets():
    """Buyer-led M&A target search page."""
    return Shell(
        H1("Find Acquisition Targets", cls="text-2xl font-bold text-gray-800 mb-4"),
        P("Search for companies matching your acquisition criteria.", cls="text-gray-500 mb-6"),
        Form(
            Div(
                Div(
                    Label("Industry / Sector", cls="block text-sm font-medium text-gray-700 mb-1"),
                    Input(name="industry", placeholder="e.g., Fintech, Healthcare SaaS, Logistics",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"),
                    cls="flex-1",
                ),
                Div(
                    Label("Revenue Range", cls="block text-sm font-medium text-gray-700 mb-1"),
                    Input(name="revenue", placeholder="e.g., $20M-100M",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"),
                    cls="flex-1",
                ),
                Div(
                    Label("Geography", cls="block text-sm font-medium text-gray-700 mb-1"),
                    Input(name="geography", placeholder="e.g., US, UK, Europe",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"),
                    cls="flex-1",
                ),
                cls="grid grid-cols-3 gap-4 mb-4",
            ),
            Div(
                Label("Additional Criteria", cls="block text-sm font-medium text-gray-700 mb-1"),
                Textarea(name="criteria", placeholder="Describe the ideal target profile, strategic rationale, deal size...",
                         rows="3", cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"),
                cls="mb-4",
            ),
            Button("Search Targets", type="submit",
                   cls="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"),
            hx_post="/api/find-targets",
            hx_target="#target-results",
            hx_indicator="#target-spinner",
        ),
        Div(id="target-spinner", cls="htmx-indicator flex justify-center mt-4",
            children=[P("Searching...", cls="text-sm text-gray-500 animate-pulse")]),
        Div(id="target-results", cls="mt-6"),
    )


@ar
def buyers():
    """Seller-led M&A buyer search page."""
    return Shell(
        H1("Find Buyers / Merger Partners", cls="text-2xl font-bold text-gray-800 mb-4"),
        P("Identify strategic and financial buyers for your business.", cls="text-gray-500 mb-6"),
        Form(
            Div(
                Div(
                    Label("Your Company / Industry", cls="block text-sm font-medium text-gray-700 mb-1"),
                    Input(name="company", placeholder="e.g., B2B SaaS in logistics",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"),
                ),
                Div(
                    Label("Revenue / Size", cls="block text-sm font-medium text-gray-700 mb-1"),
                    Input(name="revenue", placeholder="e.g., $15M ARR",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"),
                ),
                cls="grid grid-cols-2 gap-4 mb-4",
            ),
            Div(
                Label("What makes your business attractive?", cls="block text-sm font-medium text-gray-700 mb-1"),
                Textarea(name="description", rows="3", placeholder="Describe key differentiators, customer base, growth trajectory...",
                         cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"),
                cls="mb-4",
            ),
            Button("Find Buyers", type="submit",
                   cls="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"),
            hx_post="/api/find-buyers",
            hx_target="#buyer-results",
        ),
        Div(id="buyer-results", cls="mt-6"),
    )


@ar
def ipo():
    """IPO readiness assessment page."""
    return Shell(
        H1("IPO Readiness Assessment", cls="text-2xl font-bold text-gray-800 mb-4"),
        P("Evaluate your company's readiness for a public market listing.", cls="text-gray-500 mb-6"),
        Form(
            Div(
                Div(
                    Label("Company Name", cls="block text-sm font-medium text-gray-700 mb-1"),
                    Input(name="company", placeholder="Company name",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"),
                ),
                Div(
                    Label("Industry", cls="block text-sm font-medium text-gray-700 mb-1"),
                    Input(name="industry", placeholder="e.g., Enterprise SaaS",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"),
                ),
                cls="grid grid-cols-2 gap-4 mb-4",
            ),
            Div(
                Label("Key Financials & Context", cls="block text-sm font-medium text-gray-700 mb-1"),
                Textarea(name="context", rows="3", placeholder="Revenue, growth rate, profitability, governance structure...",
                         cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"),
                cls="mb-4",
            ),
            Button("Assess IPO Readiness", type="submit",
                   cls="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"),
            hx_post="/api/ipo-assess",
            hx_target="#ipo-results",
        ),
        Div(id="ipo-results", cls="mt-6"),
    )


@ar
def score():
    """Synergy scoring page."""
    return Shell(
        H1("Score Acquisition Match", cls="text-2xl font-bold text-gray-800 mb-4"),
        P("Evaluate buyer-target compatibility across 7 synergy dimensions.", cls="text-gray-500 mb-6"),
        Form(
            Div(
                Div(
                    Label("Buyer / Acquirer", cls="block text-sm font-medium text-gray-700 mb-1"),
                    Input(name="buyer", placeholder="Buyer company or profile",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"),
                ),
                Div(
                    Label("Target Company", cls="block text-sm font-medium text-gray-700 mb-1"),
                    Input(name="target", placeholder="Target company name or ticker",
                          cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"),
                ),
                cls="grid grid-cols-2 gap-4 mb-4",
            ),
            Div(
                Label("Deal Context", cls="block text-sm font-medium text-gray-700 mb-1"),
                Textarea(name="context", rows="3", placeholder="Strategic rationale, deal size, industry dynamics...",
                         cls="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"),
                cls="mb-4",
            ),
            Button("Score Match", type="submit",
                   cls="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"),
            hx_post="/api/score-match",
            hx_target="#score-results",
            hx_indicator="#score-spinner",
        ),
        Div(id="score-spinner", cls="htmx-indicator flex justify-center mt-4",
            children=[P("Scoring synergy dimensions...", cls="text-sm text-gray-500 animate-pulse")]),
        Div(id="score-results", cls="mt-6"),
    )


@ar
def company(ticker: str = ""):
    """Company lookup page."""
    return Shell(
        H1("Company Search", cls="text-2xl font-bold text-gray-800 mb-4"),
        P("Look up company profiles and financials via yfinance.", cls="text-gray-500 mb-6"),
        Form(
            Div(
                Input(name="ticker", value=ticker, placeholder="Enter ticker symbol (e.g., AAPL, MSFT, GOOG)",
                      cls="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500"),
                Button("Search", type="submit",
                       cls="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"),
                cls="flex gap-3",
            ),
            hx_get="/api/company-profile",
            hx_target="#company-results",
        ),
        Div(id="company-results", cls="mt-6"),
    )


@ar
def settings():
    """Settings page."""
    from utils.config import config
    return Shell(
        H1("Settings", cls="text-2xl font-bold text-gray-800 mb-4"),
        Div(
            Div(
                H2("LLM Configuration", cls="text-lg font-semibold text-gray-700 mb-3"),
                Div(
                    MetricCard("Provider", config.default_provider.upper(), "LLM provider"),
                    MetricCard("Model", config.default_model, "Active model"),
                    MetricCard("Temperature", str(config.default_temperature), "Creativity"),
                    MetricCard("Environment", config.environment.title(), "Runtime mode"),
                    cls="grid grid-cols-4 gap-4",
                ),
                cls="bg-white rounded-lg p-6 border border-gray-200 mb-6",
            ),
            Div(
                H2("API Keys Status", cls="text-lg font-semibold text-gray-700 mb-3"),
                Div(
                    _api_status("XAI (Grok)", bool(config.xai_api_key)),
                    _api_status("OpenAI", bool(config.openai_api_key)),
                    _api_status("EXA Search", bool(config.exa_api_key)),
                    _api_status("Tavily Search", bool(config.tavily_api_key)),
                    cls="space-y-2",
                ),
                cls="bg-white rounded-lg p-6 border border-gray-200",
            ),
        ),
    )


def _api_status(name, configured):
    dot = "bg-green-400" if configured else "bg-red-400"
    label = "Configured" if configured else "Not set"
    return Div(
        Div(cls=f"w-2 h-2 rounded-full {dot}"),
        Span(name, cls="text-sm font-medium text-gray-700"),
        Span(label, cls=f"text-xs {'text-green-600' if configured else 'text-red-500'}"),
        cls="flex items-center gap-3",
    )
