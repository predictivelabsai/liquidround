"""
3-pane layout shell: left nav (buyer/seller grouped), middle content, right canvas.
"""
from fasthtml.common import *


def _nav_link(label, href, tip):
    """Single nav link for route-based pages."""
    return A(
        Div(
            Span(label, cls="text-sm"),
            cls="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-blue-50 text-gray-700 hover:text-blue-700 transition-colors cursor-pointer",
        ),
        hx_get=href,
        hx_target="#main-content",
        hx_push_url="true",
        title=tip,
    )


def LeftPane():
    """Left sidebar — grouped by buyer/seller workflow."""
    return Nav(
        Div(
            H1("LiquidRound", cls="text-xl font-bold text-blue-800"),
            P("M&A Research Platform", cls="text-xs text-gray-500 mt-1"),
            cls="px-4 py-5 border-b border-gray-200",
        ),
        Div(
            # I'M BUYING
            Details(
                Summary(Span("I'M BUYING", cls="text-xs font-bold text-blue-700 uppercase tracking-wide"),
                        cls="px-3 py-2 cursor-pointer hover:bg-blue-50 rounded list-none nav-section-header"),
                Div(
                    _nav_link("Find Targets", "/targets", "Buyer-led M&A search"),
                    _nav_link("Company Search", "/company", "yfinance lookup"),
                    _nav_link("Score Match", "/score", "Synergy scoring"),
                    cls="pl-2 border-l-2 border-blue-200 ml-3 mb-2",
                ),
                open=True,
            ),
            # I'M SELLING
            Details(
                Summary(Span("I'M SELLING", cls="text-xs font-bold text-green-700 uppercase tracking-wide"),
                        cls="px-3 py-2 cursor-pointer hover:bg-green-50 rounded list-none nav-section-header"),
                Div(
                    _nav_link("Find Buyers", "/buyers", "Seller-led matching"),
                    _nav_link("Upload Docs", "/upload", "XLS, PPT, PDF upload"),
                    _nav_link("IPO Assessment", "/ipo", "IPO readiness check"),
                    cls="pl-2 border-l-2 border-green-200 ml-3 mb-2",
                ),
                open=True,
            ),
            # RESEARCH
            Details(
                Summary(Span("RESEARCH", cls="text-xs font-bold text-gray-500 uppercase tracking-wide"),
                        cls="px-3 py-2 cursor-pointer hover:bg-gray-50 rounded list-none nav-section-header"),
                Div(
                    _nav_link("Market Intel", "/market", "Sector heatmaps"),
                    _nav_link("Deal History", "/deals", "Past workflows"),
                    cls="pl-2 border-l-2 border-gray-200 ml-3 mb-2",
                ),
            ),
            # WORKSPACE
            Details(
                Summary(Span("WORKSPACE", cls="text-xs font-bold text-gray-500 uppercase tracking-wide"),
                        cls="px-3 py-2 cursor-pointer hover:bg-gray-50 rounded list-none nav-section-header"),
                Div(
                    _nav_link("Settings", "/settings", "LLM & config"),
                    cls="pl-2 border-l-2 border-gray-200 ml-3 mb-2",
                ),
            ),
            cls="flex flex-col gap-1 p-3 flex-1 overflow-y-auto",
        ),
        Div(
            P("Predictive Labs Ltd", cls="text-xs text-gray-400 text-center"),
            cls="mt-auto p-4 border-t border-gray-200",
        ),
        cls="w-60 bg-white border-r border-gray-200 flex flex-col h-screen fixed left-0 top-0 z-10",
    )


def RightPane():
    """Right slide-out canvas panel."""
    return Div(
        Div(
            Div(
                H2("Canvas", cls="text-lg font-semibold text-gray-800"),
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
            P("Results will appear here when you run a query.",
              cls="text-sm text-gray-500 italic p-4"),
            id="canvas-content",
            cls="flex-1 overflow-y-auto",
        ),
        id="right-pane",
        cls="w-[440px] bg-white border-l border-gray-200 fixed right-0 top-0 h-screen flex flex-col transition-transform duration-300 translate-x-full z-20 shadow-lg",
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
