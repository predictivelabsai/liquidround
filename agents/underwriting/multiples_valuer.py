"""Multiples Valuer — shared underwriting agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.valuation import multiples_valuer as multiples_tool
from tools.companies import get_company_profile, get_financials, get_peer_companies

SPEC = AGENTS_BY_SLUG["multiples_valuer"]
TOOLS = [multiples_tool, get_company_profile, get_financials, get_peer_companies]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
