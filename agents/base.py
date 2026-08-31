"""Shared helpers for building LangGraph ReAct agents — mirrors pehero's pattern.

Every agent module exports its spec and tools. `cached_agent(slug)` builds a
LangGraph app cached by both agent slug and user identity, so personal skill
overrides never leak between sessions.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain.agents import create_agent

from agents.registry import AgentSpec, by_slug
from utils.llm_factory import create_llm

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "system"
SHARED_PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "shared" / "liquidround_context.md"


def load_system_prompt(slug: str, user_id: str | None = None) -> str:
    """Load shared context plus the user's override or global/file baseline."""
    shared = SHARED_PROMPT_FILE.read_text() if SHARED_PROMPT_FILE.exists() else ""
    specific_file = PROMPTS_DIR / f"{slug}.md"
    specific = specific_file.read_text() if specific_file.exists() else ""
    try:
        from utils.prompts import get_latest_prompt, prompt_scope_user_id
        from utils.request_context import current_user_id
        resolved_user_id = user_id if user_id is not None else current_user_id()
        edited = get_latest_prompt(
            slug,
            user_id=prompt_scope_user_id(slug, resolved_user_id),
        )
        if edited is not None:
            specific = edited
    except Exception:
        # Files remain the deployment baseline and keep offline tests deterministic.
        pass
    if not specific:
        log.warning("no system prompt for %s — using shared context only", slug)
    return (shared + "\n\n" + specific).strip()


def build_agent(
    spec: AgentSpec,
    tools: list[BaseTool],
    *,
    user_id: str | None = None,
):
    """Build a LangGraph ReAct agent with the configured LLM + provided tools.

    The public `cached_agent` helper owns caching so the user identity forms
    part of the cache key.

    If the LLM cannot be constructed (e.g. no API key in the current env),
    gracefully degrade to `build_simple_agent` so unit tests still pass
    structurally. In production with keys set, this path always returns a
    full LangGraph ReAct app.
    """
    system = load_system_prompt(spec.slug, user_id=user_id)
    try:
        llm = create_llm()
    except Exception as e:  # noqa: BLE001
        log.warning("LLM construction failed for %s (%s) — using simple fallback", spec.slug, e)
        return build_simple_agent(spec, user_id=user_id)
    # LangChain's create_agent compiles a LangGraph tool-calling graph.
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system or None,
        name=spec.slug,
    )


def build_simple_agent(spec: AgentSpec, *, user_id: str | None = None):
    """Fallback for agents without a dedicated module — no tools, just the
    system prompt + the LLM. Returns a plain callable `(query, context) -> str`
    rather than a LangGraph app."""
    system = load_system_prompt(spec.slug, user_id=user_id)

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


@lru_cache(maxsize=128)
def _cached_agent(slug: str, user_id: str | None):
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
        if slug == "hermes_orchestrator":
            return module.build()
        return build_agent(spec, module.TOOLS, user_id=user_id)
    except ModuleNotFoundError:
        log.info("no module for %s — using simple LLM agent", slug)
        return build_simple_agent(spec, user_id=user_id)


def cached_agent(slug: str, user_id: str | None = None):
    """Return an agent cached by both slug and effective user identity."""
    if user_id is None:
        from utils.request_context import current_user_id
        user_id = current_user_id()
    return _cached_agent(slug, user_id)


cached_agent.cache_clear = _cached_agent.cache_clear
cached_agent.cache_info = _cached_agent.cache_info
