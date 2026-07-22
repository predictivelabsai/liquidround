"""Press release analyst — search and analyze press releases from Nordic, Baltic, and global markets."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.press_releases import PRESS_RELEASE_TOOLS
from tools.research import tavily_search

SPEC = AGENTS_BY_SLUG["press_release_analyst"]
TOOLS = PRESS_RELEASE_TOOLS + [tavily_search]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
