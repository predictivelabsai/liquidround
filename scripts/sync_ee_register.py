"""Estonia company sync — populate liquidround.deal_candidates from the open registries.

Sources (both free, open):
  • RIK e-Business Register bulk  → company list + STATUS (active R / liquidation L /
    other N) — drives incremental cleanup of dissolved companies.
  • EMTA (Tax Board) turnover open data → annual turnover (from VAT returns), sector
    (Activity), employees, joined by registry code.

Only ACTIVE companies with annual turnover ≥ REV_FLOOR (default €100k) are imported as
private M&A targets (public companies are excluded). Idempotent + incremental: upserts
by (name, country), stores reg_code, and each run marks companies now in
liquidation/deleted as is_active = FALSE so they drop out of the Deal Radar.

    python -m scripts.sync_ee_register --limit 1000        # timed sample
    python -m scripts.sync_ee_register                     # full run (~44k)
    python -m scripts.sync_ee_register --refresh           # re-download source files
"""
from __future__ import annotations

import argparse
import csv
import io
import logging
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

import requests
import psycopg2.extras
from utils.database import get_conn

log = logging.getLogger("sync_ee")

RIK_URL = "https://avaandmed.ariregister.rik.ee/sites/default/files/avaandmed/ettevotja_rekvisiidid__lihtandmed.csv.zip"
EMTA_URL = "https://ncfailid.emta.ee/s/e4DneiWeKFfje6d/download/tasutud_maksud_kaesolev_aasta_eng.csv"
CACHE = Path("/tmp")
REV_FLOOR = 100_000
FULL_YEAR = "2025"   # latest year with all four quarters

PUBLIC = [w.lower() for w in [
    "swedbank", "seb pank", "luminor", "lhv", "coop pank", "telia", "tallink",
    "enefit", "ignitis", "harju elekter", "arco vara", "ekspress", "merko",
    "tallinna kaubamaja", "silvano", "pro kapital", "nordecon", "hepsor",
    "bercman", "coop eesti", "admiral markets", "trigon", "eften", "baltic horizon",
    "filiaal", "branch", "representative office",
]]


def _download(url: str, dest: Path, refresh: bool) -> Path:
    if dest.exists() and not refresh:
        return dest
    log.info("downloading %s", url)
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def load_rik_status(refresh: bool) -> dict[str, str]:
    """reg_code -> status (R active, L liquidation, N other)."""
    zp = _download(RIK_URL, CACHE / "rik_lihtandmed.csv.zip", refresh)
    with zipfile.ZipFile(zp) as z:
        name = [n for n in z.namelist() if n.endswith(".csv")][0]
        data = z.read(name).decode("utf-8-sig")
    status = {}
    for row in csv.reader(io.StringIO(data), delimiter=";"):
        if len(row) > 6 and row[1]:
            status[row[1]] = row[5]
    log.info("RIK: %d companies (%d active)", len(status),
             sum(1 for s in status.values() if s == "R"))
    return status


def load_targets(rik_status: dict[str, str], limit: int | None) -> list[dict]:
    """Active EE companies with FULL_YEAR annual turnover ≥ REV_FLOOR."""
    fp = _download(EMTA_URL, CACHE / "emta_turnover.csv", False)
    out = []
    with open(fp, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Year") != FULL_YEAR:
                continue
            code = row["Registry code"]
            if rik_status.get(code) != "R":            # active only
                continue
            name = (row["Name"] or "").strip()
            if not name or any(p in name.lower() for p in PUBLIC):
                continue
            try:
                rev = sum(float(row[f"Turnover {q} qtr"] or 0) for q in ("I", "II", "III", "IV"))
            except ValueError:
                continue
            if rev < REV_FLOOR:
                continue
            try:
                emp = int(float(row.get("Number of employees I qtr") or 0)) or None
            except ValueError:
                emp = None
            sector = (row.get("Activity") or "").title()[:120]
            out.append({"reg_code": code, "name": name, "sector": sector,
                        "revenue": round(rev, 2), "employees": emp,
                        "county": (row.get("County") or "").strip()})
            if limit and len(out) >= limit:
                break
    log.info("EMTA: %d active EE targets ≥ €%d turnover", len(out), REV_FLOOR)
    return out


def _ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS reg_code TEXT")
    cur.execute("ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS last_synced TIMESTAMPTZ")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deal_cand_regcode ON liquidround.deal_candidates (reg_code)")


def upsert(conn, companies: list[dict]) -> int:
    cur = conn.cursor()
    rows = [(
        c["name"], "Estonia", c["sector"],
        f"Private Estonian company in {c['sector'] or 'diversified'}"
        + (f", ~{c['employees']} employees" if c["employees"] else "")
        + (f" ({c['county']})" if c["county"] else ""),
        "Estonian Business Register + Tax Board turnover", "undisclosed",
        "ee-register", c["reg_code"], c["revenue"],
    ) for c in companies]
    psycopg2.extras.execute_values(cur, """
        INSERT INTO liquidround.deal_candidates
          (company_name, country, sector, description, deal_context, deal_size_estimate,
           source, reg_code, estimated_revenue_eur)
        VALUES %s
        ON CONFLICT (company_name, country) DO UPDATE SET
          sector = EXCLUDED.sector,
          description = EXCLUDED.description,
          reg_code = EXCLUDED.reg_code,
          estimated_revenue_eur = EXCLUDED.estimated_revenue_eur,
          is_active = TRUE,
          last_synced = NOW()
    """, rows, template="(%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    return len(rows)


def cleanup(conn, rik_status: dict[str, str]) -> int:
    """Deactivate EE targets whose register status is no longer active (L/N/gone)."""
    cur = conn.cursor()
    cur.execute("SELECT reg_code FROM liquidround.deal_candidates "
                "WHERE country='Estonia' AND reg_code IS NOT NULL AND COALESCE(is_active,TRUE)")
    dead = [r[0] for r in cur.fetchall() if rik_status.get(r[0]) != "R"]
    for i in range(0, len(dead), 1000):
        batch = dead[i:i + 1000]
        cur.execute("UPDATE liquidround.deal_candidates SET is_active=FALSE, last_synced=NOW() "
                    "WHERE country='Estonia' AND reg_code = ANY(%s)", (batch,))
    return len(dead)


def main(limit=None, refresh=False, no_cleanup=False) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()
    rik = load_rik_status(refresh)
    targets = load_targets(rik, limit)
    # Dedupe by name (the upsert conflict key is (company_name, country); EE has
    # distinct companies sharing a trade name) — keep the highest-revenue one.
    best: dict[str, dict] = {}
    for c in targets:
        k = c["name"].lower()
        if k not in best or c["revenue"] > best[k]["revenue"]:
            best[k] = c
    targets = list(best.values())
    # Schema change in its OWN committed transaction — the ALTER takes an
    # AccessExclusiveLock, so it must release before the upserts (else self-deadlock).
    with get_conn() as conn:
        _ensure_schema(conn)
    n = 0
    for i in range(0, len(targets), 2000):
        with get_conn() as c2:
            n += upsert(c2, targets[i:i + 2000])
    removed = 0
    if not no_cleanup:
        with get_conn() as conn:
            removed = cleanup(conn, rik)
    dt = time.time() - t0
    log.info("EE sync: upserted %d, deactivated %d, in %.1fs", n, removed, dt)
    return {"upserted": n, "deactivated": removed, "seconds": round(dt, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--no-cleanup", action="store_true")
    a = ap.parse_args()
    print(main(limit=a.limit, refresh=a.refresh, no_cleanup=a.no_cleanup))
