"""
3-pane layout shell: left nav, middle content, right research panel.
"""
from fasthtml.common import *


def LeftPane():
    """Left sidebar with shortcuts and navigation commands."""
    nav_items = [
        ("search", "Find Targets", "/targets", "Buyer-led M&A search"),
        ("handshake", "Find Buyers", "/buyers", "Seller-led matching"),
        ("trending-up", "IPO Assessment", "/ipo", "IPO readiness check"),
        ("upload", "Upload Docs", "/upload", "XLS, PPT, PDF upload"),
        ("scale", "Score Match", "/score", "Synergy scoring"),
        ("bar-chart-2", "Market Intel", "/market", "Sector heatmaps"),
        ("building", "Company Search", "/company", "yfinance lookup"),
        ("clock", "Deal History", "/deals", "Past workflows"),
        ("settings", "Settings", "/settings", "LLM & config"),
    ]

    items = []
    for icon, label, href, tip in nav_items:
        items.append(
            A(
                Div(
                    Span(cls=f"i-lucide-{icon} w-5 h-5") if False else Span(label[0], cls="w-5 h-5 flex items-center justify-center text-xs font-bold bg-blue-100 text-blue-700 rounded"),
                    Span(label, cls="text-sm"),
                    cls="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-blue-50 text-gray-700 hover:text-blue-700 transition-colors cursor-pointer",
                ),
                hx_get=href,
                hx_target="#main-content",
                hx_push_url="true",
                title=tip,
            )
        )

    return Nav(
        Div(
            H1("LiquidRound", cls="text-xl font-bold text-blue-800"),
            P("M&A Research Platform", cls="text-xs text-gray-500 mt-1"),
            cls="px-4 py-5 border-b border-gray-200",
        ),
        Div(*items, cls="flex flex-col gap-1 p-3"),
        Div(
            P("Predictive Labs Ltd", cls="text-xs text-gray-400 text-center"),
            cls="mt-auto p-4 border-t border-gray-200",
        ),
        cls="w-60 bg-white border-r border-gray-200 flex flex-col h-screen fixed left-0 top-0 z-10",
    )


def RightPane():
    """Right slide-out panel for research results and thinking trace."""
    return Div(
        Div(
            Div(
                H2("Research Panel", cls="text-lg font-semibold text-gray-800"),
                Button(
                    "X",
                    cls="text-gray-400 hover:text-gray-600 text-sm font-bold",
                    onclick="document.getElementById('right-pane').classList.add('translate-x-full')",
                ),
                cls="flex items-center justify-between",
            ),
            cls="px-4 py-3 border-b border-gray-200",
        ),
        Div(
            P("Research results will appear here when you run a query.",
              cls="text-sm text-gray-500 italic p-4"),
            id="research-content",
            cls="flex-1 overflow-y-auto",
        ),
        id="right-pane",
        cls="w-96 bg-white border-l border-gray-200 fixed right-0 top-0 h-screen flex flex-col transition-transform duration-300 translate-x-full z-20 shadow-lg",
    )


def Shell(*children, page_title="LiquidRound"):
    """Main 3-pane application shell."""
    return (
        Title(page_title),
        LeftPane(),
        Main(
            *children,
            id="main-content",
            cls="ml-60 min-h-screen bg-gray-50 p-6",
        ),
        RightPane(),
    )
