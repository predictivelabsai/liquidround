"""
Deal history and management routes.
"""
from fasthtml.common import *
from components.layout import Shell
from components.cards import DealCard

ar = APIRouter()


@ar
def deals():
    """Deal history page."""
    from utils.database import db_service
    try:
        recent = db_service.get_recent_workflows(20)
    except Exception:
        recent = []

    if recent:
        deal_cards = [DealCard(w) for w in recent]
    else:
        deal_cards = [
            Div(
                P("No deals yet.", cls="text-gray-500 text-sm"),
                P("Start by running a query from the home page.", cls="text-gray-400 text-xs mt-1"),
                cls="text-center py-12",
            )
        ]

    return Shell(
        H1("Deal History", cls="text-2xl font-bold text-gray-800 mb-4"),
        P("View past M&A and IPO workflows.", cls="text-gray-500 mb-6"),
        Div(*deal_cards, cls="grid grid-cols-1 gap-3"),
    )
