"""Prospectus builder (ported from the `ipogate` Streamlit app).

Extracts a standardized prospectus structure from a company document using the
project LLM (``utils.llm_factory.create_llm``), and renders the edited result to
markdown for the existing memo -> PDF pipeline.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "prospectus_extractor.md"

# Section key -> display title (drives both the form and the markdown output)
SECTIONS = {
    "basic_information": "Basic Information",
    "share_offering_details": "Share Offering Details",
    "company_overview": "Company Overview",
    "management_structure": "Management Structure",
    "financial_information": "Financial Information",
    "market_analysis": "Market Analysis",
    "risk_factors": "Risk Factors",
    "future_plans": "Future Plans",
}

# Fields rendered per section (drives the editable form). Long-text fields use a
# textarea; the rest use a single-line input.
FIELDS = {
    "basic_information": ["company_name", "company_type", "jurisdiction", "industry", "founded"],
    "share_offering_details": ["shares_offered", "nominal_value_per_share", "price_range",
                               "use_of_proceeds", "listing_venue"],
    "company_overview": ["founding_story", "core_business_description", "products_services",
                         "target_market", "growth_strategy"],
    "management_structure": ["board_members", "management_team", "key_personnel", "team_expertise"],
    "financial_information": ["revenue", "revenue_growth", "profit_margins", "ebitda",
                              "total_share_capital", "key_ratios"],
    "market_analysis": ["market_size", "growth_projections", "competitive_landscape", "market_position"],
    "risk_factors": ["business_risks", "market_risks", "financial_risks", "legal_risks",
                     "share_related_risks"],
    "future_plans": ["development_strategy", "investment_plans", "expansion_goals", "product_roadmap"],
}

# Fields that should render as multi-line textareas.
LONG_FIELDS = {
    "use_of_proceeds", "founding_story", "core_business_description", "products_services",
    "target_market", "growth_strategy", "team_expertise", "key_ratios", "competitive_landscape",
    "market_position", "business_risks", "market_risks", "financial_risks", "legal_risks",
    "share_related_risks", "development_strategy", "investment_plans", "expansion_goals",
    "product_roadmap", "management_team",
}

# Field-level help shown in the "IPO 101" accordion (ported from the ipogate pages).
SECTION_HELP = {
    "basic_information": "Legal identity of the issuer — name, type, jurisdiction, sector.",
    "share_offering_details": "The offer itself — shares offered, price range, listing venue and how proceeds will be used.",
    "company_overview": "What the business does, who it serves and how it intends to grow.",
    "management_structure": "Board, leadership team and the expertise behind the company.",
    "financial_information": "Revenue, growth, margins, EBITDA and capital structure.",
    "market_analysis": "Addressable market, growth outlook and competitive position.",
    "risk_factors": "Business, market, financial, legal and share-related risks investors should weigh.",
    "future_plans": "Roadmap — development, investment and expansion plans post-listing.",
}


def _empty_skeleton() -> dict:
    """Blank structure so the form always renders, even on extraction failure."""
    return {k: {} for k in SECTIONS}


def _load_prompt() -> str:
    try:
        return _PROMPT_PATH.read_text()
    except Exception:  # noqa: BLE001
        return "Extract a company prospectus as JSON."


def extract_prospectus(doc_text: str, max_chars: int = 12000) -> dict:
    """Run the LLM extraction over document text; return the parsed dict."""
    if not doc_text or not doc_text.strip():
        return _empty_skeleton()
    try:
        from .llm_factory import create_llm
        llm = create_llm(temperature=0)
        prompt = f"{_load_prompt()}\n\nDocument content:\n{doc_text[:max_chars]}\n\nJSON:"
        raw = llm.invoke(prompt).content
        data = _parse_json(raw)
        # ensure all sections exist
        skeleton = _empty_skeleton()
        for k in skeleton:
            if isinstance(data.get(k), dict):
                skeleton[k] = data[k]
        return skeleton
    except Exception as e:  # noqa: BLE001
        logger.warning("Prospectus extraction failed: %s", e)
        return _empty_skeleton()


def _parse_json(raw: str) -> dict:
    """Tolerant JSON parse — strips code fences and finds the outermost object."""
    if not raw:
        return {}
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1:
        s = s[start:end + 1]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {}


def _clean(v) -> str:
    return str(v).strip() if v not in (None, "") else ""


def prospectus_to_markdown(data: dict, company_name: str = "") -> str:
    """Assemble the edited section data into a formatted markdown prospectus."""
    name = company_name or (data.get("basic_information", {}) or {}).get("company_name", "") or "Company"
    md = [f"# {name} — Company Prospectus", ""]
    for key, title in SECTIONS.items():
        section = data.get(key) or {}
        rows = [(k, _clean(v)) for k, v in section.items() if _clean(v)]
        if not rows:
            continue
        md.append(f"## {title}")
        md.append("")
        for field, value in rows:
            label = field.replace("_", " ").title()
            md.append(f"**{label}:** {value}")
            md.append("")
    return "\n".join(md)
