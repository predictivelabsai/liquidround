"""Hedge fund 13F data layer — reads from the hedgefolio schema on the shared DB.

ORM models mirror the hedgefolio tables; query functions are consumed by
tools/hedge_funds.py (StructuredTools for the LangGraph agent) and
routes/hedge_funds.py (treemap page data).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd
from sqlalchemy import (
    Column, String, Integer, BigInteger, Date, Text, DateTime,
    ForeignKey, Index, create_engine, func, text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

log = logging.getLogger(__name__)

DB_URL = os.getenv("DB_URL")
SCHEMA = "hedgefolio"

Base = declarative_base()

# ── ORM models ──────────────────────────────────────────────────────────

class Submission(Base):
    __tablename__ = "submission"
    __table_args__ = {"schema": SCHEMA}
    accession_number = Column(String(25), primary_key=True)
    filing_date = Column(Date, nullable=False)
    submission_type = Column(String(10), nullable=False)
    cik = Column(String(10), nullable=False, index=True)
    period_of_report = Column(Date, nullable=False, index=True)


class CoverPage(Base):
    __tablename__ = "coverpage"
    __table_args__ = {"schema": SCHEMA}
    accession_number = Column(String(25), ForeignKey(f"{SCHEMA}.submission.accession_number"), primary_key=True)
    report_calendar_or_quarter = Column(Date)
    filingmanager_name = Column(String(150), nullable=False, index=True)
    filingmanager_city = Column(String(30))
    filingmanager_stateorcountry = Column(String(2))
    report_type = Column(String(30))


class SummaryPage(Base):
    __tablename__ = "summarypage"
    __table_args__ = {"schema": SCHEMA}
    accession_number = Column(String(25), ForeignKey(f"{SCHEMA}.submission.accession_number"), primary_key=True)
    table_entry_total = Column(Integer)
    table_value_total = Column(BigInteger, index=True)


class InfoTable(Base):
    __tablename__ = "infotable"
    __table_args__ = (
        Index("idx_infotable_cusip", "cusip"),
        Index("idx_infotable_name_of_issuer", "name_of_issuer"),
        {"schema": SCHEMA},
    )
    accession_number = Column(String(25), ForeignKey(f"{SCHEMA}.submission.accession_number"), primary_key=True)
    infotable_sk = Column(BigInteger, primary_key=True)
    name_of_issuer = Column(String(200), nullable=False)
    title_of_class = Column(String(150), nullable=False)
    cusip = Column(String(9), nullable=False)
    value = Column(BigInteger, nullable=False)
    ssh_prn_amt = Column(BigInteger, nullable=False)
    ssh_prn_amt_type = Column(String(10), nullable=False)
    put_call = Column(String(10))
    investment_discretion = Column(String(10))


# ── Session management ──────────────────────────────────────────────────

_engine = None
_SessionLocal = None


def _ensure_engine():
    global _engine, _SessionLocal
    if _engine is None:
        if not DB_URL:
            raise ValueError("DB_URL not set")
        _engine = create_engine(DB_URL)
        _SessionLocal = sessionmaker(bind=_engine)
    return _SessionLocal


def get_session() -> Session:
    factory = _ensure_engine()
    session = factory()
    try:
        session.rollback()
    except Exception:
        pass
    return session


# ── Query functions ─────────────────────────────────────────────────────

def get_summary_stats() -> dict:
    s = get_session()
    try:
        total_funds = s.execute(text(f"SELECT COUNT(DISTINCT filingmanager_name) FROM {SCHEMA}.coverpage")).scalar() or 0
        total_holdings = s.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.infotable")).scalar() or 0
        total_aum = s.execute(text(f"SELECT SUM(value) FROM {SCHEMA}.infotable")).scalar() or 0
        unique_securities = s.execute(text(f"SELECT COUNT(DISTINCT name_of_issuer) FROM {SCHEMA}.infotable")).scalar() or 0
        return {
            "total_funds": total_funds,
            "total_holdings": total_holdings,
            "total_aum": float(total_aum) if total_aum else 0,
            "unique_securities": unique_securities,
        }
    finally:
        s.close()


def search_funds(query: str, limit: int = 20) -> list[dict]:
    s = get_session()
    try:
        rows = s.execute(text(f"""
            SELECT c.filingmanager_name, c.accession_number,
                   s.table_value_total, s.table_entry_total
            FROM {SCHEMA}.coverpage c
            LEFT JOIN {SCHEMA}.summarypage s ON c.accession_number = s.accession_number
            WHERE LOWER(c.filingmanager_name) LIKE LOWER(:q)
            ORDER BY s.table_value_total DESC NULLS LAST
            LIMIT :lim
        """), {"q": f"%{query}%", "lim": limit}).fetchall()
        return [{"name": r[0], "accession_number": r[1], "portfolio_value": r[2], "positions": r[3]} for r in rows]
    finally:
        s.close()


def get_fund_names() -> list[str]:
    s = get_session()
    try:
        rows = s.execute(text(f"""
            SELECT DISTINCT filingmanager_name FROM {SCHEMA}.coverpage
            WHERE filingmanager_name IS NOT NULL ORDER BY filingmanager_name
        """)).fetchall()
        return [r[0] for r in rows]
    finally:
        s.close()


def get_top_funds(top_n: int = 20) -> pd.DataFrame:
    s = get_session()
    try:
        rows = s.execute(text(f"""
            SELECT c.filingmanager_name AS "Fund Name",
                   s.table_value_total AS "Portfolio Value",
                   s.table_entry_total AS "Total Positions"
            FROM {SCHEMA}.coverpage c
            JOIN {SCHEMA}.summarypage s ON c.accession_number = s.accession_number
            WHERE s.table_value_total IS NOT NULL
            ORDER BY s.table_value_total DESC
            LIMIT :lim
        """), {"lim": top_n}).fetchall()
        return pd.DataFrame(rows, columns=["Fund Name", "Portfolio Value", "Total Positions"])
    finally:
        s.close()


def get_fund_holdings(fund_name: str, limit: int = 50) -> pd.DataFrame:
    s = get_session()
    try:
        rows = s.execute(text(f"""
            SELECT i.name_of_issuer, i.title_of_class, i.cusip,
                   i.value, i.ssh_prn_amt
            FROM {SCHEMA}.infotable i
            JOIN {SCHEMA}.coverpage c ON i.accession_number = c.accession_number
            WHERE c.filingmanager_name = :fund
            ORDER BY i.value DESC
            LIMIT :lim
        """), {"fund": fund_name, "lim": limit}).fetchall()
        df = pd.DataFrame(rows, columns=["NAMEOFISSUER", "TITLEOFCLASS", "CUSIP", "VALUE", "SSHPRNAMT"])
        if not df.empty:
            total = df["VALUE"].sum()
            df["portfolio_pct"] = (df["VALUE"] / total * 100) if total > 0 else 0
        return df
    finally:
        s.close()


def search_securities(query: str, limit: int = 15) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = get_session()
    try:
        sec_rows = s.execute(text(f"""
            SELECT i.name_of_issuer AS "Security", i.title_of_class AS "Type",
                   SUM(i.value) AS "Total Value", SUM(i.ssh_prn_amt) AS "Total Shares",
                   COUNT(DISTINCT i.accession_number) AS "Fund Count"
            FROM {SCHEMA}.infotable i
            WHERE LOWER(i.name_of_issuer) LIKE LOWER(:q)
            GROUP BY i.name_of_issuer, i.title_of_class
            ORDER BY SUM(i.value) DESC LIMIT :lim
        """), {"q": f"%{query}%", "lim": limit}).fetchall()
        sec_df = pd.DataFrame(sec_rows, columns=["Security", "Type", "Total Value", "Total Shares", "Fund Count"])
        if sec_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        fund_rows = s.execute(text(f"""
            SELECT c.filingmanager_name AS "Fund Name",
                   SUM(i.value) AS "Position Value",
                   SUM(i.ssh_prn_amt) AS "Shares Held"
            FROM {SCHEMA}.infotable i
            JOIN {SCHEMA}.coverpage c ON i.accession_number = c.accession_number
            WHERE LOWER(i.name_of_issuer) LIKE LOWER(:q)
            GROUP BY c.filingmanager_name
            ORDER BY SUM(i.value) DESC LIMIT :lim
        """), {"q": f"%{query}%", "lim": limit}).fetchall()
        fund_df = pd.DataFrame(fund_rows, columns=["Fund Name", "Position Value", "Shares Held"])
        return sec_df, fund_df
    finally:
        s.close()


def get_popular_securities(top_n: int = 20) -> pd.DataFrame:
    s = get_session()
    try:
        rows = s.execute(text(f"""
            SELECT i.name_of_issuer AS "Security", i.title_of_class AS "Type",
                   SUM(i.value) AS "Total Value", SUM(i.ssh_prn_amt) AS "Total Shares",
                   COUNT(DISTINCT i.accession_number) AS "Fund Count"
            FROM {SCHEMA}.infotable i
            GROUP BY i.name_of_issuer, i.title_of_class
            ORDER BY SUM(i.value) DESC LIMIT :lim
        """), {"lim": top_n}).fetchall()
        return pd.DataFrame(rows, columns=["Security", "Type", "Total Value", "Total Shares", "Fund Count"])
    finally:
        s.close()


def get_fund_concentration(top_n: int = 20) -> pd.DataFrame:
    s = get_session()
    try:
        rows = s.execute(text(f"""
            SELECT c.filingmanager_name, s.table_value_total, s.table_entry_total
            FROM {SCHEMA}.coverpage c
            JOIN {SCHEMA}.summarypage s ON c.accession_number = s.accession_number
            WHERE s.table_value_total IS NOT NULL
            ORDER BY s.table_value_total DESC LIMIT :lim
        """), {"lim": top_n}).fetchall()
        return pd.DataFrame(rows, columns=["FILINGMANAGER_NAME", "TABLEVALUETOTAL", "TABLEENTRYTOTAL"])
    finally:
        s.close()


def recent_activist_filings(days: int = 30, limit: int = 25, activist_only: bool = True) -> list[dict]:
    s = get_session()
    try:
        where = ["filing_date >= CURRENT_DATE - make_interval(days => :days)"]
        if activist_only:
            where.append("is_activist = TRUE")
        rows = s.execute(text(f"""
            SELECT accession_number, form_type, filing_date,
                   filer_name, filer_cik, subject_name, subject_cik, filing_url
            FROM {SCHEMA}.activist_filing
            WHERE {' AND '.join(where)}
            ORDER BY filing_date DESC, accession_number DESC
            LIMIT :lim
        """), {"days": int(days), "lim": limit}).fetchall()
        return [
            {"accession_number": r[0], "form_type": r[1], "filing_date": r[2],
             "filer_name": r[3], "filer_cik": r[4], "subject_name": r[5],
             "subject_cik": r[6], "filing_url": r[7]}
            for r in rows
        ]
    finally:
        s.close()


def activist_stats(days: int = 30) -> dict:
    s = get_session()
    try:
        row = s.execute(text(f"""
            SELECT
                COUNT(*) FILTER (WHERE form_type = 'SCHEDULE 13D') AS cnt_13d,
                COUNT(*) FILTER (WHERE form_type = 'SCHEDULE 13D/A') AS cnt_13d_a,
                COUNT(*) FILTER (WHERE form_type = 'SCHEDULE 13G') AS cnt_13g,
                COUNT(*) FILTER (WHERE form_type = 'SCHEDULE 13G/A') AS cnt_13g_a,
                COUNT(DISTINCT filer_cik) AS unique_filers
            FROM {SCHEMA}.activist_filing
            WHERE filing_date >= CURRENT_DATE - make_interval(days => :days)
        """), {"days": int(days)}).fetchone()
        return {
            "cnt_13d": row[0] or 0, "cnt_13d_a": row[1] or 0,
            "cnt_13g": row[2] or 0, "cnt_13g_a": row[3] or 0,
            "unique_filers": row[4] or 0,
        }
    finally:
        s.close()


def get_treemap_data(min_value: int = 0, fund_filter: str = "", limit: int = 500) -> list[dict]:
    """Top holdings for the Plotly treemap — grouped by fund → security.

    Includes YTD return from liquidround.security_returns (populated by
    scripts/sync_security_returns.py) when available.
    """
    s = get_session()
    try:
        where = ["s.table_value_total IS NOT NULL"]
        params = {"lim": limit}
        if min_value > 0:
            where.append("i.value >= :min_val")
            params["min_val"] = min_value
        if fund_filter:
            where.append("LOWER(c.filingmanager_name) LIKE LOWER(:fund)")
            params["fund"] = f"%{fund_filter}%"
        rows = s.execute(text(f"""
            SELECT c.filingmanager_name AS fund,
                   i.name_of_issuer AS security,
                   SUM(i.value) AS total_value,
                   sr.return_ytd,
                   sr.ticker
            FROM {SCHEMA}.infotable i
            JOIN {SCHEMA}.coverpage c ON i.accession_number = c.accession_number
            JOIN {SCHEMA}.summarypage s ON c.accession_number = s.accession_number
            LEFT JOIN liquidround.security_returns sr ON i.cusip = sr.cusip
            WHERE {' AND '.join(where)}
            GROUP BY c.filingmanager_name, i.name_of_issuer, sr.return_ytd, sr.ticker
            ORDER BY SUM(i.value) DESC
            LIMIT :lim
        """), params).fetchall()
        return [
            {
                "fund": r[0],
                "security": r[1],
                "value": float(r[2]),
                "return_ytd": float(r[3]) if r[3] is not None else None,
                "ticker": r[4],
            }
            for r in rows
        ]
    finally:
        s.close()
