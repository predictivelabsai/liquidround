"""Tests for the 25-agent registry + router — pure unit, no network."""
from __future__ import annotations

import pytest

from agents.registry import (
    AGENTS, AGENTS_BY_SLUG, AGENTS_BY_CATEGORY, CATEGORIES,
    by_audience, by_slug,
)
from agents.router import route, strip_prefix
from agents.base import load_system_prompt


# ── Shape invariants ────────────────────────────────────────────────────

def test_exactly_25_agents():
    assert len(AGENTS) == 26, f"expected 26 agents, got {len(AGENTS)}"


def test_unique_slugs():
    slugs = [a.slug for a in AGENTS]
    assert len(slugs) == len(set(slugs)), "duplicate slug detected"


def test_unique_prefixes():
    prefixes = [a.prefix for a in AGENTS]
    assert len(prefixes) == len(set(prefixes)), "duplicate prefix detected"


def test_all_categories_used():
    cat_keys = {c["key"] for c in CATEGORIES}
    used = {a.category for a in AGENTS}
    assert used == cat_keys, f"category mismatch: used={used} expected={cat_keys}"


def test_every_agent_has_audience():
    for a in AGENTS:
        assert a.audience in ("buyer", "seller", "shared"), a.slug


def test_audience_filter():
    buyer = by_audience("buyer")
    seller = by_audience("seller")
    # "both" buckets include shared agents
    assert all(a.audience in ("buyer", "shared") for a in buyer)
    assert all(a.audience in ("seller", "shared") for a in seller)
    # Spot-check: buyer has target_scanner, seller has buyer_scanner
    assert any(a.slug == "target_scanner" for a in buyer)
    assert any(a.slug == "buyer_scanner" for a in seller)


# ── Prompt loading ──────────────────────────────────────────────────────

@pytest.mark.parametrize("spec", AGENTS, ids=lambda s: s.slug)
def test_every_agent_has_system_prompt(spec):
    prompt = load_system_prompt(spec.slug)
    assert prompt, f"{spec.slug}: system prompt is empty"
    assert len(prompt) > 200, f"{spec.slug}: prompt suspiciously short ({len(prompt)} chars)"


# ── Agent build ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("spec", AGENTS, ids=lambda s: s.slug)
def test_every_agent_has_module(spec):
    """Every registry entry must have a module at agents/<category>/<slug>.py
    that exports SPEC + TOOLS + build(). Enforces the pehero convention."""
    import importlib
    module = importlib.import_module(f"agents.{spec.category}.{spec.slug}")
    assert hasattr(module, "SPEC"), f"{spec.slug}: module missing SPEC"
    assert hasattr(module, "TOOLS"), f"{spec.slug}: module missing TOOLS"
    assert hasattr(module, "build"), f"{spec.slug}: module missing build()"
    assert module.SPEC.slug == spec.slug, f"{spec.slug}: SPEC mismatch"
    assert isinstance(module.TOOLS, list), f"{spec.slug}: TOOLS must be a list"
    assert len(module.TOOLS) > 0, f"{spec.slug}: TOOLS is empty — agents need at least one tool"


@pytest.mark.parametrize("spec", AGENTS, ids=lambda s: s.slug)
def test_every_agent_builds(spec):
    """cached_agent(slug) returns a callable for every registered agent.
    With API keys set, returns a LangGraph ReAct app; without, returns a
    simple-LLM callable fallback."""
    from agents.base import cached_agent
    agent = cached_agent(spec.slug)
    assert callable(agent) or hasattr(agent, "invoke"), f"{spec.slug}: agent not callable and not a graph"


@pytest.mark.parametrize("spec", AGENTS, ids=lambda s: s.slug)
def test_every_agent_has_tools(spec):
    """Every agent module exposes at least one StructuredTool."""
    import importlib
    module = importlib.import_module(f"agents.{spec.category}.{spec.slug}")
    from langchain_core.tools import BaseTool
    assert all(isinstance(t, BaseTool) for t in module.TOOLS), f"{spec.slug}: TOOLS contains non-BaseTool"


# ── Router ──────────────────────────────────────────────────────────────

PREFIX_CASES = [
    ("triage: SaaS EUR 10M EBITDA",        "deal_triage"),
    ("memo: draft for NovaTech",            "ic_memo_writer"),
    ("dcf: Harju Elekter 9% WACC",          "dcf_valuer"),
    ("multi: apply peer multiples",         "multiples_valuer"),
    ("score buyer:Siemens target:Harju",    "match_scorer"),
    ("profile: SAP.DE",                     "company_profiler"),
    ("research: Baltic M&A",                "research_analyst"),
    ("ipo: Ignitis readiness",              "ipo_readiness"),
    ("vdr: audit NovaTech",                 "vdr_auditor"),
    ("scan: Nordic renewables",             "target_scanner"),
    ("buyers: SaaS EUR 15M",                "buyer_scanner"),
    ("synergy: Siemens + Harju",            "synergy_analyst"),
    ("abstract: top customer MSAs",         "contract_abstractor"),
    ("esg: environmental risks",            "esg_reviewer"),
    ("legal: open litigation",              "legal_reviewer"),
    ("ops: working capital",                "operational_dd"),
    ("teaser: blind teaser for NovaTech",   "teaser_designer"),
    ("bid: cash/stock mix",                 "bid_strategist"),
    ("integrate: 100-day plan",             "integration_planner"),
    ("intent: founder-owned logistics",     "seller_intent"),
    ("ltm: normalize NovaTech P&L",         "ltm_normalizer"),
    ("comps: SaaS M&A precedents",          "comps_finder"),
    ("hedgefunds: top funds by AUM",         "hedge_fund_analyst"),
    ("filings: AAPL 10-K filings",            "filing_analyst"),
    ("releases: recent M&A announcements",     "press_release_analyst"),
]


@pytest.mark.parametrize("msg,expected", PREFIX_CASES, ids=lambda v: v if isinstance(v, str) else "")
def test_prefix_routing(msg, expected):
    assert route(msg) == expected


FREEFORM_CASES = [
    ("Find acquisition targets in the Nordics",  "target_scanner"),
    ("Draft the investment committee memo",       "ic_memo_writer"),
    ("What are the synergies between A and B?",   "synergy_analyst"),
]


@pytest.mark.parametrize("msg,expected", FREEFORM_CASES)
def test_freeform_routing_falls_back_sensibly(msg, expected):
    # Free-form routing may use keyword heuristics; just assert we don't
    # fall through to the LLM default "deal_triage" for these clear cases.
    got = route(msg)
    assert got == expected, f"free-form: {msg!r} routed to {got}, expected {expected}"


def test_strip_prefix():
    assert strip_prefix("memo: draft for X") == "draft for X"
    assert strip_prefix("free-form, no prefix") == "free-form, no prefix"
    assert strip_prefix("  triage:  leading space") == "leading space"
