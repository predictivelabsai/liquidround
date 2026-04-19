"""Shared helpers for building specialist agents by slug.

Each of the 22 agents has a single-file module under
`agents/<category>/<slug>.py` that exports:
  - SPEC (from registry)
  - build()  # -> callable(query: str, context: dict) -> str

`build()` returns a simple callable (not a LangGraph graph) so it integrates
cleanly with the existing chat pipeline in `routes/api.py` and `main.py`
without requiring a structured-tool layer. Upgrade path to LangGraph ReAct
is straightforward once tools are wrapped as StructuredTools.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from agents.registry import AgentSpec, by_slug
from utils.llm_factory import create_llm

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "system"
SHARED_PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "shared" / "liquidround_context.md"


def load_system_prompt(slug: str) -> str:
    """Load `prompts/shared/liquidround_context.md` + `prompts/system/<slug>.md`."""
    shared = SHARED_PROMPT_FILE.read_text() if SHARED_PROMPT_FILE.exists() else ""
    specific_file = PROMPTS_DIR / f"{slug}.md"
    specific = specific_file.read_text() if specific_file.exists() else ""
    if not specific:
        log.warning("no system prompt for %s — using shared context only", slug)
    return (shared + "\n\n" + specific).strip()


def build_simple_agent(spec: AgentSpec):
    """Return a callable `(query: str, context: dict | None = None) -> str`.

    The returned callable invokes the LLM with the agent's system prompt +
    the user's query. Used by NEW agents that don't already have a Python
    implementation; EXISTS agents (wrapping scoring_agent.py, valuer.py,
    target_finder.py, etc.) override with their own build() in their module.
    """
    system = load_system_prompt(spec.slug)

    def _run(query: str, context: dict | None = None) -> str:
        ctx = context or {}
        prompt_str = system
        if ctx:
            try:
                prompt_str = system.format(**ctx)
            except (KeyError, IndexError):
                pass  # leave raw if template vars missing
        llm = create_llm()
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [SystemMessage(content=prompt_str), HumanMessage(content=query)]
        resp = llm.invoke(messages)
        return resp.content

    _run.__name__ = f"run_{spec.slug}"
    return _run


@lru_cache(maxsize=64)
def cached_agent(slug: str):
    """Fetch a cached agent callable by slug.

    Looks for `agents.<category>.<slug>.build()`; if not found, falls back
    to a simple LLM-with-system-prompt agent built from the registry spec.
    """
    spec = by_slug(slug)
    if spec is None:
        raise ValueError(f"unknown agent slug: {slug}")

    import importlib
    try:
        module = importlib.import_module(f"agents.{spec.category}.{spec.slug}")
        return module.build()
    except ModuleNotFoundError:
        log.info("no module for %s — using simple LLM agent", slug)
        return build_simple_agent(spec)
