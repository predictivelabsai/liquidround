"""
User preferences CRUD for LiquidRound M&A deal preferences.
"""
import json
import logging
from typing import Dict, Optional

from psycopg2.extras import RealDictCursor
from utils.database import get_conn

logger = logging.getLogger(__name__)


def get_preferences(user_id: str) -> Optional[Dict]:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM liquidround.user_preferences WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_account(user_id: str, *, company_name: str = "", job_title: str = "",
                   phone: str = "", country: str = "", city: str = "",
                   currency: str = "EUR", language: str = "en") -> bool:
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.user_preferences
                    (user_id, company_name, job_title, phone, country, city, currency, language, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    job_title = EXCLUDED.job_title,
                    phone = EXCLUDED.phone,
                    country = EXCLUDED.country,
                    city = EXCLUDED.city,
                    currency = EXCLUDED.currency,
                    language = EXCLUDED.language,
                    updated_at = NOW()
            """, (user_id, company_name, job_title, phone, country, city, currency, language))
        return True
    except Exception as e:
        logger.error(f"upsert_account error: {e}")
        return False


def upsert_deal_prefs(user_id: str, *, deal_size_min: float = None, deal_size_max: float = None,
                      sectors: list = None, geographies: list = None, deal_types: list = None,
                      rev_min: float = None, rev_max: float = None,
                      ebitda_min: float = None, ebitda_max: float = None) -> bool:
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.user_preferences
                    (user_id, deal_size_min_eur, deal_size_max_eur,
                     preferred_sectors, preferred_geographies, preferred_deal_types,
                     target_revenue_min_eur, target_revenue_max_eur,
                     target_ebitda_min_eur, target_ebitda_max_eur, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    deal_size_min_eur = EXCLUDED.deal_size_min_eur,
                    deal_size_max_eur = EXCLUDED.deal_size_max_eur,
                    preferred_sectors = EXCLUDED.preferred_sectors,
                    preferred_geographies = EXCLUDED.preferred_geographies,
                    preferred_deal_types = EXCLUDED.preferred_deal_types,
                    target_revenue_min_eur = EXCLUDED.target_revenue_min_eur,
                    target_revenue_max_eur = EXCLUDED.target_revenue_max_eur,
                    target_ebitda_min_eur = EXCLUDED.target_ebitda_min_eur,
                    target_ebitda_max_eur = EXCLUDED.target_ebitda_max_eur,
                    updated_at = NOW()
            """, (user_id, deal_size_min, deal_size_max,
                  json.dumps(sectors or []), json.dumps(geographies or []),
                  json.dumps(deal_types or []),
                  rev_min, rev_max, ebitda_min, ebitda_max))
        return True
    except Exception as e:
        logger.error(f"upsert_deal_prefs error: {e}")
        return False


def get_digest_recipients() -> list[Dict]:
    """Return all users who opted in to weekly digest emails.
    Users without a preferences row default to opted-in."""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT DISTINCT ON (u.email) u.user_id, u.email, u.display_name
            FROM liquidround.users u
            LEFT JOIN liquidround.user_preferences p ON p.user_id = u.user_id
            WHERE COALESCE(p.notify_weekly_digest, TRUE) = TRUE
              AND u.email IS NOT NULL
              AND u.email != ''
            ORDER BY u.email, u.id
        """)
        return [dict(r) for r in cur.fetchall()]


def upsert_notifications(user_id: str, *, notify_new_deals: bool = True,
                         notify_price_changes: bool = True,
                         notify_weekly_digest: bool = True) -> bool:
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.user_preferences
                    (user_id, notify_new_deals, notify_price_changes, notify_weekly_digest, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    notify_new_deals = EXCLUDED.notify_new_deals,
                    notify_price_changes = EXCLUDED.notify_price_changes,
                    notify_weekly_digest = EXCLUDED.notify_weekly_digest,
                    updated_at = NOW()
            """, (user_id, notify_new_deals, notify_price_changes, notify_weekly_digest))
        return True
    except Exception as e:
        logger.error(f"upsert_notifications error: {e}")
        return False
