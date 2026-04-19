"""Deep Research Analyst — shared portfolio agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.research import exa_search, tavily_search, deep_research
from tools.companies import get_company_profile

SPEC = AGENTS_BY_SLUG["research_analyst"]
TOOLS = [deep_research, exa_search, tavily_search, get_company_profile]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
