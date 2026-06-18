#!/usr/bin/env python3
"""Sync recent SEC Schedule 13D/13G activist filings from EDGAR daily index.

Usage:
    python -m scripts.sync_activist            # last 14 days
    python -m scripts.sync_activist --days 30  # last 30 days

Data goes into hedgefolio.activist_filing on the shared PostgreSQL DB.
"""
from __future__ import annotations

import logging
import os
import re
import time

from dotenv import load_dotenv
load_dotenv()
from datetime import date, timedelta
from typing import Iterator, Optional

import requests
from sqlalchemy import text

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

USER_AGENT = os.getenv("SEC_USER_AGENT", "LiquidRound/1.0 (info@liquidround.com)")
IDX_URL = "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{q}/form.{yyyymmdd}.idx"
ARCHIVE_URL = "https://www.sec.gov/Archives/{path}"
SCHEMA = "hedgefolio"

ACTIVIST_FORMS = {"SCHEDULE 13D", "SCHEDULE 13D/A", "SCHEDULE 13G", "SCHEDULE 13G/A"}

_DASH_RE = re.compile(r"^-{10,}$")


def _parse_index_lines(text_body: str) -> Iterator[tuple[str, str, str, date, str]]:
    past_header = False
    for raw in text_body.splitlines():
        if not past_header:
            if _DASH_RE.match(raw.strip()):
                past_header = True
            continue
        if not raw.strip() or len(raw) < 50:
            continue
        form_type = raw[:17].strip()
        if form_type not in ACTIVIST_FORMS:
            continue
        company = raw[17:79].strip()
        cik = raw[79:91].strip()
        date_str = raw[91:103].strip()
        path = raw[103:].strip()
        try:
            fd = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
        except (ValueError, IndexError):
            continue
        yield form_type, company, cik, fd, path


def _accession_from_path(path: str) -> Optional[str]:
    base = path.rsplit("/", 1)[-1]
    if base.endswith(".txt"):
        base = base[:-4]
    if re.fullmatch(r"\d{10}-\d{2}-\d{6}", base):
        return base
    return None


_INSERT_SQL = text(f"""
    INSERT INTO {SCHEMA}.activist_filing
        (accession_number, form_type, is_amendment, is_activist,
         filer_cik, filer_name, filing_date, filing_url, index_path)
    VALUES (:acc, :form, :amend, :activist, :cik, :name, :fd, :url, :path)
    ON CONFLICT (accession_number) DO UPDATE SET
        form_type = EXCLUDED.form_type,
        is_amendment = EXCLUDED.is_amendment,
        is_activist = EXCLUDED.is_activist,
        filer_cik = EXCLUDED.filer_cik,
        filer_name = EXCLUDED.filer_name,
        filing_date = EXCLUDED.filing_date,
        filing_url = EXCLUDED.filing_url,
        index_path = EXCLUDED.index_path,
        updated_at = NOW()
""")


def sync_days(days: int = 14) -> dict:
    from utils.hedge_fund_db import get_session
    sess = requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})

    today = date.today()
    total = 0
    fetched = 0

    for delta in range(days):
        d = today - timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        q = (d.month - 1) // 3 + 1
        url = IDX_URL.format(year=d.year, q=q, yyyymmdd=d.strftime("%Y%m%d"))
        try:
            r = sess.get(url, timeout=30)
        except requests.RequestException as e:
            logger.warning("Fetch failed %s: %s", d, e)
            continue
        if r.status_code in (403, 404):
            continue
        if r.status_code >= 400:
            logger.warning("Index %s returned %s", d, r.status_code)
            continue

        rows = list(_parse_index_lines(r.text))
        db_session = get_session()
        try:
            n = 0
            for form_type, company, cik, fd, path in rows:
                acc = _accession_from_path(path)
                if not acc:
                    continue
                db_session.execute(_INSERT_SQL, {
                    "acc": acc, "form": form_type,
                    "amend": form_type.endswith("/A"),
                    "activist": "13D" in form_type,
                    "cik": cik, "name": company[:250],
                    "fd": fd, "url": ARCHIVE_URL.format(path=path), "path": path,
                })
                n += 1
            db_session.commit()
            total += n
            fetched += 1
            logger.info("  %s → %d filings", d, n)
        except Exception as e:
            db_session.rollback()
            logger.error("DB error for %s: %s", d, e)
        finally:
            db_session.close()
        time.sleep(0.2)

    return {"filings_ingested": total, "days_fetched": fetched}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Sync SEC 13D/13G activist filings")
    ap.add_argument("--days", type=int, default=14, help="Days to look back (default 14)")
    args = ap.parse_args()
    result = sync_days(days=args.days)
    logger.info("Done: %s", result)
