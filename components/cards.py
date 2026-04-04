"""
Reusable card components for deals, targets, scores, and metrics.
"""
from fasthtml.common import *


def MetricCard(label, value, subtitle="", color="blue"):
    colors = {"blue": "text-blue-700 bg-blue-50", "green": "text-green-700 bg-green-50", "red": "text-red-700 bg-red-50", "yellow": "text-yellow-700 bg-yellow-50"}
    c = colors.get(color, colors["blue"])
    return Div(
        P(label, cls="text-xs font-medium text-gray-500 uppercase tracking-wide"),
        P(str(value), cls=f"text-2xl font-bold mt-1 {c.split()[0]}"),
        P(subtitle, cls="text-xs text-gray-400 mt-1") if subtitle else "",
        cls=f"rounded-lg p-4 {c.split()[1]} border border-gray-100",
    )


def TargetCard(target: dict, index: int = 0):
    name = target.get("company_name", "Unknown")
    ticker = target.get("ticker", "")
    score = target.get("strategic_fit_score", 0)
    revenue = target.get("estimated_revenue", "N/A")
    sector = target.get("sector", "")
    highlights = target.get("investment_highlights", "")

    score_color = "text-green-600" if score >= 4 else "text-yellow-600" if score >= 3 else "text-red-600"

    return Div(
        Div(
            Div(
                H3(f"{index}. {name}", cls="font-semibold text-gray-800"),
                Span(ticker, cls="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded") if ticker else "",
                cls="flex items-center gap-2",
            ),
            Span(f"{score}/5", cls=f"font-bold {score_color}"),
            cls="flex items-center justify-between",
        ),
        Div(
            Span(f"Revenue: {revenue}", cls="text-sm text-gray-600"),
            Span(f" | {sector}", cls="text-sm text-gray-500") if sector else "",
            cls="mt-1",
        ),
        P(highlights, cls="text-sm text-gray-500 mt-2 line-clamp-2") if highlights else "",
        cls="bg-white rounded-lg p-4 border border-gray-200 hover:border-blue-300 transition-colors",
    )


def ScoreCard(score_data: dict):
    """Synergy score card with dimension breakdown."""
    composite = score_data.get("composite_score", 0)
    dims = score_data.get("dimensions", {})
    recommendation = score_data.get("recommendation", "N/A")

    rec_colors = {
        "STRONG BUY": "bg-green-100 text-green-800",
        "PROCEED": "bg-blue-100 text-blue-800",
        "CAUTIOUS": "bg-yellow-100 text-yellow-800",
        "PASS": "bg-red-100 text-red-800",
    }
    rec_cls = rec_colors.get(recommendation, "bg-gray-100 text-gray-800")

    dim_bars = []
    for dim_name, dim_data in dims.items():
        s = dim_data.get("score", 0) if isinstance(dim_data, dict) else dim_data
        label = dim_name.replace("_", " ").title()
        bar_width = s * 10  # 0-100%
        bar_color = "bg-green-500" if s >= 7 else "bg-yellow-500" if s >= 5 else "bg-red-500"
        dim_bars.append(
            Div(
                Div(
                    Span(label, cls="text-xs text-gray-600"),
                    Span(f"{s}/10", cls="text-xs font-medium"),
                    cls="flex justify-between mb-1",
                ),
                Div(
                    Div(cls=f"{bar_color} h-2 rounded-full", style=f"width:{bar_width}%"),
                    cls="w-full bg-gray-200 rounded-full h-2",
                ),
                cls="mb-2",
            )
        )

    return Div(
        Div(
            Div(
                P("Composite Score", cls="text-sm text-gray-500"),
                P(str(composite), cls="text-4xl font-bold text-blue-700"),
                P("out of 100", cls="text-xs text-gray-400"),
                cls="text-center",
            ),
            Span(recommendation, cls=f"px-3 py-1 rounded-full text-sm font-semibold {rec_cls}"),
            cls="flex items-center justify-between mb-4",
        ),
        Div(*dim_bars),
        Div(
            id="score-radar-chart",
            cls="mt-4",
        ),
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


def BuyerMatchCard(match: dict, index: int = 1):
    """Buyer match card with 7-dimension score bars — reusable in chat and canvas."""
    rec = match.get("recommendation", "N/A")
    rec_cls = {"STRONG BUY": "bg-green-100 text-green-800", "PROCEED": "bg-blue-100 text-blue-800",
               "CAUTIOUS": "bg-yellow-100 text-yellow-800", "PASS": "bg-red-100 text-red-800"}.get(rec, "bg-gray-100")
    dims = match.get("dimensions", {})
    dim_bars = []
    for dk in ["revenue_synergies","cost_synergies","strategic_fit","cultural_fit","financial_health","integration_risk","market_timing"]:
        dv = dims.get(dk, {})
        s = dv.get("score", 5) if isinstance(dv, dict) else 5
        bar_w = s * 10
        bar_c = "bg-green-500" if s >= 7 else "bg-yellow-500" if s >= 5 else "bg-red-500"
        dim_bars.append(Div(
            Div(Span(dk.replace("_"," ").title(), cls="text-xs text-gray-500"), Span(f"{s}/10", cls="text-xs font-medium"), cls="flex justify-between"),
            Div(Div(cls=f"{bar_c} h-1.5 rounded-full", style=f"width:{bar_w}%"), cls="w-full bg-gray-200 rounded-full h-1.5"),
            cls="mb-1",
        ))
    return Div(
        Div(
            Div(
                Span(f"#{index}", cls="text-xs font-bold text-gray-400 mr-2"),
                Span(match.get("buyer","Unknown"), cls="font-semibold text-gray-800"),
                Span(f" ({match.get('buyer_type','')})", cls="text-xs text-gray-500"),
            ),
            Div(
                Span(str(match.get("composite_score",0)), cls="text-lg font-bold text-blue-700"),
                Span(rec, cls=f"text-xs px-2 py-0.5 rounded-full font-medium {rec_cls} ml-2"),
            ),
            cls="flex items-center justify-between mb-2",
        ),
        P(match.get("rationale",""), cls="text-sm text-gray-600 mb-2"),
        *dim_bars,
        cls="bg-white rounded-lg p-4 border border-gray-200 mb-2",
    )


def DealCard(deal: dict):
    status = deal.get("status", "unknown")
    status_colors = {
        "completed": "bg-green-100 text-green-700",
        "in_progress": "bg-blue-100 text-blue-700",
        "error": "bg-red-100 text-red-700",
    }
    s_cls = status_colors.get(status, "bg-gray-100 text-gray-700")
    return Div(
        Div(
            H3(deal.get("deal_type", "M&A").upper(), cls="font-semibold text-gray-800"),
            Span(status, cls=f"text-xs px-2 py-0.5 rounded-full {s_cls}"),
            cls="flex items-center justify-between",
        ),
        P(deal.get("user_query", "")[:80], cls="text-sm text-gray-600 mt-2"),
        P(deal.get("created_at", ""), cls="text-xs text-gray-400 mt-2"),
        cls="bg-white rounded-lg p-4 border border-gray-200 hover:shadow-sm transition-shadow cursor-pointer",
        hx_get=f"/deal/{deal.get('deal_id', '')}",
        hx_target="#main-content",
    )
