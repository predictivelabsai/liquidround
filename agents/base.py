"""Shared helpers for building LangGraph ReAct agents — mirrors pehero's pattern.

Every agent module exports `build()` that returns a cached LangGraph app
(or a simple callable as fallback). `cached_agent(slug)` looks up the
module and calls its `build()`; if no module exists, a simple-LLM agent
is returned as a graceful fallback.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

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


def build_agent(spec: AgentSpec, tools: list[BaseTool]):
    """Build a LangGraph ReAct agent with the configured LLM + provided tools.

    NOT cached here — caller's module-level `build()` handles caching via
    `@lru_cache` so each agent can pick its own tool set.

    If the LLM cannot be constructed (e.g. no API key in the current env),
    gracefully degrade to `build_simple_agent` so unit tests still pass
    structurally. In production with keys set, this path always returns a
    full LangGraph ReAct app.
    """
    system = load_system_prompt(spec.slug)
    try:
        llm = create_llm()
    except Exception as e:  # noqa: BLE001
        log.warning("LLM construction failed for %s (%s) — using simple fallback", spec.slug, e)
        return build_simple_agent(spec)
    # create_react_agent wires tool-use + message state automatically.
    return create_react_agent(llm, tools, prompt=system or None)


def build_simple_agent(spec: AgentSpec):
    """Fallback for agents without a dedicated module — no tools, just the
    system prompt + the LLM. Returns a plain callable `(query, context) -> str`
    rather than a LangGraph app."""
    system = load_system_prompt(spec.slug)

    def _run(query: str, context: dict | None = None) -> str:
        ctx = context or {}
        prompt_str = system
        if ctx:
            try:
                prompt_str = system.format(**ctx)
            except (KeyError, IndexError):
                pass
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = create_llm()
        resp = llm.invoke([SystemMessage(content=prompt_str), HumanMessage(content=query)])
        return resp.content

    _run.__name__ = f"run_{spec.slug}"
    return _run


@lru_cache(maxsize=64)
def cached_agent(slug: str):
    """Fetch a cached agent by slug.

    Convention: `agents/<category>/<slug>.py` exports `build()` that returns
    a LangGraph app. If no module exists, falls back to `build_simple_agent`
    (an LLM call with the agent's system prompt — no tools).
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
