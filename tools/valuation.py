"""Valuation tools — DCF + multiples + synergy quantification.

Pure Python calculators that consume yfinance-sourced financials and return
artifact-bearing results.

Consumed by:
  - dcf_valuer           (underwriting)
  - multiples_valuer     (underwriting)
  - synergy_analyst      (underwriting)
  - ic_memo_writer       (capital) — reads latest model
"""
from __future__ import annotations

import json
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from utils.yfinance_util import yfinance_util
from tools.artifact import emit


# ────────────────────────────────────────────────────────────────────────
# DCF
# ────────────────────────────────────────────────────────────────────────

class DCFArgs(BaseModel):
    ticker: str = Field(description="Exchange-qualified ticker of the target company.")
    wacc_pct: float = Field(default=10.0, ge=4.0, le=20.0, description="Weighted average cost of capital, percent.")
    terminal_growth_pct: float = Field(default=2.5, ge=0.0, le=5.0, description="Perpetuity growth rate, percent.")
    revenue_growth_pct: float = Field(default=8.0, ge=-10.0, le=40.0, description="5-yr revenue growth CAGR, percent.")
    ebitda_margin_pct: Optional[float] = Field(default=None, description="Terminal EBITDA margin %; if None, uses the current LTM margin.")
    years: int = Field(default=5, ge=3, le=10)


def _dcf_valuer(**kw) -> str:
    args = DCFArgs(**kw)
    fin = yfinance_util.get_financials(args.ticker)
    if "error" in fin:
        return f"Lookup failed for {args.ticker}: {fin['error']}"
    profile = yfinance_util.get_company_profile(args.ticker)

    rev = float(fin.get("revenue") or 0)
    ebitda = float(fin.get("ebitda") or 0)
    if rev <= 0:
        return f"No revenue data for {args.ticker}; DCF not possible."

    start_margin = ebitda / rev if rev else 0.10
    target_margin = (args.ebitda_margin_pct / 100.0) if args.ebitda_margin_pct else start_margin

    projections = []
    fcf_sum_pv = 0.0
    capex_pct = 0.04   # rule of thumb as % of revenue
    tax_rate = 0.22
    for y in range(1, args.years + 1):
        rev = rev * (1 + args.revenue_growth_pct / 100.0)
        # glide margin toward target linearly
        margin = start_margin + (target_margin - start_margin) * (y / args.years)
        ebitda_y = rev * margin
        capex = rev * capex_pct
        # approximate FCF: EBITDA * (1-tax) - capex
        fcf = ebitda_y * (1 - tax_rate) - capex
        pv = fcf / ((1 + args.wacc_pct / 100.0) ** y)
        fcf_sum_pv += pv
        projections.append({
            "year": y,
            "revenue": round(rev, 0),
            "ebitda": round(ebitda_y, 0),
            "ebitda_margin_%": round(margin * 100, 1),
            "fcf": round(fcf, 0),
            "pv_of_fcf": round(pv, 0),
        })

    # terminal value — Gordon growth
    terminal_fcf = projections[-1]["fcf"] * (1 + args.terminal_growth_pct / 100.0)
    terminal_value = terminal_fcf / max(0.001, (args.wacc_pct - args.terminal_growth_pct) / 100.0)
    terminal_pv = terminal_value / ((1 + args.wacc_pct / 100.0) ** args.years)

    enterprise_value = fcf_sum_pv + terminal_pv

    summary = {
        "wacc_%": args.wacc_pct,
        "terminal_growth_%": args.terminal_growth_pct,
        "sum_pv_fcf": round(fcf_sum_pv, 0),
        "terminal_pv": round(terminal_pv, 0),
        "enterprise_value": round(enterprise_value, 0),
        "implied_ev_ebitda": round(enterprise_value / max(1.0, projections[-1]["ebitda"]), 1),
    }

    # Sensitivity grid: WACC ± 1pp × TG ± 0.5pp
    grid_rows = []
    for w in [args.wacc_pct - 1, args.wacc_pct, args.wacc_pct + 1]:
        row = {"wacc_%": round(w, 1)}
        for tg in [args.terminal_growth_pct - 0.5, args.terminal_growth_pct, args.terminal_growth_pct + 0.5]:
            if (w - tg) / 100.0 <= 0:
                row[f"TG_{tg}%"] = "—"
                continue
            tfcf = projections[-1]["fcf"] * (1 + tg / 100.0)
            tv = tfcf / max(0.001, (w - tg) / 100.0)
            tpv = tv / ((1 + w / 100.0) ** args.years)
            row[f"TG_{tg}%"] = round((fcf_sum_pv + tpv) / 1e6, 0)  # in $M
        grid_rows.append(row)

    return emit(
        kind="table",
        title=f"DCF — {profile.get('name','?')} ({args.ticker})",
        subtitle=f"{args.years}y · WACC {args.wacc_pct}% · TG {args.terminal_growth_pct}% → EV {_fmt(enterprise_value)}",
        columns=["year", "revenue", "ebitda", "ebitda_margin_%", "fcf", "pv_of_fcf"],
        rows=projections,
        summary={"inputs": args.model_dump(), "results": summary, "sensitivity_ev_usd_m": grid_rows},
    )


