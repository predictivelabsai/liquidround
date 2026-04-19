"""Deal Triage — shared sourcing agent. 90-second go/no-go."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.companies import get_company_profile, get_financials
from tools.research import tavily_search

SPEC = AGENTS_BY_SLUG["deal_triage"]
TOOLS = [get_company_profile, get_financials, tavily_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
