"""IR Publish — finalize an approved draft into a publication-ready package."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.research import tavily_search

SPEC = AGENTS_BY_SLUG["ir_publish"]
TOOLS = [tavily_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
