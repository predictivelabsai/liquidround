"""Shared parsing utilities."""
from __future__ import annotations

import re


def parse_amount(raw) -> float:
    """Parse human-friendly amounts: 1M, 35.5k, 2B, 1,000,000, etc.

    Supports: k/K, m/M/mm/mn, b/B/bn, t/T/tr
    Strips: commas, spaces, currency symbols (€ $ £)
    """
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip().replace(",", "").replace(" ", "")
    s = re.sub(r'^[€$£]+', '', s)
    if not s:
        return 0.0
    m = re.match(r'^([+-]?\d+\.?\d*)\s*(k|m|mm|mn|b|bn|t|tr)?$', s, re.IGNORECASE)
    if m:
        num = float(m.group(1))
        suffix = (m.group(2) or "").lower()
        multipliers = {"k": 1e3, "m": 1e6, "mm": 1e6, "mn": 1e6,
                        "b": 1e9, "bn": 1e9, "t": 1e12, "tr": 1e12}
        return num * multipliers.get(suffix, 1)
    try:
        return float(s)
    except ValueError:
        return 0.0
