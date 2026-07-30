"""Intent router — maps a user message to a specialist agent slug.

Order of preference:
  1. Forced slug (caller already knows which agent)
  2. Explicit prefix (`triage:`, `memo:`, etc.) — from AgentSpec.prefix
  3. Keyword heuristics per category
  4. LLM fallback classifier (short prompt, low-cost)
"""
from __future__ import annotations

import logging
import re

from agents.registry import AGENTS, AGENTS_BY_SLUG

log = logging.getLogger(__name__)


# Keyword hints per category — tuned to avoid false positives on generic terms.
CATEGORY_HINTS: dict[str, list[str]] = {
    "sourcing": [
        "find target", "find buyers", "find deals", "off-market", "off market",
        "surface deal", "triage", "go/no-go", "go no go", "scan the market",
        "seller intent", "likely to sell", "founder owned", "founder-owned",
        "sale process", "proprietary deal",
    ],
    "underwriting": [
        "profile", "cap table", "ltm", "trailing twelve months", "qoe",
        "quality of earnings", "dcf", "discounted cash flow",
        "ev/ebitda", "ev/revenue", "entry multiple", "exit multiple",
        "synergy", "synergies", "valuation", "trading comp", "transaction comp",
        "wacc", "terminal growth",
    ],
    "diligence": [
        "data room", "vdr", "due diligence", "diligence",
        "abstract", "contract abstract", "msa", "customer contract",
        "regulatory", "licensure", "litigation", "change of control",
        "100-day plan", "ops review", "operational diligence",
        "esg", "environmental", "governance",
    ],
    "capital": [
        "ic memo", "investment memo", "memo", "teaser", "cim",
        "confidential info memo", "bid strategy", "term sheet", "escrow",
        "earnout", "ipo", "going public", "listing",
        "score buyer", "score target", "score match", "match score",
    ],
    "portfolio": [
        "research", "deep research", "market intel",
        "integrate", "integration plan", "post-close", "post close",
        "day one", "first 100 days",
    ],
    "public_markets": [
        "hedge fund", "hedge funds", "13f", "13-f",
        "activist filing", "activist stake", "13d", "13g",
        "fund holdings", "institutional ownership", "aum",
        "popular securities", "crowded trade", "most held",
        "fund concentration",
        "sec filing", "sec filings", "edgar", "10-k", "10-q", "8-k",
        "annual report", "quarterly report", "proxy statement",
        "def 14a", "s-1", "form 4", "xbrl",
        "press release", "press releases", "news release", "announcement",
        "globenewswire", "euronext news", "omx news", "baltic news",
        "prnewswire", "pr newswire",
        "reverse merger", "reverse takeover", "rto", "public shell",
        "shell company", "backdoor listing", "back-door listing",
        "qualifying transaction", "capital pool company", "cpc transaction",
        "de-spac", "de spac",
        "sedar", "sedarplus", "sedar+", "canadian filing", "csa filing",
    ],
    "investor_relations": [
        "investor relations", "ir triage", "materiality", "disclosure",
        "reg fd", "mar article 17", "inside information",
        "disclosure obligation", "press release draft", "publish release",
        "wire service", "globenewswire submission", "pr newswire submission",
        "exchange notification", "investor list", "distribution plan",
        "compliance review", "selective disclosure",
    ],
}


_PREFIX_MAP: dict[str, str] = {a.prefix.lower(): a.slug for a in AGENTS}
_ALL_PREFIXES = tuple(sorted(_PREFIX_MAP.keys(), key=len, reverse=True))


def _prefix_match(message: str) -> str | None:
    lower = message.lower().strip()
    for prefix in _ALL_PREFIXES:
        if lower.startswith(prefix):
            return _PREFIX_MAP[prefix]
    return None


def _keyword_scores(message: str) -> dict[str, int]:
    lower = message.lower()
    scores: dict[str, int] = {}
    for agent in AGENTS:
        # Exact agent-name presence wins big
        if agent.name.lower() in lower:
            scores[agent.slug] = scores.get(agent.slug, 0) + 5
        for hint in CATEGORY_HINTS.get(agent.category, []):
            if hint in lower:
                scores[agent.slug] = scores.get(agent.slug, 0) + (2 if " " in hint else 1)
    return scores


