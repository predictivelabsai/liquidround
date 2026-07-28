"""Reverse-merger discovery, classification, persistence, and SPAC comparison.

US records are discovered from SEC EDGAR. Canadian records now enter through two
paths: (a) the SEDAR+ Playwright scraper in ``utils/sedarplus.py`` which crawls
the public sedarplus.ca document search and parses downloaded PDFs through the
same ``filing_intelligence`` pipeline as EDGAR filings, and (b) the reviewed
manual-import form for one-off citations. The SEDAR+ scraper respects the
public search UI, stores only metadata + a content hash (never a mirrored copy
of the document), and tags every record with ``ingestion='sedarplus_scraper'``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, timedelta
from urllib.parse import urlparse

log = logging.getLogger(__name__)

TRANSACTION_TYPES = {
    "us_reverse_merger": "US reverse merger",
    "us_de_spac": "US de-SPAC",
    "ca_rto": "Canadian RTO",
    "ca_cpc_qt": "Canadian CPC qualifying transaction",
    "ca_spac_qa": "Canadian SPAC qualifying acquisition",
}

_MONEY_MULTIPLIERS = {
    "billion": 1_000_000_000,
    "million": 1_000_000,
    "thousand": 1_000,
}


def extract_transaction_terms(text: str, *, public_company: str = "") -> dict:
    """Extract conservative target, value, and closing signals from filing text."""
    clean = re.sub(r"\s+", " ", text or "")
    target = None
    legal_name = (
        r"[A-Z][A-Za-z0-9&,'’() .-]{1,75}?"
        r"(?:Inc\.?|Incorporated|Corp\.?|Corporation|LLC|L\.L\.C\.|"
        r"Ltd\.?|Limited|Co\.)"
    )
    target_patterns = (
        r"(?:acquisition|combination|merger|share exchange)\s+(?:of|with)\s+"
        rf"({legal_name})(?=,?\s+(?:a |an |the |pursuant|for |which |and |\())",
        r"(?:target company|acquired company|private company)\s+(?:is|was|named)\s+"
        rf"({legal_name})(?=[.;,])",
    )
    for pattern in target_patterns:
        match = re.search(pattern, clean, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" ,;:-")
            exact_names = re.findall(legal_name, candidate)
            if exact_names:
                candidate = exact_names[-1].strip(" ,;:-")
            if candidate and candidate.lower() != (public_company or "").lower():
                target = candidate
                break

    value = None
    value_match = re.search(
        r"(?:transaction value|valued at|aggregate consideration|purchase price|"
        r"\b(?:acquire|acquisition|merger)\b.{0,100}?\bfor)"
        r"(?:\s+(?:of|is|was|approximately|about))*\s*"
        r"\$\s*([0-9][0-9,.]*)\s*(billion|million|thousand|bn|mm|m)?\b",
        clean,
        re.IGNORECASE,
    )
    if value_match:
        amount = float(value_match.group(1).replace(",", ""))
        unit = (value_match.group(2) or "").lower()
        multiplier = _MONEY_MULTIPLIERS.get(
            unit, 1_000_000_000 if unit == "bn" else 1_000_000 if unit in {"mm", "m"} else 1
        )
        value = amount * multiplier

    completed = any(re.search(pattern, clean, re.IGNORECASE) for pattern in (
        r"\b(?:completed|consummated|closed)\s+(?:the|its|our)\s+"
        r"(?:reverse merger|merger|acquisition|business combination|share exchange)\b",
        r"\bclosing of the (?:merger|acquisition|business combination|share exchange)\b",
        r"\bceased to be a shell company\b",
        r"\bno longer a shell company\b",
    ))
    announced = any(re.search(pattern, clean, re.IGNORECASE) for pattern in (
        r"\bentered into (?:a|the) (?:definitive )?(?:merger|share exchange|business combination) agreement\b",
        r"\bannounced (?:a|the) (?:proposed )?(?:merger|acquisition|business combination)\b",
    ))
    return {
        "private_target": target,
        "deal_value": value,
        "completed": completed,
        "announced": announced,
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
        "special purpose acquisition company", "blank check company",
        "de-spac", "de spac", "redemption rights", "trust account",
        "sponsor promote",
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

    transaction_items = {"8-K Item 1.01", "8-K Item 2.01", "8-K Item 5.01", "8-K Item 5.06"}
    if de_spac:
        kind = "us_de_spac"
    elif shell_exit or (reverse and transaction_items.intersection(signals)):
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
    terms = extract_transaction_terms(text, public_company=result.get("entity_name", ""))
    accession = result.get("accession_number", "")
    url = result.get("file_url") or result.get("url", "")
    key_seed = accession or url
    return {
        "transaction_key": f"sec:{hashlib.sha1(key_seed.encode()).hexdigest()[:20]}",
        "jurisdiction": "US",
        "transaction_type": analysis["transaction_type"],
        "status": "completed" if terms["completed"] else "announced" if terms["announced"] else "candidate",
        "public_company": result.get("entity_name") or "Unknown SEC registrant",
        "private_target": terms["private_target"],
        "announcement_date": result.get("filing_date") or None,
        "completion_date": result.get("filing_date") if terms["completed"] else None,
        "deal_value": terms["deal_value"],
        "source_url": url,
        "source_type": result.get("form_type") or "SEC filing",
        "source_filing_id": accession,
        "risk_flags": analysis["risk_flags"],
        "confidence": analysis["confidence"],
        "metadata": {"signals": analysis["signals"], "extraction": "filing_text_v2"},
    }


def classify_sedar_filing(text: str, *, document_name: str = "",
                          company_name: str = "") -> dict:
    """Classify a SEDAR+ document using Canadian RTO/CPC/SPAC-QA signals.

    Mirrors ``classify_filing`` but keys on Canadian transaction language
    rather than SEC 8-K items. Returns the same shape so downstream code can
    treat US and CA records uniformly.
    """
    lower = re.sub(r"\s+", " ", (text or "")).lower()
    doc_lower = (document_name or "").lower()
    signals: list[str] = []

    rto = any(p in lower for p in (
        "reverse takeover", "reverse acquisition", "reverse merger",
        "backdoor listing", "back-door listing", "share exchange agreement",
    )) or "reverse takeover" in doc_lower
    cpc = any(p in lower for p in (
        "qualifying transaction", "capital pool company",
    )) or "qualifying transaction" in doc_lower or "capital pool" in doc_lower
    spac_qa = any(p in lower for p in (
        "special purpose acquisition", "qualifying acquisition",
        "spac qualifying acquisition",
    )) or "qualifying acquisition" in doc_lower
    material_change = "material change report" in doc_lower or "material change" in lower
    completed = any(p in lower for p in (
        "completed the", "completed its", "closed the", "closed its",
        "closing of the", "consummated",
        "the reverse takeover is complete", "effective date of the",
    ))

    if rto:
        signals.append("reverse-takeover language")
    if cpc:
        signals.append("CPC qualifying-transaction language")
    if spac_qa:
        signals.append("SPAC qualifying-acquisition language")
    if material_change:
        signals.append("material change report")
    if completed:
        signals.append("completion language")

    if spac_qa:
        kind = "ca_spac_qa"
    elif cpc:
        kind = "ca_cpc_qt"
    elif rto:
        kind = "ca_rto"
    else:
        kind = "candidate"
    confidence = min(0.98, 0.40 + 0.10 * len(signals) + (0.15 if completed else 0))
    risks: list[str] = []
    if not completed and kind != "candidate":
        risks.append("completion_not_confirmed")
    if "financial statements" not in lower and kind in {"ca_rto", "ca_cpc_qt"}:
        risks.append("financial_statements_not_detected")
    return {
        "transaction_type": kind,
        "signals": signals,
        "risk_flags": risks,
        "confidence": round(confidence, 3),
        "company_name": company_name,
        "completed": completed,
    }


def candidate_from_sedar(document: dict, *, text: str = "") -> dict:
    """Build a CA transaction record from a SEDAR+ search hit + parsed text.

    Parallel to ``candidate_from_edgar``. ``document`` is a SEDAR+ row dict
    (profile_name, profile_number, document_name, submitted_date,
    jurisdiction, download_url).
    """
    matched_query = document.get("matched_query", "")
    evidence_text = "\n".join(part for part in (text, matched_query) if part)
    analysis = classify_sedar_filing(
        evidence_text, document_name=document.get("document_name", ""),
        company_name=document.get("profile_name", ""),
    )
    terms = extract_transaction_terms(text, public_company=document.get("profile_name", ""))
    resource_url = document.get("download_url") or document.get("source_url") or ""
    profile_number = document.get("profile_number", "")
    url = (
        f"https://www.sedarplus.ca/csa-party/{profile_number}.html?_locale=en"
        if profile_number else resource_url
    )
    key_seed = profile_number or resource_url or document.get("document_name", "")
    status = "completed" if analysis["completed"] else "announced" if terms["announced"] else "candidate"
    return {
        "transaction_key": f"sedar:{hashlib.sha1(key_seed.encode()).hexdigest()[:20]}",
        "jurisdiction": "CA",
        "transaction_type": analysis["transaction_type"],
        "status": status,
        "public_company": document.get("profile_name") or "Unknown SEDAR+ issuer",
        "public_ticker": None,
        "private_target": terms["private_target"],
        "exchange": _infer_exchange(document.get("jurisdiction", "")),
        "announcement_date": document.get("submitted_date") or None,
        "completion_date": document.get("submitted_date") if analysis["completed"] else None,
        "deal_value": terms["deal_value"],
        "source_url": url,
        "source_type": "SEDAR+",
        "source_filing_id": profile_number or None,
        "risk_flags": analysis["risk_flags"],
        "confidence": analysis["confidence"],
        "review_status": "unreviewed",
        "metadata": {
            "signals": analysis["signals"],
            "ingestion": "sedarplus_scraper",
            "document_mirrored": False,
            "document_name": document.get("document_name", ""),
            "profile_number": profile_number,
            "principal_jurisdiction": document.get("jurisdiction", ""),
            "file_size": document.get("file_size", ""),
            "extraction": "sedar_text_v1",
            "matched_query": matched_query,
            "document_text_available": bool(text),
            "resource_url": resource_url,
        },
    }


def _infer_exchange(jurisdiction: str) -> str | None:
    """Best-effort TSX/TSXV/CSE inference from a SEDAR+ principal jurisdiction."""
    j = (jurisdiction or "").lower()
    if "venture" in j or "tsxv" in j:
        return "TSXV"
    if "cse" in j or "canadian securities" in j:
        return "CSE"
    if "tsx" in j or "ontario" in j or "toronto" in j:
        return "TSX"
    if "cboe" in j or "alpha" in j:
        return "Cboe Canada"
    return None


def discover_sedarplus_candidates(days: int = 365, limit: int = 40,
                                 *, headless: bool = True) -> list[dict]:
    """Discover recent Canadian reverse-merger candidates from SEDAR+.

    Drives the Playwright scraper in ``utils.sedarplus`` to find RTO / CPC-QT /
    SPAC-QA documents, downloads each, parses via ``filing_intelligence``, and
    builds transaction records. Only records with a recognized transaction type
    (i.e. not bare ``candidate``) are returned, matching the EDGAR discovery
    contract.
    """
    from utils.sedarplus import SedarplusClient, discover_documents, fetch_document_text

    records: list[dict] = []
    # SEDAR+ resource URLs contain session-bound DRM keys, so discovery and
    # download must share one browser context.
    with SedarplusClient(headless=headless) as client:
        documents = discover_documents(
            days=days, limit=limit * 2, headless=headless, client=client
        )
        for doc in documents:
            url = doc.download_url
            try:
                parsed = fetch_document_text(
                    url, headless=headless, client=client
                ) if url else {"text": "", "sha256": ""}
            except Exception as exc:  # noqa: BLE001
                log.warning("SEDAR+ document parse failed for %s: %s", url, exc)
                parsed = {"text": "", "sha256": ""}
            record = candidate_from_sedar(doc.to_dict(), text=parsed.get("text", ""))
            record["document_hash"] = parsed.get("sha256", "")
            record["detected_items"] = sorted(parsed.get("sections", {}))
            record["metadata"].update({
                "document_count": 1,
                "document_types": [doc.document_name] if doc.document_name else [],
                "section_items": sorted(parsed.get("sections", {})),
            })
            if record["transaction_type"] != "candidate":
                records.append(record)
            if len(records) >= limit:
                break
    return records


def discover_edgar_candidates(years: int = 3, limit: int = 40) -> list[dict]:
    """Discover recent candidates from EDGAR and classify their primary filings."""
    from utils.edgar import get_filing_submission, search_filings
    from utils.filing_intelligence import build_filing_document

    start = (date.today() - timedelta(days=365 * years)).isoformat()
    end = date.today().isoformat()
    queries = (
        '"Item 5.06" "shell company"',
        '"ceased to be a shell company"',
        '"reverse merger" "Item 2.01"',
        '"reverse acquisition" "Item 1.01"',
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
                raw = get_filing_submission(hit["file_url"])
                filing = build_filing_document(raw, source_url=hit["file_url"])
                text = filing["combined_text"]
            except Exception:
                filing = {"documents": [], "sections": {}, "sha256": ""}
                text = ""
            record = candidate_from_edgar(hit, text=text)
            record["document_hash"] = filing["sha256"]
            record["detected_items"] = sorted(filing["sections"])
            record["metadata"].update({
                "document_count": len(filing["documents"]),
                "document_types": sorted({
                    document["document_type"] for document in filing["documents"]
                    if document["document_type"]
                }),
                "section_items": sorted(filing["sections"]),
            })
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
          completion_date=COALESCE(EXCLUDED.completion_date,liquidround.reverse_merger_transactions.completion_date),
          deal_value=COALESCE(EXCLUDED.deal_value,liquidround.reverse_merger_transactions.deal_value),
          concurrent_financing=COALESCE(EXCLUDED.concurrent_financing,liquidround.reverse_merger_transactions.concurrent_financing),
          target_ownership_pct=COALESCE(EXCLUDED.target_ownership_pct,liquidround.reverse_merger_transactions.target_ownership_pct),
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
            if record.get("source_filing_id"):
                regulator = "SEDAR+" if record.get("jurisdiction") == "CA" and "sedar" in (
                    record.get("source_type", "") + record.get("transaction_key", "")
                ).lower() else ("SEDAR+" if record.get("source_type") == "SEDAR+" else "SEC")
                cur.execute(
                    """
                INSERT INTO liquidround.reverse_merger_filings
                    (transaction_id,regulator,form_type,filing_date,
                     accession_number,source_url,detected_items,document_hash)
                SELECT id,%s,%s,%s,%s,%s,%s::jsonb,%s
                FROM liquidround.reverse_merger_transactions
                WHERE transaction_key=%s
                ON CONFLICT (regulator,accession_number,source_url) DO UPDATE SET
                    form_type=EXCLUDED.form_type,
                    filing_date=EXCLUDED.filing_date,
                    detected_items=EXCLUDED.detected_items,
                    document_hash=EXCLUDED.document_hash
                    """,
                    (
                        regulator, record.get("source_type"), record.get("announcement_date"),
                        record.get("source_filing_id"), record.get("source_url"),
                        json.dumps(record.get("detected_items", [])),
                        record.get("document_hash"), record.get("transaction_key"),
                    ),
                )
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
