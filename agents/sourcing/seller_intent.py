"""Seller Intent Signal — buyer-side sourcing agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.companies import get_company_profile
from tools.research import exa_search, tavily_search

SPEC = AGENTS_BY_SLUG["seller_intent"]
TOOLS = [get_company_profile, exa_search, tavily_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
