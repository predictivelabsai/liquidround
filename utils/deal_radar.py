"""Daily M&A Deal Radar engine.

Pairs a PUBLIC buyer (validated to a live Yahoo Finance ticker) with a PRIVATE
Baltic target (liquidround.deal_candidates), scores the synergy fit with the
editable `deal_radar_synergy` prompt (5-bucket, 1-5, weighted composite), and
persists the top-N pairs of each run to liquidround.deal_radar_pairs.

Coverage rule: a pair is only scored when the buyer resolves to real Yahoo
financials AND the target has an estimated revenue in the DB ("fully-covered").
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date

log = logging.getLogger("deal_radar")

SLUG = "deal_radar_synergy"

BUYER_WATCHLIST = [
    # Vertical-market-software serial acquirers
    "CSU.TO", "TOI.V", "LMN.V", "VIT-B.ST", "ENGH.TO", "ROP",
    # Enterprise software / tech strategics
    "SAP", "SIE.DE", "NEM.DE",
    # Fintech / payments
    "ADYEN.AS", "NEXI.MI", "WISE.L", "PYPL",
    # Industrials / logistics / cleantech
    "ABB", "DSV.CO", "VWS.CO", "KNEBV.HE",
]

DEFAULT_WEIGHTS = {
    "cost_operational": 35, "revenue": 25, "strategic": 20,
    "financial": 10, "organizational": 10,
}


# ── prompt (uses the user-edited version when present) ──────────────────────

def load_scoring_prompt() -> str:
    """Latest edited prompt from liquidround.prompt_versions, else the .md file."""
    try:
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT content FROM liquidround.prompt_versions WHERE slug = %s "
                "ORDER BY id DESC LIMIT 1", (SLUG,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
    except Exception:
        pass
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "prompts" / "system" / f"{SLUG}.md"
    return p.read_text() if p.exists() else ""


def _llm(temperature: float = 0.3):
    from utils.config import config
    from utils.llm_factory import create_llm
    return create_llm(provider=config.default_provider, temperature=temperature)


# ── buyers (public, Yahoo-validated) ────────────────────────────────────────

_BUYER_CACHE: dict[str, dict | None] = {}


def buyer_info(ticker: str) -> dict | None:
    """Resolve a ticker to a real public company with financials, or None."""
    key = ticker.upper()
    if key in _BUYER_CACHE:
        return _BUYER_CACHE[key]
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        mktcap = info.get("marketCap")
        name = info.get("shortName") or info.get("longName")
        if not mktcap or not name:
            _BUYER_CACHE[key] = None
            return None
        result = {
            "ticker": key,
            "name": name,
            "exchange": info.get("exchange") or info.get("fullExchangeName") or "",
            "country": info.get("country") or "",
            "sector": info.get("sector") or "",
            "industry": info.get("industry") or "",
            "mktcap_usd": float(mktcap),
            "revenue": info.get("totalRevenue"),
            "ebitda": info.get("ebitda"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "currency": info.get("financialCurrency") or info.get("currency") or "",
        }
        _BUYER_CACHE[key] = result
        return result
    except Exception as e:
        log.debug("buyer_info failed for %s: %s", ticker, e)
        return None


def _propose_buyer_tickers(target: dict, n: int = 4) -> list[str]:
    """Ask the LLM for likely PUBLIC acquirer tickers for this target."""
    prompt = (
        f"Target (private, {target.get('country')}): {target.get('company_name')}\n"
        f"Sector: {target.get('sector')}\n"
        f"Description: {target.get('description')}\n"
        f"Deal context: {target.get('deal_context')}\n\n"
        f"List up to {n} PUBLICLY LISTED companies (any country) that would be the "
        "most logical strategic acquirers of this target. Prefer companies active "
        "in the Baltics/Nordics/Europe or serial acquirers in this sector. Return "
        "ONLY a JSON array of Yahoo Finance ticker symbols (with exchange suffix "
        'where needed, e.g. "SAP", "CSU.TO", "VIT-B.ST", "ADYEN.AS"). No prose.'
    )
    try:
        raw = _llm(0.4).invoke(prompt).content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        tickers = json.loads(m.group() if m else raw)
        return [str(t).strip().upper() for t in tickers if str(t).strip()][:n]
    except Exception as e:
        log.debug("propose buyers failed: %s", e)
        return []


def candidate_buyers(target: dict, per_target: int = 3) -> list[dict]:
    """Yahoo-validated public buyers for a target: LLM-proposed + watchlist."""
    seen, out = set(), []
    for tk in _propose_buyer_tickers(target) + BUYER_WATCHLIST:
        tk = tk.upper()
        if tk in seen:
            continue
        seen.add(tk)
        info = buyer_info(tk)
        if info:
            out.append(info)
        if len(out) >= per_target:
            break
    return out


# ── scoring ─────────────────────────────────────────────────────────────────

def _band(score: float) -> str:
    if score >= 4.5:
        return "Excellent — strong deal rationale"
    if score >= 3.5:
        return "Solid — pursue with focused integration plan"
    if score >= 2.5:
        return "Marginal — deep scrutiny or lower premium"
    return "High risk — reconsider or walk away"


def score_pair(buyer: dict, target: dict, scoring_prompt: str | None = None) -> dict | None:
    """Score one public-buyer ↔ private-target pair. Returns a pair record."""
    system = scoring_prompt or load_scoring_prompt()
    rev = target.get("estimated_revenue_eur")
    ctx = (
        f"BUYER (public): {buyer['name']} ({buyer['ticker']})\n"
        f"  exchange={buyer['exchange']} country={buyer['country']} "
        f"sector={buyer['sector']} industry={buyer['industry']}\n"
        f"  market_cap_usd={buyer['mktcap_usd']:.0f} revenue={buyer.get('revenue')} "
        f"ebitda={buyer.get('ebitda')} ev/ebitda={buyer.get('ev_ebitda')}\n\n"
        f"TARGET (private, Baltics): {target.get('company_name')} ({target.get('country')})\n"
        f"  sector={target.get('sector')}\n"
        f"  description={target.get('description')}\n"
        f"  deal_context={target.get('deal_context')}\n"
        f"  estimated_revenue_eur={rev}\n\n"
        "Score this specific buyer↔target pair per the methodology. Return ONLY the JSON."
    )
    try:
        raw = _llm(0.3).invoke(f"{system}\n\n{ctx}").content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group() if m else raw)
    except Exception as e:
        log.warning("score_pair parse failed for %s+%s: %s",
                    buyer["ticker"], target.get("company_name"), e)
        return None

    buckets = data.get("buckets", {}) or {}
    num = den = 0.0
    for k, spec in buckets.items():
        try:
            s = float(spec.get("score"))
            w = float(spec.get("weight", DEFAULT_WEIGHTS.get(k, 0)))
        except (TypeError, ValueError):
            continue
        num += s * w
        den += w
    composite = round(num / den, 2) if den else None
    if composite is None:
        try:
            composite = round(float(data.get("composite_score")), 2)
        except (TypeError, ValueError):
            return None
    composite = max(1.0, min(5.0, composite))

    return {
        "buyer_name": buyer["name"], "buyer_ticker": buyer["ticker"],
        "buyer_exchange": buyer["exchange"], "buyer_country": buyer["country"],
        "buyer_mktcap_usd": buyer["mktcap_usd"],
        "target_name": target.get("company_name"), "target_country": target.get("country"),
        "target_sector": target.get("sector"), "target_revenue_eur": rev,
        "composite_score": composite,
        "recommendation": data.get("recommendation") or _band(composite),
        "bucket_scores": buckets,
        "reasoning": data.get("reasoning", ""),
    }


# ── pipeline ────────────────────────────────────────────────────────────────

def _fully_covered_targets(limit: int, country: str | None = None) -> list[dict]:
    from utils.database import get_conn
    from psycopg2.extras import RealDictCursor
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        where_country = "AND country = %s" if country else ""
        params = ([country, limit] if country else [limit])
        cur.execute(f"""
            SELECT company_name, country, sector, description, deal_context,
                   deal_size_estimate, estimated_revenue_eur
            FROM liquidround.deal_candidates
            WHERE COALESCE(is_active, TRUE) = TRUE
              AND estimated_revenue_eur BETWEEN 100000 AND 5000000000
              AND company_name !~* '(filiaal|filialas|\\mbranch\\M|representative office)'
              {where_country}
            ORDER BY estimated_revenue_eur DESC
            LIMIT %s
        """, params)
        return [dict(r) for r in cur.fetchall()]


def _radar_countries() -> list[str]:
    from utils.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT country FROM liquidround.deal_candidates
                       WHERE COALESCE(is_active,TRUE) AND estimated_revenue_eur >= 100000
                       GROUP BY country ORDER BY count(*) DESC""")
        return [r[0] for r in cur.fetchall()]


