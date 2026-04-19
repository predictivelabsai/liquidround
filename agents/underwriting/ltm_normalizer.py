"""LTM Financials Normalizer — shared underwriting agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.companies import get_financials, get_company_profile
from tools.documents import read_document, list_documents

SPEC = AGENTS_BY_SLUG["ltm_normalizer"]
TOOLS = [get_financials, get_company_profile, read_document, list_documents]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
