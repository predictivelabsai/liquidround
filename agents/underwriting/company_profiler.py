"""Company Profiler — shared underwriting agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.companies import get_company_profile, get_financials, get_peer_companies
from tools.research import tavily_search

SPEC = AGENTS_BY_SLUG["company_profiler"]
TOOLS = [get_company_profile, get_financials, get_peer_companies, tavily_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
