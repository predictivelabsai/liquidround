"""
Research panel routes — EXA + TAVILY results and thinking trace.
"""
from fasthtml.common import *
from components.research_panel import ResearchPanel

ar = APIRouter()

# In-memory research cache keyed by workflow_id
_research_cache = {}


@ar
def research(workflow_id: str = ""):
    """Get research panel content for a workflow."""
    data = _research_cache.get(workflow_id, {})
    if not data:
        return Div(
            P("No research data yet for this workflow.", cls="text-sm text-gray-400 italic p-4"),
        )
    return ResearchPanel(data)


def store_research(workflow_id: str, data: dict):
    """Store research results for a workflow (called by API routes)."""
    _research_cache[workflow_id] = data
