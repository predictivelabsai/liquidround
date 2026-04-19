"""Match Scorer — shared capital agent. 7-dimension buyer-target scoring."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.scoring import score_match
from tools.companies import get_company_profile, get_financials

SPEC = AGENTS_BY_SLUG["match_scorer"]
TOOLS = [score_match, get_company_profile, get_financials]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
