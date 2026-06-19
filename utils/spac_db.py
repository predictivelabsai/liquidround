"""SPAC data layer — CRUD for liquidround.spac_data + 13F cross-reference."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

SCHEMA = "liquidround"
TABLE = f"{SCHEMA}.spac_data"


def _get_conn():
    from .database import get_conn
    return get_conn()


def upsert_spacs(records: list[dict]) -> int:
    if not records:
        return 0
    cols = [
        "spac_key", "ticker", "warrant_ticker", "company_name", "sponsor",
        "status", "trust_size", "trust_per_share", "current_price",
        "warrant_price", "nav_premium_pct", "target_name", "target_sector",
        "ipo_date", "da_date", "vote_date", "completion_date", "deadline_date",
        "redemption_pct", "exchange", "sector_focus", "country", "ipo_size",
        "deal_value", "post_merge_return_1m", "post_merge_return_3m",
        "post_merge_return_6m", "source", "last_updated",
    ]
    update_cols = [c for c in cols if c != "spac_key"]
    placeholders = ", ".join(["%s"] * len(cols))
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    sql = f"""
        INSERT INTO {TABLE} ({", ".join(cols)})
        VALUES ({placeholders})
        ON CONFLICT (spac_key) DO UPDATE SET {update_set}
    """
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with _get_conn() as conn:
        cur = conn.cursor()
        for rec in records:
            rec.setdefault("last_updated", now)
            vals = [rec.get(c) for c in cols]
            try:
                cur.execute(sql, vals)
                n += 1
            except Exception:
                conn.rollback()
                logger.warning("Failed to upsert SPAC %s", rec.get("spac_key"), exc_info=True)
        conn.commit()
    return n


def get_spac_data(
    status: Optional[str] = None,
    sort: str = "trust_size",
    limit: int = 500,
) -> pd.DataFrame:
    allowed_sorts = {
        "trust_size": "trust_size DESC NULLS LAST",
        "ipo_date": "ipo_date DESC NULLS LAST",
        "current_price": "current_price DESC NULLS LAST",
        "nav_premium_pct": "nav_premium_pct DESC NULLS LAST",
        "company_name": "company_name ASC",
    }
    order = allowed_sorts.get(sort, allowed_sorts["trust_size"])
    where = ""
    params: list = []
    if status:
        where = "WHERE status = %s"
        params.append(status)
    params.append(limit)
    sql = f"SELECT * FROM {TABLE} {where} ORDER BY {order} LIMIT %s"
    with _get_conn() as conn:
        return pd.read_sql(sql, conn, params=params)


def get_spac_stats() -> dict:
    sql = f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status = 'searching') AS seeking,
            COUNT(*) FILTER (WHERE status = 'announced') AS announced,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed,
            COUNT(*) FILTER (WHERE status = 'liquidated') AS liquidated,
            COALESCE(SUM(trust_size) FILTER (WHERE status IN ('searching','announced')), 0) AS total_trust,
            COALESCE(AVG(redemption_pct) FILTER (WHERE redemption_pct IS NOT NULL), 0) AS avg_redemption
        FROM {TABLE}
    """
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()
    if not row:
        return {"total": 0, "seeking": 0, "announced": 0, "completed": 0,
                "liquidated": 0, "total_trust": 0, "avg_redemption": 0.0}
    return {
        "total": row[0], "seeking": row[1], "announced": row[2],
        "completed": row[3], "liquidated": row[4],
        "total_trust": int(row[5] or 0), "avg_redemption": float(row[6] or 0),
    }


def get_spac_timeline(years: int = 5) -> list[dict]:
    sql = f"""
        SELECT
            EXTRACT(YEAR FROM ipo_date)::int AS year,
            COUNT(*) AS ipo_count,
            COALESCE(SUM(ipo_size), 0) AS total_proceeds
        FROM {TABLE}
        WHERE ipo_date IS NOT NULL
          AND ipo_date >= CURRENT_DATE - INTERVAL '%s years'
        GROUP BY 1
        ORDER BY 1
    """
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (years,))
        return [{"year": r[0], "ipo_count": r[1], "total_proceeds": int(r[2] or 0)}
                for r in cur.fetchall()]


def get_institutional_holders(ticker: str, limit: int = 20) -> list[dict]:
    sql = """
        SELECT
            cp.filingmanager_name AS fund,
            it.value AS position_value,
            it.ssh_prn_amt AS shares,
            sp.table_value_total AS fund_aum
        FROM hedgefolio.infotable it
        JOIN hedgefolio.coverpage cp USING (accession_number)
        LEFT JOIN hedgefolio.summarypage sp USING (accession_number)
        WHERE UPPER(it.name_of_issuer) LIKE UPPER(%s)
        ORDER BY it.value DESC NULLS LAST
        LIMIT %s
    """
    pattern = f"%{ticker.upper()}%"
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (pattern, limit))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def search_spacs(query: str, limit: int = 50) -> pd.DataFrame:
    sql = f"""
        SELECT ticker, company_name, status, trust_size, current_price,
               nav_premium_pct, target_name, ipo_date, exchange
        FROM {TABLE}
        WHERE company_name ILIKE %s OR ticker ILIKE %s OR target_name ILIKE %s
        ORDER BY trust_size DESC NULLS LAST
        LIMIT %s
    """
    pattern = f"%{query}%"
    with _get_conn() as conn:
        return pd.read_sql(sql, conn, params=(pattern, pattern, pattern, limit))


def get_status_breakdown() -> list[dict]:
    sql = f"""
        SELECT status, COUNT(*) AS count, COALESCE(SUM(trust_size), 0) AS trust_total
        FROM {TABLE}
        GROUP BY status
        ORDER BY trust_total DESC
    """
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        return [{"status": r[0], "count": r[1], "trust_total": int(r[2] or 0)}
                for r in cur.fetchall()]