def _best_in_category_for(message: str) -> str | None:
    """If the message looks like a category, pick a sane default agent for it."""
    lower = message.lower()
    # Specific landing words → specific agents
    if "triage" in lower or "go/no-go" in lower or "go no go" in lower:
        return "deal_triage"
    if "find target" in lower or "acquisition target" in lower:
        return "target_scanner"
    if "find buyer" in lower or "strategic buyer" in lower:
        return "buyer_scanner"
    if "ic memo" in lower or "investment memo" in lower:
        return "ic_memo_writer"
    if "teaser" in lower or "cim" in lower:
        return "teaser_designer"
    if "ipo" in lower or "going public" in lower:
        return "ipo_readiness"
    if "synergy" in lower or "synergies" in lower:
        return "synergy_analyst"
    if "dcf" in lower or "discounted cash flow" in lower:
        return "dcf_valuer"
    if "deep research" in lower or "research:" in lower:
        return "research_analyst"
    if "score" in lower and ("buyer" in lower or "target" in lower or "match" in lower):
        return "match_scorer"
    if "ltm" in lower or "quality of earnings" in lower or "qoe" in lower:
        return "ltm_normalizer"
    if "msa" in lower or "contract abstract" in lower:
        return "contract_abstractor"
    if "100-day" in lower or "100 day" in lower or "integration" in lower:
        return "integration_planner"
    if "hedge fund" in lower or "13f" in lower or "activist filing" in lower:
        return "hedge_fund_analyst"
    if "fund holdings" in lower or "institutional ownership" in lower:
        return "hedge_fund_analyst"
    if "sec filing" in lower or "edgar" in lower or "10-k" in lower or "10-q" in lower:
        return "filing_analyst"
    if "8-k" in lower or "annual report" in lower or "proxy statement" in lower:
        return "filing_analyst"
    if "def 14a" in lower or "xbrl" in lower:
        return "filing_analyst"
    if any(term in lower for term in (
        "reverse merger", "reverse takeover", "public shell", "shell company",
        "qualifying transaction", "capital pool company", "de-spac", "de spac",
    )):
        return "reverse_merger_analyst"
    if "press release" in lower or "news release" in lower or "globenewswire" in lower:
        if any(word in lower for word in ("write", "draft", "create", "prepare", "compose")):
            return "press_release_writer"
        return "press_release_analyst"
    if "euronext news" in lower or "omx news" in lower or "baltic news" in lower:
        return "press_release_analyst"
    # ── Investor Relations & Communications ──────────────────────────────
    if "ir-triage" in lower or ("materiality" in lower and "disclose" in lower) or "reg fd" in lower or "mar article 17" in lower:
        return "ir_triage"
    if "ir-compliance" in lower or "compliance review" in lower or "selective disclosure" in lower:
        return "ir_compliance"
    if "ir-publish" in lower or ("publish" in lower and "release" in lower) or "wire-ready" in lower or "pre-publish checklist" in lower:
        return "ir_publish"
    if "ir-distribute" in lower or "distribution plan" in lower or ("wire service" in lower and "routing" in lower) or "exchange notification" in lower:
        return "ir_distribute"
    if "investor relations" in lower and not any(p in lower for p in ("triage", "compliance", "publish", "distribute")):
        return "press_release_writer"
    return None


_LLM_CLASSIFIER_PROMPT = """You are a router for LiquidRound, an M&A / IPO deal-flow platform.
Return just the SLUG of the best specialist agent for the user's message.

Agents (slug: one_liner):
{agent_list}

User message: {message}

Best slug:"""


def _llm_classify(message: str) -> str:
    """LLM fallback — cheap call, returns slug or a sane default."""
    try:
        from utils.llm_factory import create_llm
        agent_list = "\n".join(f"- {a.slug}: {a.one_liner}" for a in AGENTS)
        prompt = _LLM_CLASSIFIER_PROMPT.format(agent_list=agent_list, message=message[:500])
        llm = create_llm()
        resp = llm.invoke(prompt).content.strip().split()[0].strip(":.,\"'")
        if resp in AGENTS_BY_SLUG:
            return resp
    except Exception as e:  # noqa: BLE001
        log.warning("llm classifier failed: %s", e)
    return "deal_triage"  # sane default


def route(message: str, forced_slug: str | None = None) -> str:
    """Return the best agent slug for `message`.

    Never raises — always returns a slug.
    """
    if forced_slug and forced_slug in AGENTS_BY_SLUG:
        return forced_slug

    slug = _prefix_match(message)
    if slug:
        return slug

    slug = _best_in_category_for(message)
    if slug:
        return slug

    scores = _keyword_scores(message)
    if scores:
        return max(scores, key=scores.get)

    return _llm_classify(message)


def route_with_context(
    message: str,
    previous_user_messages: list[str] | tuple[str, ...] | None = None,
    active_slug: str | None = None,
) -> str:
    """Route a refinement without losing its active specialist mandate."""
    prefix_slug = _prefix_match(message)
    if prefix_slug:
        return prefix_slug

    direct_slug = _best_in_category_for(message)
    if direct_slug:
        return direct_slug

    scores = _keyword_scores(message)
    if scores:
        return max(scores, key=scores.get)

    previous = [str(item).strip() for item in (previous_user_messages or []) if str(item).strip()]
    if previous and active_slug in AGENTS_BY_SLUG and len(message.split()) <= 24:
        return active_slug

    contextual = "\n".join([*previous[-5:], message]) if previous else message
    return _llm_classify(contextual)


def contextualize_user_query(message: str, previous_user_messages: list[str] | tuple[str, ...] | None = None) -> str:
    """Give a specialist the compact user-only mandate history."""
    previous = [str(item).strip() for item in (previous_user_messages or []) if str(item).strip()]
    if not previous:
        return message
    prior = "\n".join(f"- {item}" for item in previous[-5:])
    return (
        "Continue the user's accumulated mandate. Preserve prior filters and treat the "
        "latest turn as a refinement unless it explicitly changes them.\n\n"
        f"Prior user criteria (oldest to newest):\n{prior}\n\n"
        f"Latest user turn:\n{message}"
    )


def has_specialist_prefix(message: str) -> bool:
    """True if the message starts with a registered agent prefix."""
    return _prefix_match(message) is not None


def strip_prefix(message: str) -> str:
    """Remove the leading `<prefix>:` from a message, if present.

    Supports hyphenated prefixes (e.g. `ir-triage:`, `write-release:`).
    """
    m = re.match(r"^\s*([a-z][a-z-]{1,15}):\s*", message, flags=re.IGNORECASE)
    if m and (m.group(1).lower() + ":") in _PREFIX_MAP:
        return message[m.end():]
    return message
