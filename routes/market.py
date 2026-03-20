"""
Market intelligence routes.
"""
from fasthtml.common import *
from components.layout import Shell
from components.charts import SectorHeatmap

ar = APIRouter()


@ar
def market():
    """Market intelligence dashboard."""
    # Sample sector data (would come from market_intelligence.py in production)
    sectors = ["Technology", "Healthcare", "Financials", "Consumer", "Energy",
               "Utilities", "Materials", "Industrials", "Real Estate", "Comm Services"]
    years = ["2022", "2023", "2024", "2025", "2026 YTD"]
    # Sample performance data (%)
    values = [
        [-28, 57, 35, 22, 8],    # Tech
        [-2, 2, 12, 5, 3],       # Healthcare
        [-11, 12, 28, 15, 6],    # Financials
        [-37, 42, 22, 10, 4],    # Consumer
        [64, -1, -2, -8, 2],     # Energy
        [1, -7, 24, 8, 5],       # Utilities
        [-12, 10, 8, 3, 1],      # Materials
        [-5, 18, 17, 12, 4],     # Industrials
        [-26, 12, 6, 4, 2],      # Real Estate
        [-40, 55, 32, 18, 7],    # Comm Services
    ]

    return Shell(
        H1("Market Intelligence", cls="text-2xl font-bold text-gray-800 mb-4"),
        P("Sector performance analysis for M&A deal sourcing.", cls="text-gray-500 mb-6"),
        Div(
            SectorHeatmap("sector-heatmap", sectors, years, values),
            cls="bg-white rounded-lg p-4 border border-gray-200 mb-6",
        ),
        Div(
            H2("Key Insights", cls="text-lg font-semibold text-gray-700 mb-3"),
            Div(
                _insight("Technology sector continues strong growth — active M&A pipeline", "green"),
                _insight("Energy sector volatile — opportunistic acquisitions possible", "yellow"),
                _insight("Healthcare stable but slow — value plays available", "blue"),
                _insight("Consumer sector recovery creating seller interest", "blue"),
                cls="space-y-2",
            ),
            cls="bg-white rounded-lg p-6 border border-gray-200",
        ),
    )


def _insight(text, color):
    colors = {"green": "border-green-400 bg-green-50", "yellow": "border-yellow-400 bg-yellow-50", "blue": "border-blue-400 bg-blue-50"}
    c = colors.get(color, colors["blue"])
    return Div(P(text, cls="text-sm text-gray-700"), cls=f"border-l-4 {c} px-3 py-2 rounded-r")
