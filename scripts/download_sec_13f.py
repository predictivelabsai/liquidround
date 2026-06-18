#!/usr/bin/env python3
"""Download the latest SEC Form 13F quarterly dataset and load it into the DB.

Usage:
    python -m scripts.download_sec_13f              # download + load
    python -m scripts.download_sec_13f --skip-load  # download only
    python -m scripts.download_sec_13f --skip-download  # load existing TSVs

Data ends up in the hedgefolio schema on the shared PostgreSQL DB.
"""
from __future__ import annotations

import calendar
import logging
import os
import shutil
import zipfile
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

import requests

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEC_BASE = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets"
USER_AGENT = os.getenv("SEC_USER_AGENT", "LiquidRound/1.0 (info@liquidround.com)")
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "sec_13f"
DOWNLOAD_DIR = DATA_DIR / "downloads"


def _last_day(y: int, m: int) -> int:
    return calendar.monthrange(y, m)[1]


def _window_url(start: date) -> tuple[str, str]:
    y1, m1 = start.year, start.month
    m3 = m1 + 2
    y3 = y1
    if m3 > 12:
        m3 -= 12
        y3 += 1
    end = date(y3, m3, _last_day(y3, m3))
    mon_s = calendar.month_abbr[m1].lower()
    mon_e = calendar.month_abbr[m3].lower()
    name = f"01{mon_s}{y1}-{end.day:02d}{mon_e}{y3}_form13f.zip"
    return name, f"{SEC_BASE}/{name}"


def _quarter_starts(n: int = 12) -> Iterable[date]:
    today = date.today()
    y = today.year
    candidates = [(y, 12), (y, 9), (y, 6), (y, 3),
                  (y - 1, 12), (y - 1, 9), (y - 1, 6), (y - 1, 3),
                  (y - 2, 12), (y - 2, 9), (y - 2, 6), (y - 2, 3)]
    starts = []
    for yy, mm in candidates:
        end_month = mm + 2
        end_year = yy
        if end_month > 12:
            end_month -= 12
            end_year += 1
        end = date(end_year, end_month, _last_day(end_year, end_month))
        if end <= today:
            starts.append(date(yy, mm, 1))
    return starts[:n]


def find_latest_url(session: requests.Session) -> tuple[str, str]:
    for start in _quarter_starts():
        name, url = _window_url(start)
        r = session.head(url, allow_redirects=True, timeout=30)
        if r.status_code == 200:
            logger.info("Latest window: %s (%s bytes)", name, r.headers.get("Content-Length", "?"))
            return name, url
    raise RuntimeError("No recent SEC 13F dataset found")


def download(url: str, dest: Path, session: requests.Session) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    logger.info("Downloading %s → %s", url, dest)
    import time
    with session.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        last_report = time.time()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
                    done += len(chunk)
                    now = time.time()
                    if now - last_report > 5:
                        pct = (done / total * 100) if total else 0
                        logger.info("  %.1f%% (%d / %d MB)", pct, done >> 20, total >> 20)
                        last_report = now
    tmp.rename(dest)
    logger.info("Done: %s (%d MB)", dest, dest.stat().st_size >> 20)


def extract(zip_path: Path, target: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    logger.info("Extracting %s → %s", zip_path, target)
    extracted = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            out = target / Path(info.filename).name
            with zf.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(out)
            logger.info("  %s (%d MB)", out.name, out.stat().st_size >> 20)
    return extracted


def load_to_db(data_dir: Path) -> None:
    import sys
    sys.path.insert(0, str(ROOT))
    from sqlalchemy import create_engine, text
    from utils.hedge_fund_db import SCHEMA, DB_URL

    if not DB_URL:
        raise ValueError("DB_URL not set")

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        conn.commit()

    # Use hedgefolio's loader — it handles the ORM and upserts
    import importlib.util
    hedgefolio_root = ROOT.parent / "hedgefolio"
    spec = importlib.util.spec_from_file_location("db_util", hedgefolio_root / "utils" / "db_util.py")
    if spec and spec.loader:
        db_util = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(db_util)
        db_util.load_all_data(str(data_dir))
    else:
        logger.error("Could not import hedgefolio db_util — load data manually")


def verify_counts() -> dict[str, int]:
    from utils.hedge_fund_db import get_session, SCHEMA
    from sqlalchemy import text
    tables = ["submission", "coverpage", "summarypage", "signature", "infotable"]
    s = get_session()
    counts = {}
    for t in tables:
        try:
            counts[t] = s.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.{t}")).scalar() or 0
        except Exception:
            counts[t] = -1
    s.close()
    return counts


def main(url_override: Optional[str] = None, *, skip_download: bool = False, skip_load: bool = False):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/zip, */*"})

    if skip_download:
        logger.info("Reusing existing files in %s", DATA_DIR)
    else:
        if url_override:
            name = Path(url_override).name
            url = url_override
        else:
            name, url = find_latest_url(session)
        zip_path = DOWNLOAD_DIR / name
        if zip_path.exists() and zip_path.stat().st_size > 1_000_000:
            logger.info("Reusing cached zip: %s", zip_path)
        else:
            download(url, zip_path, session)
        extract(zip_path, DATA_DIR)

    if skip_load:
        return

    load_to_db(DATA_DIR)
    counts = verify_counts()
    logger.info("Row counts:")
    for t, c in counts.items():
        logger.info("  %-16s %10d", t, c)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Download SEC 13F quarterly data")
    ap.add_argument("--url", help="Explicit SEC zip URL")
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--skip-load", action="store_true")
    args = ap.parse_args()
    main(url_override=args.url, skip_download=args.skip_download, skip_load=args.skip_load)
