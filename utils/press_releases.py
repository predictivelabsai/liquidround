"""Press release data layer — queries the finespresso public.news table."""
from __future__ import annotations

import logging
from typing import Optional

from utils.database import get_conn

log = logging.getLogger(__name__)


def search_press_releases(
    query: str = "",
    ticker: str = "",
    event_type: str = "",
    publisher: str = "",
    days: int = 30,
    limit: int = 50,
) -> list[dict]:
    """Search press releases with optional filters."""
    where = ["published_date >= CURRENT_DATE - make_interval(days => %(days)s)"]
    params = {"days": days, "limit": limit}

    if query:
        where.append("(title ILIKE %(q)s OR content ILIKE %(q)s)")
        params["q"] = f"%{query}%"
    if ticker:
        where.append("(yf_ticker ILIKE %(ticker)s OR ticker ILIKE %(ticker)s)")
        params["ticker"] = f"%{ticker}%"
    if event_type:
        where.append("event = %(event)s")
        params["event"] = event_type
    if publisher:
        where.append("publisher ILIKE %(pub)s")
        params["pub"] = f"%{publisher}%"

    sql = f"""
        SELECT id, title, company, yf_ticker, ticker, published_date,
               event, publisher, industry,
               COALESCE(title_en, title) AS display_title,
               LEFT(COALESCE(content_en, content, ''), 300) AS snippet,
               predicted_side, predicted_move, reason
        FROM public.news
        WHERE {' AND '.join(where)}
        ORDER BY published_date DESC
        LIMIT %(limit)s
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_press_release(news_id: int) -> Optional[dict]:
    """Get a single press release by ID."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, title, company, yf_ticker, ticker, published_date,
                   event, publisher, industry,
                   COALESCE(title_en, title) AS display_title,
                   COALESCE(content_en, content) AS full_content,
                   predicted_side, predicted_move, reason, link
            FROM public.news WHERE id = %s
        """, (news_id,))
        if not cur.rowcount:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, cur.fetchone()))


def get_event_types() -> list[str]:
    """Get distinct event types for the filter dropdown."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT event FROM public.news
            WHERE event IS NOT NULL AND event != ''
            ORDER BY event
        """)
        return [r[0] for r in cur.fetchall()]


def get_publishers() -> list[str]:
    """Get distinct publishers for the filter dropdown."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT publisher FROM public.news
            WHERE publisher IS NOT NULL AND publisher != ''
            ORDER BY publisher
        """)
        return [r[0] for r in cur.fetchall()]


def press_release_stats(days: int = 30) -> dict:
    """Summary stats for the press releases page header."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS total,
                   COUNT(DISTINCT company) FILTER (WHERE company IS NOT NULL) AS companies,
                   COUNT(DISTINCT publisher) AS sources,
                   COUNT(*) FILTER (WHERE event = 'mergers_acquisitions') AS ma_count,
                   COUNT(*) FILTER (WHERE event = 'earnings_releases_and_operating_results' OR event = 'financial_results') AS earnings_count
            FROM public.news
            WHERE published_date >= CURRENT_DATE - make_interval(days => %s)
        """, (days,))
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, cur.fetchone()))


def text_to_sql_query(sql: str) -> list[dict]:
    """Execute a read-only SQL query against the news table.
    Only SELECT statements are allowed."""
    sql_clean = sql.strip().rstrip(";")
    if not sql_clean.upper().startswith("SELECT"):
        return [{"error": "Only SELECT queries are allowed"}]
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql_clean)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, row)) for row in rows[:100]]
