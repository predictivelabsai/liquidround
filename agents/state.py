"""Structured multi-turn mandate state for sourcing and underwriting agents."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field


@dataclass
class MandateState:
    geography: list[str] = field(default_factory=list)
    sector: str = ""
    ownership: list[str] = field(default_factory=list)
    min_revenue: str = ""
    min_ebitda: str = ""
    min_employees: int | None = None
    result_limit: int | None = None
    exclusions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value not in ("", [], None)}

    def as_prompt(self) -> str:
        values = self.to_dict()
        if not values:
            return "No structured mandate fields have been established."
        return "\n".join(f"- {key.replace('_', ' ')}: {value}" for key, value in values.items())


_GEOGRAPHIES = {
    "dach": "DACH", "baltics": "Baltics", "baltic": "Baltics",
    "lithuania": "Lithuania", "latvia": "Latvia", "estonia": "Estonia",
    "nordics": "Nordics", "nordic": "Nordics", "germany": "Germany",
    "austria": "Austria", "switzerland": "Switzerland", "canada": "Canada",
    "united states": "United States", "us": "United States", "uk": "United Kingdom",
}


def extract_mandate(messages: list[str] | tuple[str, ...]) -> MandateState:
    state = MandateState()
    combined = "\n".join(str(message) for message in messages if str(message).strip())
    lower = combined.lower()
    for key, label in _GEOGRAPHIES.items():
        if re.search(rf"\b{re.escape(key)}\b", lower) and label not in state.geography:
            state.geography.append(label)

    sector_matches = re.findall(
        r"\b(?:accounting|vertical|horizontal|fintech|healthcare|industrial|logistics|"
        r"renewable|cybersecurity|legal|hr|property|construction)\s+(?:saas|software|tech|services?)\b",
        lower,
    )
    if sector_matches:
        state.sector = sector_matches[-1].title()
    elif "saas" in lower:
        state.sector = "SaaS"

    for label in ("founder-owned", "family-owned", "sponsor-backed"):
        if label.split("-")[0] in lower and label not in state.ownership:
            state.ownership.append(label)

    money = r"(?:€|eur|\$|usd|£|gbp)?\s*\d+(?:\.\d+)?\s*[kmb]?"
    revenue = re.findall(rf"({money})\s*(?:revenue|arr)|(?:revenue|arr)\s*(?:of|above|over|>)?\s*({money})", lower)
    if revenue:
        state.min_revenue = next((part.strip() for part in revenue[-1] if part.strip()), "")
    ebitda = re.findall(rf"({money})\s*ebitda|ebitda\s*(?:of|above|over|>)?\s*({money})", lower)
    if ebitda:
        state.min_ebitda = next((part.strip() for part in ebitda[-1] if part.strip()), "")
    employees = re.findall(r"(\d+)\+?\s*(?:employees|staff|people|fte)", lower)
    if employees:
        state.min_employees = int(employees[-1])
    limits = re.findall(r"\b(\d+)\s*(?:max|maximum|targets?|companies|results?)\b", lower)
    range_limits = re.findall(r"\b\d+\s*-\s*(\d+)\s*(?:max(?:imum)?\b)?", lower)
    if limits or range_limits:
        state.result_limit = int((limits + range_limits)[-1])
    if "no other restriction" in lower:
        state.exclusions.append("No additional restrictions")
    return state