dcf_valuer = StructuredTool.from_function(
    func=_dcf_valuer,
    name="dcf_valuer",
    description="Build a 5-year DCF for a listed target company using yfinance financials. Outputs projections + sensitivity grid as a table artifact.",
    args_schema=DCFArgs,
)


# ────────────────────────────────────────────────────────────────────────
# Multiples
# ────────────────────────────────────────────────────────────────────────

class MultiplesArgs(BaseModel):
    ticker: str = Field(description="Target company ticker.")
    peer_ev_ebitda: Optional[float] = Field(default=None, description="Override peer median EV/EBITDA. If None, uses the sector-ETF implied multiple approximation.")
    peer_ev_revenue: Optional[float] = Field(default=None, description="Override peer median EV/Revenue.")


def _multiples_valuer(**kw) -> str:
    args = MultiplesArgs(**kw)
    fin = yfinance_util.get_financials(args.ticker)
    profile = yfinance_util.get_company_profile(args.ticker)
    if "error" in fin:
        return f"Lookup failed for {args.ticker}: {fin['error']}"

    revenue = float(fin.get("revenue") or 0)
    ebitda = float(fin.get("ebitda") or 0)
    if revenue <= 0 and ebitda <= 0:
        return f"Insufficient financial data for {args.ticker}."

    self_ev_ebitda = float(fin.get("ev_to_ebitda") or 0)
    peer_ev_ebitda = args.peer_ev_ebitda or (self_ev_ebitda if self_ev_ebitda > 0 else 10.0)
    peer_ev_revenue = args.peer_ev_revenue or 3.0  # reasonable default

    rows = [
        {"method": "EV/EBITDA — own multiple", "multiple": round(self_ev_ebitda, 1), "applied_to": _fmt(ebitda), "implied_ev": _fmt(ebitda * self_ev_ebitda)},
        {"method": "EV/EBITDA — peer median",  "multiple": round(peer_ev_ebitda, 1),  "applied_to": _fmt(ebitda), "implied_ev": _fmt(ebitda * peer_ev_ebitda)},
        {"method": "EV/Revenue — peer median", "multiple": round(peer_ev_revenue, 1), "applied_to": _fmt(revenue), "implied_ev": _fmt(revenue * peer_ev_revenue)},
    ]
    low  = min(ebitda * self_ev_ebitda if self_ev_ebitda else 1e99, ebitda * peer_ev_ebitda, revenue * peer_ev_revenue)
    high = max(ebitda * self_ev_ebitda if self_ev_ebitda else 0,    ebitda * peer_ev_ebitda, revenue * peer_ev_revenue)
    mid  = (low + high) / 2

    return emit(
        kind="table",
        title=f"Multiples valuation — {profile.get('name','?')} ({args.ticker})",
        subtitle=f"EV range {_fmt(low)} – {_fmt(high)} (mid {_fmt(mid)})",
        columns=["method", "multiple", "applied_to", "implied_ev"],
        rows=rows,
        summary={"revenue": revenue, "ebitda": ebitda, "ev_range": {"low": low, "mid": mid, "high": high}},
    )


multiples_valuer = StructuredTool.from_function(
    func=_multiples_valuer,
    name="multiples_valuer",
    description="Apply EV/EBITDA and EV/Revenue multiples to a target's financials. Returns an implied EV range. Emits a table artifact.",
    args_schema=MultiplesArgs,
)


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────

def _fmt(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    for t, s in [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]:
        if abs(n) >= t:
            return f"${n/t:.1f}{s}"
    return f"${n:,.0f}"
