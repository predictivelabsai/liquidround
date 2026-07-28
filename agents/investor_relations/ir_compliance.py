"""IR Compliance Reviewer — Reg FD / MAR / exchange disclosure checks on a draft."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.research import tavily_search, exa_search

SPEC = AGENTS_BY_SLUG["ir_compliance"]
TOOLS = [tavily_search, exa_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
