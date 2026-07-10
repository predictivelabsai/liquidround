"""Norway company sync — populate liquidround.deal_candidates from Brønnøysund (BRREG),
a fully-open registry.

Sources (both free, open, no auth):
  • Enhetsregisteret API → company list (AS = private limited), NACE sector, bankruptcy
    flag (konkurs) — the cleanup signal.
  • Regnskapsregisteret API → per-company annual accounts; sumDriftsinntekter = operating
    revenue.

Unlike Estonia (bulk turnover CSV), NO financials are per-company, so revenue is fetched
concurrently and the run is bounded by --target (number of covered companies to collect).
Active AS companies with revenue ≥ €100k are imported as private M&A targets.

    python -m scripts.sync_no_register --target 500      # collect 500 covered, timed
    python -m scripts.sync_no_register --target 10000
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

import requests
import psycopg2.extras
from utils.database import get_conn

log = logging.getLogger("sync_no")

ENHETER = "https://data.brreg.no/enhetsregisteret/api/enheter"
BULK = "https://data.brreg.no/enhetsregisteret/api/enheter/lastned"
REGNSKAP = "https://data.brreg.no/regnskapsregisteret/regnskap/{}"
NOK_EUR = 0.086            # ~1 NOK; used only for the revenue-floor filter
REV_FLOOR_EUR = 100_000
PAGE = 500
PUBLIC = ["equinor", "dnb", "telenor", "norsk hydro", "yara", "orkla", "mowi",
          "aker", "kongsberg", "storebrand", "gjensidige", "schibsted", "tomra",
          "nordic semiconductor", "salmar", "leroy", "adevinta", "elkem"]


def _revenue_eur(orgnr: str) -> tuple[float | None, str, str]:
    """Latest operating revenue (EUR) + fiscal year + currency for an orgnr."""
    try:
        r = requests.get(REGNSKAP.format(orgnr), timeout=15)
        if r.status_code != 200:
            return None, "", ""
        data = r.json()
        if not isinstance(data, list) or not data:
            return None, "", ""
        rec = data[0]  # most recent
        val = (rec.get("resultatregnskapResultat", {})
                  .get("driftsresultat", {})
                  .get("driftsinntekter", {})
                  .get("sumDriftsinntekter"))
        if val is None:
            return None, "", ""
        cur = rec.get("valuta") or "NOK"
        year = (rec.get("regnskapsperiode", {}) or {}).get("tilDato", "")[:4]
        eur = float(val) * (NOK_EUR if cur == "NOK" else (1.0 if cur == "EUR" else 0.9))
        return eur, year, cur
    except Exception:
        return None, "", ""


def collect(target: int) -> list[dict]:
    """Page AS companies, fetch revenue concurrently, keep those ≥ floor."""
    out, page, scanned = [], 0, 0
    with ThreadPoolExecutor(max_workers=20) as pool:
        while len(out) < target and page < 400:
            resp = requests.get(ENHETER, params={
                "organisasjonsform": "AS", "konkurs": "false",
                "size": PAGE, "page": page}, timeout=25)
            ents = resp.json().get("_embedded", {}).get("enheter", [])
            if not ents:
                break
            page += 1
            scanned += len(ents)
            ents = [e for e in ents
                    if not any(p in (e.get("navn") or "").lower() for p in PUBLIC)]
            revs = list(pool.map(lambda e: _revenue_eur(e["organisasjonsnummer"]), ents))
            for e, (eur, yr, cur) in zip(ents, revs):
                if eur and eur >= REV_FLOOR_EUR:
                    out.append({
                        "orgnr": e["organisasjonsnummer"],
                        "name": (e.get("navn") or "").strip(),
                        "sector": (e.get("naeringskode1") or {}).get("beskrivelse", "")[:120],
                        "revenue": round(eur, 2),
                        "employees": e.get("antallAnsatte"),
                    })
                    if len(out) >= target:
                        break
            log.info("scanned %d AS, collected %d covered", scanned, len(out))
    return out


def _iter_bulk_as():
    """Stream the full BRREG registry (209MB gz) → active AS companies. Not capped
    at the API's 10k-result pagination limit, so it can cover all ~426k."""
    import gzip
    import ijson
    r = requests.get(BULK, stream=True, timeout=300,
                     headers={"Accept": "application/vnd.brreg.enhetsregisteret.enhet.v2+gzip"})
    r.raise_for_status()
    gz = gzip.GzipFile(fileobj=r.raw)
    for ent in ijson.items(gz, "item"):
        of = ent.get("organisasjonsform") or {}
        if of.get("kode") == "AS" and not ent.get("konkurs"):
            name = (ent.get("navn") or "").strip()
            if name and not any(p in name.lower() for p in PUBLIC):
                yield {"orgnr": ent["organisasjonsnummer"], "name": name,
                       "sector": ((ent.get("naeringskode1") or {}).get("beskrivelse") or "")[:120],
                       "employees": ent.get("antallAnsatte")}


