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


def configured_admin_emails() -> frozenset[str]:
    """Return normalized emails granted administration by deployment config."""
    return frozenset(
        item.strip().lower()
        for item in os.getenv("ADMIN_EMAILS", "").split(",")
        if item.strip()
    )


def is_configured_admin_email(email: str) -> bool:
    return email.strip().lower() in configured_admin_emails()


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
    normalized_email = email.lower().strip()
    pw_hash = hash_password(password) if password else None
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                INSERT INTO liquidround.users
                    (email, password_hash, google_id, display_name, is_admin)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING user_id, email, display_name, is_admin, created_at
                """,
                (
                    normalized_email,
                    pw_hash,
                    google_id,
                    display_name,
                    is_configured_admin_email(normalized_email),
                ),
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
        return ensure_configured_admin(user)
    return None


def link_google_id(email: str, google_id: str):
    """Link Google to the existing email account and return that same user."""
    if not email or not google_id:
        return None
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "UPDATE liquidround.users SET google_id = %s, updated_at = NOW() "
            "WHERE lower(email) = %s AND (google_id IS NULL OR google_id = %s) "
            "RETURNING *",
            (google_id, email.lower().strip(), google_id),
        )
        row = cur.fetchone()
        if not row:
            logger.warning("Google identity could not be linked to the existing email account")
            return None
        # Let the surrounding connection commit before a configured-admin
        # promotion opens its own transaction in ``resolve_google_user``.
        return _user_dict(row)


def ensure_configured_admin(user: Optional[Dict]) -> Optional[Dict]:
    """Promote configured operator emails and return the refreshed user dict."""
    if not user or user.get("is_admin") or not is_configured_admin_email(user.get("email", "")):
        return user
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "UPDATE liquidround.users SET is_admin = TRUE, updated_at = NOW() "
            "WHERE user_id = %s RETURNING *",
            (user["user_id"],),
        )
        row = cur.fetchone()
        return _user_dict(row) if row else user


def resolve_google_user(
    *,
    google_id: str,
    email: str,
    display_name: str = "",
    email_verified: bool | str | int = False,
) -> Optional[Dict]:
    """Resolve Google SSO onto one canonical email account."""
    if not email:
        raise ValueError("Google did not provide email")
    if email_verified not in {True, "true", "True", 1}:
        raise ValueError("Google email is not verified")

    user = get_user_by_google_id(google_id) if google_id else None
    if not user:
        user = get_user_by_email(email)
        if user and google_id:
            user = link_google_id(email, google_id)
        elif not user:
            user = create_user(
                email=email,
                google_id=google_id or None,
                display_name=display_name or None,
            )
    return ensure_configured_admin(user)


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


def send_password_reset_email(email: str, token: str, base_url: str) -> dict:
    """Send a password reset link via Postmark."""
    import requests as _req

    api_token = os.getenv("POSTMARK_API_TOKEN")
    if not api_token:
        logger.error("POSTMARK_API_TOKEN not set — cannot send reset email")
        return {"ok": False, "error": "POSTMARK_API_TOKEN not set"}

    from_email = os.getenv("FROM_EMAIL", "info@liquidround.com")
    reset_link = f"{base_url}/reset?token={token}"

    html = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
      <div style="text-align: center; margin-bottom: 32px;">
        <div style="display: inline-block; width: 48px; height: 48px; border-radius: 12px; background: linear-gradient(135deg, #2563EB, #60A5FA); color: #fff; font-weight: 800; font-size: 18px; line-height: 48px;">LR</div>
        <p style="font-size: 18px; font-weight: 700; color: #1E293B; margin: 8px 0 0;">LiquidRound</p>
      </div>
      <h2 style="font-size: 20px; font-weight: 600; color: #1E293B; margin-bottom: 12px;">Reset your password</h2>
      <p style="color: #475569; font-size: 14px; line-height: 1.6;">
        We received a request to reset your password. Click the button below to choose a new one. This link expires in 1 hour.
      </p>
      <div style="text-align: center; margin: 28px 0;">
        <a href="{reset_link}" style="display: inline-block; background: #2563EB; color: #ffffff; padding: 12px 32px; border-radius: 8px; font-weight: 600; font-size: 14px; text-decoration: none;">Reset Password</a>
      </div>
      <p style="color: #94A3B8; font-size: 12px; line-height: 1.5;">
        If you didn't request this, you can safely ignore this email. Your password won't be changed.
      </p>
      <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;">
      <p style="color: #94A3B8; font-size: 11px;">Predictive Labs Ltd &middot; LiquidRound</p>
    </div>
    """

    resp = _req.post(
        "https://api.postmarkapp.com/email",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": api_token,
        },
        json={
            "From": from_email,
            "To": email,
            "Subject": "Reset your LiquidRound password",
            "HtmlBody": html,
            "MessageStream": "outbound",
        },
        timeout=15,
    )

    if resp.status_code == 200:
        logger.info(f"Password reset email sent to {email}")
        return {"ok": True}
    else:
        logger.error(f"Postmark error: {resp.status_code} {resp.text}")
        return {"ok": False, "error": resp.text}


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
