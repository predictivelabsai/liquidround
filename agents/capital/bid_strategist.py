"""Bid Strategist — buyer-side capital agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.companies import get_company_profile, get_financials
from tools.valuation import multiples_valuer
from tools.documents import read_document

SPEC = AGENTS_BY_SLUG["bid_strategist"]
TOOLS = [get_company_profile, get_financials, multiples_valuer, read_document]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
