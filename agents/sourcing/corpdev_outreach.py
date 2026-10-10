"""Corp-Dev Outreach — draft-only sequences for listed-buyer decision makers."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.companies import get_company_profile, get_peer_companies
from tools.research import exa_search, tavily_search

SPEC = AGENTS_BY_SLUG["corpdev_outreach"]
TOOLS = [get_company_profile, get_peer_companies, exa_search, tavily_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
