"""IR Event Triage — materiality and disclosure-obligation go / no-go."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.research import tavily_search, exa_search
from tools.press_releases import search_press_releases_tool

SPEC = AGENTS_BY_SLUG["ir_triage"]
TOOLS = [tavily_search, exa_search, search_press_releases_tool]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
