"""Integration & 100-Day Planner — buyer-side portfolio agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.companies import get_company_profile, get_financials
from tools.scoring import score_match
from tools.research import tavily_search

SPEC = AGENTS_BY_SLUG["integration_planner"]
TOOLS = [get_company_profile, get_financials, score_match, tavily_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
