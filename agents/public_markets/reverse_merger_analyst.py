"""Reverse Merger Analyst — US RTO discovery and SPAC comparison."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.reverse_mergers import REVERSE_MERGER_TOOLS

SPEC = AGENTS_BY_SLUG["reverse_merger_analyst"]
TOOLS = REVERSE_MERGER_TOOLS


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
