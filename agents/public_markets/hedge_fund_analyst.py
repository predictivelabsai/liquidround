"""Hedge Fund Analyst — public markets agent for SEC 13F data + news."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.hedge_funds import HEDGE_FUND_TOOLS
from tools.research import tavily_search

SPEC = AGENTS_BY_SLUG["hedge_fund_analyst"]
TOOLS = HEDGE_FUND_TOOLS + [tavily_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
