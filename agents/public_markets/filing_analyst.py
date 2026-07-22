"""SEC filing analyst — search, read, and analyze SEC EDGAR filings."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.filings import FILING_TOOLS

SPEC = AGENTS_BY_SLUG["filing_analyst"]
TOOLS = FILING_TOOLS


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
