"""Denmark company sync — populate liquidround.deal_candidates from the Erhvervsstyrelsen
open data (free, public credentials).

  • distribution.virk.dk/offentliggoerelser (creds oiorest:oiorest) -> annual-report
    metadata: CVR + the XBRL document URL, newest first.
  • The XBRL (gzip) carries the company name (g:NameOfReportingEntity) and financials.
    Danish accounting-class-B companies disclose GrossProfitLoss (bruttofortjeneste)
    rather than Revenue, so we use Revenue when present, else GrossProfitLoss as a size
    proxy. Values are DKK -> converted to EUR.

Per-company XBRL fetch, so bounded by --target (number of covered companies to collect)
and deduped to the latest report per CVR.

    python -m scripts.sync_dk_register --target 200
"""
from __future__ import annotations

import argparse
import gzip
import logging
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

import requests
import psycopg2.extras
from utils.database import get_conn

log = logging.getLogger("sync_dk")

OFF = "http://distribution.virk.dk/offentliggoerelser/_search"
AUTH = ("oiorest", "oiorest")
DKK_EUR = 0.134
REV_FLOOR_EUR = 100_000
PUBLIC = ["novo nordisk", "maersk", "mærsk", "danske bank", "carlsberg", "vestas",
          "ørsted", "orsted", "coloplast", "genmab", "dsv", "pandora", "tryg",
          "demant", "ambu", "netcompany", "chr. hansen", "novozymes", "gn store",
          "rockwool", "issa", "jyske bank", "sydbank", "topdanmark", "nkt"]


def _num(xbrl: str, tag: str) -> float | None:
    m = re.search(rf'<{re.escape(tag)}[^>]*>(-?[0-9.]+)</{re.escape(tag)}>', xbrl)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _parse_xbrl(url: str) -> tuple[str | None, float | None, str]:
    try:
        raw = requests.get(url, timeout=20).content
        try:
            xbrl = gzip.decompress(raw).decode("utf-8", "ignore")
        except OSError:
            xbrl = raw.decode("utf-8", "ignore")
    except Exception:
        return None, None, ""
    nm = re.search(r'<[a-z]+:NameOfReportingEntity[^>]*>([^<]+)</[a-z]+:NameOfReportingEntity>', xbrl)
    name = nm.group(1).strip() if nm else None
    # Revenue (nettoomsaetning) preferred, else GrossProfitLoss (bruttofortjeneste)
    val = None
    for tag in ("fsa:Revenue", "d:Revenue"):
        val = _num(xbrl, tag)
        if val:
            break
    kind = "revenue"
    if not val:
        for tag in ("d:GrossProfitLoss", "fsa:GrossProfitLoss", "d:GrossResult"):
            val = _num(xbrl, tag)
            if val:
                kind = "gross-profit"
                break
    return name, (val * DKK_EUR if val else None), kind


def collect(target: int) -> list[dict]:
    out, seen, frm = [], set(), 0
    while len(out) < target and frm < 20000:
        body = {"from": frm, "size": 100,
                "query": {"term": {"offentliggoerelsestype": "regnskab"}},
                "sort": [{"offentliggoerelsesTidspunkt": "desc"}]}
        r = requests.post(OFF, json=body, auth=AUTH, timeout=30)
        hits = r.json().get("hits", {}).get("hits", [])
        if not hits:
            break
        frm += 100
        for h in hits:
            s = h["_source"]
            cvr = s.get("cvrNummer")
            if not cvr or cvr in seen:
                continue
            seen.add(cvr)
            xurl = next((d.get("dokumentUrl") for d in s.get("dokumenter", [])
                         if d.get("dokumentMimeType") == "application/xml"), None)
            if not xurl:
                continue
            name, rev, kind = _parse_xbrl(xurl)
            if name and rev and rev >= REV_FLOOR_EUR and \
               not any(p in name.lower() for p in PUBLIC):
                out.append({"cvr": str(cvr), "name": name, "revenue": round(rev, 2), "kind": kind})
                if len(out) >= target:
                    break
        log.info("scanned %d reports, collected %d covered", frm, len(out))
    return out


def _ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS reg_code TEXT")
    cur.execute("ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS last_synced TIMESTAMPTZ")


def upsert(conn, companies: list[dict]) -> int:
    best = {}
    for c in companies:
        k = c["name"].lower()
        if k not in best or c["revenue"] > best[k]["revenue"]:
            best[k] = c
    rows = [(
        c["name"], "Denmark", "",
        f"Private Danish company ({c['kind']} basis)",
        "Erhvervsstyrelsen annual reports (CVR)", "undisclosed",
        "dk-register", c["cvr"], c["revenue"],
    ) for c in best.values()]
    cur = conn.cursor()
    psycopg2.extras.execute_values(cur, """
        INSERT INTO liquidround.deal_candidates
          (company_name, country, sector, description, deal_context, deal_size_estimate,
           source, reg_code, estimated_revenue_eur)
        VALUES %s
        ON CONFLICT (company_name, country) DO UPDATE SET
          description = EXCLUDED.description, reg_code = EXCLUDED.reg_code,
          estimated_revenue_eur = EXCLUDED.estimated_revenue_eur,
          is_active = TRUE, last_synced = NOW()
    """, rows, template="(%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    return len(rows)


def main(target=200) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()
    companies = collect(target)
    with get_conn() as conn:
        _ensure_schema(conn)
    with get_conn() as conn:
        n = upsert(conn, companies) if companies else 0
    dt = time.time() - t0
    log.info("DK sync: upserted %d covered targets in %.1fs", n, dt)
    return {"upserted": n, "seconds": round(dt, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=200)
    print(main(target=ap.parse_args().target))
