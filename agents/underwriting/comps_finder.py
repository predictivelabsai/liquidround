"""Comps Finder — shared underwriting agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.companies import get_company_profile, get_peer_companies, get_financials
from tools.research import exa_search, tavily_search

SPEC = AGENTS_BY_SLUG["comps_finder"]
TOOLS = [get_company_profile, get_peer_companies, get_financials, exa_search, tavily_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
