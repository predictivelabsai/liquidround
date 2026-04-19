"""DCF Valuer — shared underwriting agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.valuation import dcf_valuer as dcf_tool
from tools.companies import get_company_profile, get_financials

SPEC = AGENTS_BY_SLUG["dcf_valuer"]
TOOLS = [dcf_tool, get_company_profile, get_financials]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
