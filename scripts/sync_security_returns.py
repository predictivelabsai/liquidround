"""Batch job: compute YTD returns for top 13F-held securities.

Pipeline: hedgefolio CUSIPs -> OpenFIGI ticker lookup -> yfinance YTD return.

Usage:
    python -m scripts.sync_security_returns           # top 2000 CUSIPs
    python -m scripts.sync_security_returns --limit 500
    python -m scripts.sync_security_returns --dry-run
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("sync_returns")

DB_URL = os.getenv("DB_URL")
HEDGEFOLIO = "hedgefolio"
SCHEMA = "liquidround"

OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
OPENFIGI_BATCH = 10  # max per request without API key


def _get_top_cusips(conn, limit: int) -> list[dict]:
    """Top CUSIPs by total holding value from hedgefolio."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT i.cusip, i.name_of_issuer, SUM(i.value) AS total_value
            FROM {HEDGEFOLIO}.infotable i
            JOIN {HEDGEFOLIO}.coverpage c ON i.accession_number = c.accession_number
            JOIN {HEDGEFOLIO}.summarypage s ON c.accession_number = s.accession_number
            WHERE s.table_value_total IS NOT NULL
              AND i.value > 0
              AND i.cusip IS NOT NULL
              AND LENGTH(i.cusip) >= 6
            GROUP BY i.cusip, i.name_of_issuer
            ORDER BY SUM(i.value) DESC
            LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def _get_existing_tickers(conn) -> dict[str, str]:
    """Load existing CUSIP->ticker from DB."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT cusip, ticker FROM {SCHEMA}.security_returns WHERE ticker IS NOT NULL")
        return {r[0]: r[1] for r in cur.fetchall()}


def _openfigi_batch(cusips: list[str]) -> dict[str, str]:
    """Resolve a batch of CUSIPs to tickers via OpenFIGI API."""
    result = {}
    for i in range(0, len(cusips), OPENFIGI_BATCH):
        batch = cusips[i:i + OPENFIGI_BATCH]
        payload = [{"idType": "ID_CUSIP", "idValue": c} for c in batch]
        try:
            r = requests.post(OPENFIGI_URL, json=payload,
                              headers={"Content-Type": "application/json"}, timeout=15)
            if r.status_code == 429:
                log.warning("OpenFIGI rate limit — sleeping 30s")
                time.sleep(30)
                r = requests.post(OPENFIGI_URL, json=payload,
                                  headers={"Content-Type": "application/json"}, timeout=15)
            if r.status_code != 200:
                log.warning("OpenFIGI HTTP %d for batch %d", r.status_code, i)
                continue
            for j, item in enumerate(r.json()):
                if "data" in item and item["data"]:
                    ticker = item["data"][0].get("ticker")
                    if ticker:
                        # Normalize: yfinance uses '-' not '/' (e.g. BRK-B not BRK/B)
                        ticker = ticker.replace("/", "-")
                        # Skip index symbols (start with $)
                        if not ticker.startswith("$"):
                            result[batch[j]] = ticker
        except Exception as e:
            log.warning("OpenFIGI error: %s", e)
        # Rate-limit: 5 req/min without API key
        if i + OPENFIGI_BATCH < len(cusips):
            time.sleep(12)
    return result


def _calc_ytd_return(ticker: str) -> float | None:
    """YTD return from yfinance."""
    try:
        t = yf.Ticker(ticker)
        now = datetime.now(timezone.utc)
        hist = t.history(start=f"{now.year}-01-01", end=now.strftime("%Y-%m-%d"))
        if hist.empty or len(hist) < 2:
            return None
        first_close = float(hist["Close"].iloc[0])
        last_close = float(hist["Close"].iloc[-1])
        if first_close <= 0 or last_close <= 0:
            return None
        import math
        ret = (last_close - first_close) / first_close
        if math.isnan(ret) or math.isinf(ret):
            return None
        return ret
    except Exception as e:
        log.debug("yfinance error for %s: %s", ticker, e)
        return None


def _upsert_returns(conn, records: list[dict]) -> int:
    if not records:
        return 0
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            f"""INSERT INTO {SCHEMA}.security_returns (cusip, ticker, company_name, return_ytd, updated_at)
                VALUES %s
                ON CONFLICT (cusip) DO UPDATE SET
                    ticker = EXCLUDED.ticker,
                    company_name = EXCLUDED.company_name,
                    return_ytd = EXCLUDED.return_ytd,
                    updated_at = NOW()""",
            [(r["cusip"], r["ticker"], r["company_name"], r["return_ytd"]) for r in records],
            template="(%s, %s, %s, %s, NOW())",
        )
    conn.commit()
    return len(records)


def main(limit: int = 2000, dry_run: bool = False) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    conn = psycopg2.connect(DB_URL)
    try:
        top = _get_top_cusips(conn, limit)
        log.info("Fetched %d top CUSIPs from hedgefolio", len(top))

        existing = _get_existing_tickers(conn)
        log.info("Loaded %d existing ticker mappings from DB", len(existing))

        # Identify CUSIPs that need OpenFIGI lookup
        cusip_map = {c: existing[c] for c in existing}
        need_lookup = [r["cusip"] for r in top if r["cusip"] not in cusip_map]
        log.info("Need OpenFIGI lookup for %d CUSIPs", len(need_lookup))

        if need_lookup:
            figi_result = _openfigi_batch(need_lookup)
            cusip_map.update(figi_result)
            log.info("OpenFIGI resolved %d / %d CUSIPs", len(figi_result), len(need_lookup))

        # Build issuer name lookup
        issuer_names = {r["cusip"]: r["name_of_issuer"] for r in top}

        # Fetch YTD returns via yfinance
        results = []
        skipped = 0
        errors = 0
        unique_tickers_seen = set()

        for i, row in enumerate(top):
            cusip = row["cusip"]
            ticker = cusip_map.get(cusip)
            if not ticker:
                skipped += 1
                continue

            # Skip duplicate tickers (different CUSIPs, same company e.g. GOOG/GOOGL)
            if ticker in unique_tickers_seen:
                results.append({
                    "cusip": cusip,
                    "ticker": ticker,
                    "company_name": issuer_names.get(cusip, ""),
                    "return_ytd": next((r["return_ytd"] for r in results if r["ticker"] == ticker), None),
                })
                continue
            unique_tickers_seen.add(ticker)

            ytd = _calc_ytd_return(ticker)
            if ytd is None:
                errors += 1
                continue

            results.append({
                "cusip": cusip,
                "ticker": ticker,
                "company_name": issuer_names.get(cusip, ""),
                "return_ytd": round(ytd, 4),
            })

            if (i + 1) % 100 == 0:
                log.info("Progress: %d/%d processed, %d resolved, %d skipped",
                         i + 1, len(top), len(results), skipped)

        # Filter out None returns and deduplicate by CUSIP
        results = [r for r in results if r["return_ytd"] is not None]
        seen_cusips = set()
        deduped = []
        for r in results:
            if r["cusip"] not in seen_cusips:
                seen_cusips.add(r["cusip"])
                deduped.append(r)
        results = deduped

        log.info("Final: %d with returns, %d skipped (no ticker), %d errors (yfinance)",
                 len(results), skipped, errors)

        if dry_run:
            for r in sorted(results, key=lambda x: x["return_ytd"] or 0, reverse=True)[:20]:
                log.info("  %s %-6s %-30s YTD=%+.2f%%",
                         r["cusip"], r["ticker"], r["company_name"][:30], r["return_ytd"] * 100)
            log.info("Dry run — %d records would be written", len(results))
        else:
            written = _upsert_returns(conn, results)
            log.info("Upserted %d rows into %s.security_returns", written, SCHEMA)

        return {"resolved": len(results), "skipped": skipped, "errors": errors}
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync YTD security returns from yfinance")
    parser.add_argument("--limit", type=int, default=2000, help="Top N CUSIPs to process")
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing")
    args = parser.parse_args()
    main(limit=args.limit, dry_run=args.dry_run)
