"""IC Memo Writer — buyer-side capital agent. Synthesizes everything into a memo."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.companies import get_company_profile, get_financials
from tools.valuation import dcf_valuer, multiples_valuer
from tools.scoring import score_match
from tools.documents import list_documents, read_document

SPEC = AGENTS_BY_SLUG["ic_memo_writer"]
TOOLS = [get_company_profile, get_financials, dcf_valuer, multiples_valuer,
         score_match, list_documents, read_document]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
