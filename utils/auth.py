"""
Authentication module for LiquidRound.
Password hashing (bcrypt), user CRUD, Google OAuth linking, password reset tokens.
"""
import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor

from utils.database import get_conn

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------
def create_user(
    email: str,
    password: str = None,
    google_id: str = None,
    display_name: str = None,
) -> Optional[Dict]:
    pw_hash = hash_password(password) if password else None
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                INSERT INTO liquidround.users (email, password_hash, google_id, display_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING user_id, email, display_name, is_admin, created_at
                """,
                (email.lower().strip(), pw_hash, google_id, display_name),
            )
            row = cur.fetchone()
            if row:
                return _user_dict(row)
    except Exception as e:
        logger.error(f"create_user error: {e}")
    return None


def get_user_by_email(email: str) -> Optional[Dict]:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM liquidround.users WHERE email = %s AND is_active = TRUE",
            (email.lower().strip(),),
        )
        row = cur.fetchone()
        return _user_dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM liquidround.users WHERE user_id = %s AND is_active = TRUE",
            (user_id,),
        )
        row = cur.fetchone()
        return _user_dict(row) if row else None


def get_user_by_google_id(google_id: str) -> Optional[Dict]:
    if not google_id:
        return None
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM liquidround.users WHERE google_id = %s AND is_active = TRUE",
            (google_id,),
        )
        row = cur.fetchone()
        return _user_dict(row) if row else None


def authenticate(email: str, password: str) -> Optional[Dict]:
    user = get_user_by_email(email)
    if not user:
        return None
    pw_hash = user.pop("_password_hash", None)
    if not pw_hash:
        return None  # Google-only account
    if verify_password(password, pw_hash):
        return user
    return None


def link_google_id(email: str, google_id: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE liquidround.users SET google_id = %s, updated_at = NOW() WHERE email = %s",
            (google_id, email.lower().strip()),
        )


# ---------------------------------------------------------------------------
# Password reset tokens
# ---------------------------------------------------------------------------
def create_password_reset_token(email: str) -> Optional[str]:
    user = get_user_by_email(email)
    if not user:
        return None
    token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO liquidround.password_reset_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user["user_id"], token, expires),
        )
    return token


def verify_and_consume_reset_token(token: str) -> Optional[Dict]:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT t.user_id, t.expires_at, u.email
            FROM liquidround.password_reset_tokens t
            JOIN liquidround.users u ON u.user_id = t.user_id
            WHERE t.token = %s AND t.used_at IS NULL
            """,
            (token,),
        )
        row = cur.fetchone()
        if not row:
            return None
        if row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return None
        cur.execute(
            "UPDATE liquidround.password_reset_tokens SET used_at = NOW() WHERE token = %s",
            (token,),
        )
        return {"user_id": str(row["user_id"]), "email": row["email"]}


def update_password(user_id: str, new_password: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE liquidround.users SET password_hash = %s, updated_at = NOW() WHERE user_id = %s",
            (hash_password(new_password), user_id),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _user_dict(row) -> Dict:
    d = dict(row)
    d["user_id"] = str(d["user_id"])
    d["created_at"] = str(d.get("created_at", ""))
    # Keep password hash privately for authenticate(), strip from public dict
    pw = d.pop("password_hash", None)
    d["_password_hash"] = pw
    d.pop("id", None)
    return d
