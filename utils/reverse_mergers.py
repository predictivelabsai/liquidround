"""Reverse-merger discovery, classification, persistence, and SPAC comparison.

SEDAR+ public pages are deliberately not automated: their public terms prohibit
scraping and database construction. Canadian records enter through reviewed
manual metadata or a future licensed provider adapter.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from urllib.parse import urlparse

TRANSACTION_TYPES = {
    "us_reverse_merger": "US reverse merger",
    "us_de_spac": "US de-SPAC",
    "ca_rto": "Canadian RTO",
    "ca_cpc_qt": "Canadian CPC qualifying transaction",
    "ca_spac_qa": "Canadian SPAC qualifying acquisition",
}


def classify_filing(text: str, *, company_name: str = "") -> dict:
    """Classify filing text using auditable regulatory and transaction signals."""
    lower = re.sub(r"\s+", " ", text or "").lower()
    signals: list[str] = []
    for item in ("1.01", "2.01", "5.01", "5.06", "9.01"):
        if re.search(rf"item\s+{re.escape(item)}\b", lower):
            signals.append(f"8-K Item {item}")
    shell_exit = any(p in lower for p in (
        "ceased to be a shell company", "change in shell company status",
        "no longer a shell company",
    ))
    de_spac = any(p in lower for p in (
        "special purpose acquisition company", "business combination agreement",
        "de-spac", "de spac", "redemption rights", "trust account",
    ))
    reverse = any(p in lower for p in (
        "reverse merger", "reverse acquisition", "share exchange agreement",
        "former shareholders of the private", "change of control",
    ))
    if shell_exit:
        signals.append("former shell disclosed")
    if de_spac:
        signals.append("SPAC/de-SPAC language")
    if reverse:
        signals.append("reverse-merger language")

    if de_spac and shell_exit:
        kind = "us_de_spac"
    elif shell_exit or (reverse and "8-K Item 5.06" in signals):
        kind = "us_reverse_merger"
    else:
        kind = "candidate"
    confidence = min(0.98, 0.35 + 0.09 * len(signals) + (0.18 if shell_exit else 0))
    risks = []
    if shell_exit:
        risks.append("former_shell_restrictions")
    if "8-K Item 9.01" not in signals and shell_exit:
        risks.append("financial_statements_not_detected")
    if de_spac:
        risks.append("redemption_and_sponsor_dilution")
    return {
        "transaction_type": kind,
        "signals": signals,
        "risk_flags": risks,
        "confidence": round(confidence, 3),
        "company_name": company_name,
    }


def candidate_from_edgar(result: dict, *, text: str = "") -> dict:
    analysis = classify_filing(text, company_name=result.get("entity_name", ""))
    accession = result.get("accession_number", "")
    url = result.get("file_url") or result.get("url", "")
    key_seed = accession or url
    return {
        "transaction_key": f"sec:{hashlib.sha1(key_seed.encode()).hexdigest()[:20]}",
        "jurisdiction": "US",
        "transaction_type": analysis["transaction_type"],
        "status": "completed" if "former shell disclosed" in analysis["signals"] else "candidate",
        "public_company": result.get("entity_name") or "Unknown SEC registrant",
        "announcement_date": result.get("filing_date") or None,
        "source_url": url,
        "source_type": result.get("form_type") or "SEC filing",
        "source_filing_id": accession,
        "risk_flags": analysis["risk_flags"],
        "confidence": analysis["confidence"],
        "metadata": {"signals": analysis["signals"]},
    }


def discover_edgar_candidates(years: int = 3, limit: int = 40) -> list[dict]:
    """Discover recent candidates from EDGAR and classify their primary filings."""
    from utils.edgar import get_filing_text, search_filings

    start = (date.today() - timedelta(days=365 * years)).isoformat()
    end = date.today().isoformat()
    queries = (
        '"Item 5.06" "shell company"',
        '"ceased to be a shell company"',
        '"reverse merger" "Item 2.01"',
    )
    seen: set[str] = set()
    records: list[dict] = []
    for query in queries:
        data = search_filings(query, forms="8-K", start_date=start, end_date=end, limit=40)
        for hit in data.get("results", []):
            filing_date = hit.get("filing_date", "")
            if filing_date and filing_date < start:
                continue
            key = hit.get("accession_number") or hit.get("file_url")
            if not key or key in seen:
                continue
            seen.add(key)
            try:
                text = get_filing_text(hit["file_url"], max_chars=120_000)
            except Exception:
                text = ""
            record = candidate_from_edgar(hit, text=text)
            if record["transaction_type"] != "candidate":
                records.append(record)
            if len(records) >= limit:
                return records
    return records


def validate_manual_record(data: dict) -> dict:
    """Validate a reviewed manual record without scraping its source URL."""
    jurisdiction = str(data.get("jurisdiction", "")).upper()
    if jurisdiction not in {"US", "CA"}:
        raise ValueError("Jurisdiction must be US or CA.")
    kind = str(data.get("transaction_type", ""))
    if kind not in TRANSACTION_TYPES:
        raise ValueError("Choose a supported transaction type.")
    public_company = str(data.get("public_company", "")).strip()
    source_url = str(data.get("source_url", "")).strip()
    if not public_company or not source_url:
        raise ValueError("Public company and source URL are required.")
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Source URL must be an HTTP(S) URL.")
    # SEDAR+ may be cited one record at a time, but the app never crawls or mirrors it.
    source_host = parsed.netloc.lower()
    source_type = "SEDAR+ manual citation" if "sedarplus" in source_host else "manual public source"
    key_seed = "|".join((jurisdiction, kind, public_company, source_url))
    return {
        "transaction_key": f"manual:{hashlib.sha1(key_seed.encode()).hexdigest()[:20]}",
        "jurisdiction": jurisdiction,
        "transaction_type": kind,
        "status": str(data.get("status", "candidate")),
        "public_company": public_company,
        "public_ticker": str(data.get("public_ticker", "")).strip() or None,
        "private_target": str(data.get("private_target", "")).strip() or None,
        "exchange": str(data.get("exchange", "")).strip() or None,
        "announcement_date": str(data.get("announcement_date", "")).strip() or None,
        "source_url": source_url,
        "source_type": source_type,
        "summary": str(data.get("summary", "")).strip() or None,
        "confidence": 1.0,
        "review_status": "reviewed",
        "risk_flags": [],
        "metadata": {"ingestion": "manual", "document_mirrored": False},
    }


def upsert_transactions(records: list[dict]) -> int:
    if not records:
        return 0
    from utils.database import get_conn
    sql = """
        INSERT INTO liquidround.reverse_merger_transactions
        (transaction_key,jurisdiction,transaction_type,status,public_company,
         public_ticker,public_cik,private_target,exchange,announcement_date,
         completion_date,deal_value,concurrent_financing,target_ownership_pct,
         source_url,source_type,source_filing_id,summary,risk_flags,confidence,
         review_status,metadata,last_verified_at,updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s::jsonb,%s,%s,%s::jsonb,NOW(),NOW())
        ON CONFLICT (transaction_key) DO UPDATE SET
          transaction_type=EXCLUDED.transaction_type,status=EXCLUDED.status,
          private_target=COALESCE(EXCLUDED.private_target,liquidround.reverse_merger_transactions.private_target),
          summary=COALESCE(EXCLUDED.summary,liquidround.reverse_merger_transactions.summary),
          risk_flags=EXCLUDED.risk_flags,confidence=EXCLUDED.confidence,
          metadata=EXCLUDED.metadata,last_verified_at=NOW(),updated_at=NOW()
    """
    columns = (
        "transaction_key","jurisdiction","transaction_type","status","public_company",
        "public_ticker","public_cik","private_target","exchange","announcement_date",
        "completion_date","deal_value","concurrent_financing","target_ownership_pct",
        "source_url","source_type","source_filing_id","summary",
    )
    count = 0
    with get_conn() as conn:
        cur = conn.cursor()
        for record in records:
            values = [record.get(c) for c in columns]
            values += [
                json.dumps(record.get("risk_flags", [])), record.get("confidence", .5),
                record.get("review_status", "unreviewed"),
                json.dumps(record.get("metadata", {})),
            ]
            cur.execute(sql, values)
            count += 1
        conn.commit()
    return count


def list_transactions(*, jurisdiction: str = "", kind: str = "", status: str = "",
                      query: str = "", limit: int = 250) -> list[dict]:
    from utils.database import get_conn
    clauses, params = [], []
    if jurisdiction:
        clauses.append("jurisdiction=%s"); params.append(jurisdiction)
    if kind:
        clauses.append("transaction_type=%s"); params.append(kind)
    if status:
        clauses.append("status=%s"); params.append(status)
    if query:
        clauses.append("(public_company ILIKE %s OR private_target ILIKE %s OR public_ticker ILIKE %s)")
        params.extend([f"%{query}%"] * 3)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    sql = f"""SELECT id,jurisdiction,transaction_type,status,public_company,
              public_ticker,private_target,exchange,announcement_date,deal_value,
              concurrent_financing,target_ownership_pct,source_url,source_type,
              summary,risk_flags,confidence,review_status
              FROM liquidround.reverse_merger_transactions{where}
              ORDER BY announcement_date DESC NULLS LAST, id DESC LIMIT %s"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            names = [d[0] for d in cur.description]
            return [dict(zip(names, row)) for row in cur.fetchall()]
    except Exception:
        return []


def combined_market_rows(limit: int = 250) -> list[dict]:
    """Return reverse mergers plus existing SPACs in a normalized comparison shape."""
    rows = list_transactions(limit=limit)
    try:
        from utils.spac_db import get_spac_data
        df = get_spac_data(limit=limit)
        for _, r in df.iterrows():
            rows.append({
                "id": f"spac:{r.get('spac_key')}",
                "jurisdiction": "US" if str(r.get("country", "")).lower() != "canada" else "CA",
                "transaction_type": "us_de_spac" if str(r.get("country", "")).lower() != "canada" else "ca_spac_qa",
                "status": r.get("status"),
                "public_company": r.get("company_name"),
                "public_ticker": r.get("ticker"),
                "private_target": r.get("target_name"),
                "exchange": r.get("exchange"),
                "announcement_date": r.get("da_date") or r.get("ipo_date"),
                "deal_value": r.get("deal_value"),
                "source_url": "",
                "source_type": "SPAC tracker",
                "confidence": 1,
                "review_status": "tracked",
            })
    except Exception:
        pass
    return rows