def build_deal_radar(per_country: int = 3, targets_per_country: int = 4,
                     buyers_per_target: int = 3, persist: bool = True,
                     countries: list[str] | None = None) -> list[dict]:
    """Score buyer↔target pairs and keep the top `per_country` PER COUNTRY."""
    scoring_prompt = load_scoring_prompt()
    countries = countries or _radar_countries()
    all_pairs: list[dict] = []
    for country in countries:
        targets = _fully_covered_targets(targets_per_country, country=country)
        cpairs: list[dict] = []
        for t in targets:
            for b in candidate_buyers(t, per_target=buyers_per_target):
                p = score_pair(b, t, scoring_prompt)
                if p:
                    cpairs.append(p)
        cpairs.sort(key=lambda p: p["composite_score"], reverse=True)
        kept = cpairs[:per_country]
        log.info("Deal Radar [%s]: %d pairs scored → keep %d", country, len(cpairs), len(kept))
        all_pairs.extend(kept)

    all_pairs.sort(key=lambda p: p["composite_score"], reverse=True)
    for i, p in enumerate(all_pairs, 1):
        p["rank"] = i

    if persist and all_pairs:
        _persist(all_pairs)
    return all_pairs


def _persist(pairs: list[dict]) -> None:
    from utils.database import get_conn
    today = date.today()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM liquidround.deal_radar_pairs WHERE run_date = %s", (today,))
        for p in pairs:
            cur.execute("""
                INSERT INTO liquidround.deal_radar_pairs
                  (run_date, rank, buyer_name, buyer_ticker, buyer_exchange, buyer_country,
                   buyer_mktcap_usd, target_name, target_country, target_sector,
                   target_revenue_eur, composite_score, recommendation, bucket_scores, reasoning)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (today, p["rank"], p["buyer_name"], p["buyer_ticker"], p["buyer_exchange"],
                  p["buyer_country"], p["buyer_mktcap_usd"], p["target_name"],
                  p["target_country"], p["target_sector"], p["target_revenue_eur"],
                  p["composite_score"], p["recommendation"],
                  json.dumps(p["bucket_scores"]), p["reasoning"]))


def get_latest_pairs(limit: int = 20) -> list[dict]:
    """Most-recent run's ranked pairs."""
    from utils.database import get_conn
    from psycopg2.extras import RealDictCursor
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM liquidround.deal_radar_pairs
            WHERE run_date = (SELECT MAX(run_date) FROM liquidround.deal_radar_pairs)
            ORDER BY rank LIMIT %s
        """, (limit,))
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            if isinstance(d.get("bucket_scores"), str):
                try:
                    d["bucket_scores"] = json.loads(d["bucket_scores"])
                except Exception:
                    d["bucket_scores"] = {}
            rows.append(d)
        return rows


# ── featured agent rotation ─────────────────────────────────────────────────

def featured_agent(seed: str | None = None) -> dict | None:
    """Pick one agent from the registry (deterministic per day) with its prompt."""
    try:
        from agents.registry import all_agents
        agents = list(all_agents())
    except Exception:
        return None
    if not agents:
        return None
    import hashlib
    seed = seed or date.today().isoformat()
    idx = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16) % len(agents)
    a = agents[idx]
    prompt = ""
    try:
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT content FROM liquidround.prompt_versions WHERE slug=%s "
                        "ORDER BY id DESC LIMIT 1", (a.slug,))
            row = cur.fetchone()
            if row and row[0]:
                prompt = row[0]
    except Exception:
        pass
    if not prompt:
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "prompts" / "system" / f"{a.slug}.md"
        prompt = p.read_text() if p.exists() else ""
    return {"slug": a.slug, "name": a.name, "one_liner": a.one_liner,
            "description": a.description, "category": a.category, "prompt": prompt}
