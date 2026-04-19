"""Contract Abstractor — shared diligence agent."""
from __future__ import annotations
from functools import lru_cache

from agents.base import build_agent
from agents.registry import AGENTS_BY_SLUG
from tools.documents import list_documents, read_document, extract_key_terms

SPEC = AGENTS_BY_SLUG["contract_abstractor"]
TOOLS = [list_documents, read_document, extract_key_terms]


@lru_cache(maxsize=1)
def build():
    return build_agent(SPEC, TOOLS)