def collect_bulk(target: int) -> list[dict]:
    """Enumerate all AS via the bulk file, enrich revenue concurrently, keep covered."""
    out, buf, scanned = [], [], 0
    with ThreadPoolExecutor(max_workers=20) as pool:
        for ent in _iter_bulk_as():
            buf.append(ent)
            if len(buf) >= 100:
                for e, (eur, yr, cur) in zip(buf, pool.map(lambda x: _revenue_eur(x["orgnr"]), buf)):
                    if eur and eur >= REV_FLOOR_EUR:
                        e["revenue"] = round(eur, 2)
                        out.append(e)
                scanned += len(buf)
                buf = []
                if scanned % 2000 == 0:
                    log.info("bulk: scanned %d AS, collected %d covered", scanned, len(out))
                if len(out) >= target:
                    break
    return out[:target]


def _ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS reg_code TEXT")
    cur.execute("ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS last_synced TIMESTAMPTZ")


def upsert(conn, companies: list[dict]) -> int:
    # dedupe by name (conflict key)
    best = {}
    for c in companies:
        k = c["name"].lower()
        if k not in best or c["revenue"] > best[k]["revenue"]:
            best[k] = c
    rows = [(
        c["name"], "Norway", c["sector"],
        f"Private Norwegian company (AS) in {c['sector'] or 'diversified'}"
        + (f", ~{c['employees']} employees" if c["employees"] else ""),
        "Brønnøysund Register + Regnskapsregisteret", "undisclosed",
        "no-register", c["orgnr"], c["revenue"],
    ) for c in best.values()]
    cur = conn.cursor()
    psycopg2.extras.execute_values(cur, """
        INSERT INTO liquidround.deal_candidates
          (company_name, country, sector, description, deal_context, deal_size_estimate,
           source, reg_code, estimated_revenue_eur)
        VALUES %s
        ON CONFLICT (company_name, country) DO UPDATE SET
          sector = EXCLUDED.sector, description = EXCLUDED.description,
          reg_code = EXCLUDED.reg_code, estimated_revenue_eur = EXCLUDED.estimated_revenue_eur,
          is_active = TRUE, last_synced = NOW()
    """, rows, template="(%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    return len(rows)


def main(target=500, bulk=False) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()
    companies = collect_bulk(target) if bulk else collect(target)
    with get_conn() as conn:
        _ensure_schema(conn)
    with get_conn() as conn:
        n = upsert(conn, companies)
    dt = time.time() - t0
    log.info("NO sync: upserted %d covered targets in %.1fs", n, dt)
    return {"upserted": n, "seconds": round(dt, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=500)
    ap.add_argument("--bulk", action="store_true", help="stream the full 209MB registry (beyond the 10k API cap)")
    a = ap.parse_args()
    print(main(target=a.target, bulk=a.bulk))
