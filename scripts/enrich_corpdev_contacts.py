"""Corp-dev contact enricher spike.

Pulls candidate decision-makers for listed buyers (default: BUYER_WATCHLIST
plus US/CA SaaS serial-acquirer list) from Companies House (.L), EDGAR (US),
or low-confidence heuristic stubs when keys/APIs are unavailable.

Usage:
    python -m scripts.enrich_corpdev_contacts --dry-run --limit 10
    python -m scripts.enrich_corpdev_contacts --tickers SAP,WISE.L,CRM --dry-run
    python -m scripts.enrich_corpdev_contacts --tickers CRM,NOW --limit 5
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("enrich_corpdev_contacts")

ROOT = Path(__file__).resolve().parents[1]

# Heuristic titles when filings APIs are unavailable (source=llm_web, low conf).
_STUB_TITLES = (
    ("Head of Corporate Development", "corp_dev", "Head"),
    ("VP Corporate Development", "corp_dev", "VP"),
    ("Head of M&A", "mna", "Head"),
    ("VP Strategy & Corporate Development", "strategy", "VP"),
)

# US/CA SaaS serial acquirers & strategics (beyond European BUYER_WATCHLIST).
SAAS_BUYER_WATCHLIST_US_CA: list[str] = [
    "CRM", "NOW", "ADBE", "INTU", "WDAY", "TEAM", "SNOW", "DDOG",
    "NET", "ZM", "OKTA", "HUBS",
    "SHOP.TO", "OTEX.TO", "DSGX.TO",
    "CSU.TO", "TOI.V", "LMN.V", "ENGH.TO",
    "ROP", "PYPL",
]


def _load_watchlist_file() -> list[str]:
    path = ROOT / "data" / "saas_buyer_watchlist_us_ca.txt"
    if not path.is_file():
        return list(SAAS_BUYER_WATCHLIST_US_CA)
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line.upper())
    return out or list(SAAS_BUYER_WATCHLIST_US_CA)


def default_tickers() -> list[str]:
    """Union of Deal Radar BUYER_WATCHLIST + US/CA SaaS list (deduped, order preserved)."""
    from utils.deal_radar import BUYER_WATCHLIST

    seen: set[str] = set()
    out: list[str] = []
    for tk in list(BUYER_WATCHLIST) + _load_watchlist_file():
        u = tk.upper().strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _geo_for_ticker(ticker: str) -> str:
    t = ticker.upper()
    if t.endswith(".L"):
        return "GB"
    if t.endswith((".TO", ".V", ".CN")):
        return "CA"
    if t.endswith((".DE", ".AS", ".MI", ".PA", ".HE", ".ST", ".CO")):
        return "EU"
    return "US"


def _sector_tag(ticker: str) -> str:
    saas = {
        "CRM", "NOW", "ADBE", "INTU", "WDAY", "TEAM", "SNOW", "DDOG", "NET",
        "ZM", "OKTA", "HUBS", "SHOP.TO", "OTEX.TO", "DSGX.TO", "CSU.TO",
        "TOI.V", "LMN.V", "ENGH.TO", "SAP", "ROP", "PYPL",
    }
    return "saas" if ticker.upper() in saas else "other"


def _stub_candidates(ticker: str) -> list[dict[str, Any]]:
    geo = _geo_for_ticker(ticker)
    sector = _sector_tag(ticker)
    out: list[dict[str, Any]] = []
    for title, role_family, seniority in _STUB_TITLES[:2]:
        out.append({
            "ticker": ticker,
            "full_name": f"[Unknown] {title} @ {ticker}",
            "title": title,
            "role_family": role_family,
            "seniority": seniority,
            "email": None,
            "email_status": "unknown",
            "phone": None,
            "linkedin_url": None,
            "location": geo,
            "source": "llm_web",
            "source_url": None,
            "source_date": date.today().isoformat(),
            "confidence": 0.15,
            "is_primary_corpdev": role_family == "corp_dev",
            "metadata": {
                "geo": geo,
                "sector": sector,
                "heuristic": True,
                "note": "Stub title — replace via Sales Nav paste or filings enrich",
            },
        })
    return out


def _from_companies_house(ticker: str) -> list[dict[str, Any]]:
    """UK .L tickers → Companies House officers when API key present."""
    if not ticker.upper().endswith(".L"):
        return []
    api_key = os.getenv("COMPANIES_HOUSE_API_KEY") or os.getenv("CH_API_KEY")
    if not api_key:
        log.info("No COMPANIES_HOUSE_API_KEY — skipping CH for %s", ticker)
        return []
    try:
        from utils.companies_house_api import CompaniesHouseAPI
    except Exception as exc:  # pragma: no cover
        log.warning("companies_house_api import failed: %s", exc)
        return []

    query = ticker.split(".")[0]
    try:
        client = CompaniesHouseAPI(api_key=api_key)
        companies = client.search_companies(query, items_per_page=5) or []
        if not companies:
            return []
        company_number = companies[0].get("company_number")
        if not company_number:
            return []
        officers = client.get_officers(company_number) or []
    except Exception as exc:
        log.warning("Companies House lookup failed for %s: %s", ticker, exc)
        return []

    corpdev_roles = ("director", "corporate", "secretary", "ceo", "cfo")
    out: list[dict[str, Any]] = []
    for off in officers[:15]:
        role = (getattr(off, "role", None) or "").lower()
        name = getattr(off, "name", None) or ""
        if not name:
            continue
        if getattr(off, "resigned_on", None):
            continue
        role_family = "board"
        if any(k in role for k in ("chief executive", "ceo")):
            role_family = "ceo"
        elif any(k in role for k in ("chief financial", "cfo", "finance")):
            role_family = "cfo"
        elif "corporate" in role or "development" in (getattr(off, "occupation", None) or "").lower():
            role_family = "corp_dev"
        elif role not in corpdev_roles and "director" not in role:
            continue
        out.append({
            "ticker": ticker,
            "full_name": name.title() if name.isupper() else name,
            "title": getattr(off, "role", None) or "Director",
            "role_family": role_family,
            "seniority": "Director",
            "email": None,
            "email_status": "unknown",
            "phone": None,
            "linkedin_url": None,
            "location": "GB",
            "source": "companies_house",
            "source_url": f"https://find-and-update.company-information.service.gov.uk/company/{company_number}/officers",
            "source_date": getattr(off, "appointed_on", None) or date.today().isoformat(),
            "confidence": 0.55,
            "is_primary_corpdev": role_family == "corp_dev",
            "metadata": {
                "geo": "GB",
                "sector": _sector_tag(ticker),
                "company_number": company_number,
                "occupation": getattr(off, "occupation", None),
            },
        })
    return out


def _from_edgar(ticker: str) -> list[dict[str, Any]]:
    """US tickers → EDGAR company submissions / officer hints when available."""
    if "." in ticker and not ticker.upper().endswith(".US"):
        # Non-US exchange suffixes — skip EDGAR
        suffix = ticker.split(".")[-1].upper()
        if suffix not in ("US",):
            return []
    try:
        from utils import edgar
    except Exception as exc:
        log.info("edgar unavailable: %s", exc)
        return []

    try:
        cik = edgar.ticker_to_cik(ticker)
        if not cik:
            return []
        # Prefer submissions JSON for company name; DEF 14A officer parse is deferred.
        # Surface a low/medium confidence IR/corp-dev placeholder tied to CIK.
        name = None
        try:
            subs = edgar._get(  # noqa: SLF001 — reuse client throttle
                f"https://data.sec.gov/submissions/CIK{cik}.json"
            ).json()
            name = subs.get("name")
        except Exception:
            pass
        geo = "US"
        base = {
            "ticker": ticker,
            "email": None,
            "email_status": "unknown",
            "phone": None,
            "linkedin_url": None,
            "location": geo,
            "source": "edgar_def14a",
            "source_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=DEF+14A",
            "source_date": date.today().isoformat(),
            "confidence": 0.35,
            "metadata": {
                "geo": geo,
                "sector": _sector_tag(ticker),
                "cik": cik,
                "issuer_name": name,
                "note": "CIK resolved; DEF 14A officer parse is a follow-on — paste Sales Nav for names",
            },
        }
        return [
            {
                **base,
                "full_name": f"[EDGAR] Corp Dev contact @ {ticker}",
                "title": "Corporate Development (see DEF 14A)",
                "role_family": "corp_dev",
                "seniority": "Unknown",
                "is_primary_corpdev": True,
            },
            {
                **base,
                "full_name": f"[EDGAR] Investor Relations @ {ticker}",
                "title": "Investor Relations",
                "role_family": "ir",
                "seniority": "Unknown",
                "is_primary_corpdev": False,
                "confidence": 0.30,
            },
        ]
    except Exception as exc:
        log.warning("EDGAR enrich failed for %s: %s", ticker, exc)
        return []


def enrich_ticker(ticker: str) -> list[dict[str, Any]]:
    ticker = ticker.upper().strip()
    candidates: list[dict[str, Any]] = []
    if ticker.endswith(".L"):
        candidates.extend(_from_companies_house(ticker))
    else:
        candidates.extend(_from_edgar(ticker))
    if not candidates:
        candidates.extend(_stub_candidates(ticker))
    return candidates


def upsert_contacts(candidates: list[dict[str, Any]]) -> int:
    from utils.database import get_conn
    from psycopg2.extras import Json

    upserted = 0
    with get_conn() as conn:
        cur = conn.cursor()
        for c in candidates:
            meta = Json(c.get("metadata") or {})
            cur.execute(
                """
                SELECT id FROM liquidround.corpdev_contacts
                WHERE ticker = %s
                  AND lower(full_name) = lower(%s)
                  AND lower(COALESCE(title, '')) = lower(COALESCE(%s, ''))
                LIMIT 1
                """,
                (c["ticker"], c["full_name"], c.get("title")),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    """
                    UPDATE liquidround.corpdev_contacts SET
                        role_family = %s,
                        seniority = %s,
                        email = COALESCE(%s, email),
                        email_status = %s,
                        phone = COALESCE(%s, phone),
                        linkedin_url = COALESCE(%s, linkedin_url),
                        location = COALESCE(%s, location),
                        source = %s,
                        source_url = %s,
                        source_date = %s,
                        confidence = GREATEST(COALESCE(confidence, 0), COALESCE(%s, 0)),
                        metadata = metadata || %s,
                        is_primary_corpdev = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        c["role_family"], c.get("seniority"), c.get("email"),
                        c.get("email_status", "unknown"), c.get("phone"),
                        c.get("linkedin_url"), c.get("location"),
                        c["source"], c.get("source_url"), c.get("source_date"),
                        c.get("confidence"), meta, c.get("is_primary_corpdev", False),
                        row[0],
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO liquidround.corpdev_contacts (
                        ticker, full_name, title, role_family, seniority,
                        email, email_status, phone, linkedin_url, location,
                        source, source_url, source_date, confidence, metadata,
                        is_primary_corpdev
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s
                    )
                    """,
                    (
                        c["ticker"], c["full_name"], c.get("title"),
                        c["role_family"], c.get("seniority"),
                        c.get("email"), c.get("email_status", "unknown"),
                        c.get("phone"), c.get("linkedin_url"), c.get("location"),
                        c["source"], c.get("source_url"), c.get("source_date"),
                        c.get("confidence"), meta, c.get("is_primary_corpdev", False),
                    ),
                )
            upserted += 1
    return upserted


def log_enrichment_run(
    tickers: list[str],
    candidates: list[dict[str, Any]],
    upserted: int,
    dry_run: bool,
    status: str = "completed",
    error_message: str | None = None,
) -> None:
    if dry_run:
        return
    try:
        from utils.database import get_conn
        from psycopg2.extras import Json
        from collections import Counter

        mix = dict(Counter(c["source"] for c in candidates))
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO liquidround.contact_enrichment_runs (
                    tickers, source_mix, contacts_found, contacts_upserted,
                    dry_run, status, error_message, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tickers, Json(mix), len(candidates), upserted,
                    False, status, error_message,
                    Json({"at": datetime.now(timezone.utc).isoformat()}),
                ),
            )
    except Exception as exc:
        log.warning("Could not log enrichment run: %s", exc)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Enrich corp-dev contacts for listed buyers")
    p.add_argument("--tickers", type=str, default="",
                   help="Comma-separated tickers (default: BUYER_WATCHLIST ∪ US/CA SaaS list)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print JSON candidates; no DB writes")
    p.add_argument("--limit", type=int, default=0,
                   help="Max tickers to process (0 = all)")
    args = p.parse_args(argv)

    if args.tickers.strip():
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = default_tickers()
    if args.limit and args.limit > 0:
        tickers = tickers[: args.limit]

    all_candidates: list[dict[str, Any]] = []
    for tk in tickers:
        found = enrich_ticker(tk)
        all_candidates.extend(found)
        log.info("%s → %d candidate(s)", tk, len(found))

    if args.dry_run:
        print(json.dumps({
            "dry_run": True,
            "tickers": tickers,
            "count": len(all_candidates),
            "candidates": all_candidates,
        }, indent=2, default=str))
        return 0

    try:
        upserted = upsert_contacts(all_candidates)
        log_enrichment_run(tickers, all_candidates, upserted, dry_run=False)
        print(json.dumps({
            "dry_run": False,
            "tickers": tickers,
            "found": len(all_candidates),
            "upserted": upserted,
        }, indent=2))
        return 0
    except Exception as exc:
        log.error("DB upsert failed: %s", exc)
        log_enrichment_run(tickers, all_candidates, 0, dry_run=False,
                           status="failed", error_message=str(exc))
        # Still exit non-zero so CI/operators notice; dry-run path never hits this.
        print(json.dumps({"error": str(exc), "found": len(all_candidates)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
