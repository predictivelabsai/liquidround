"""Shared security controls for authentication, administration and uploads."""
from __future__ import annotations

import ipaddress
import os
import secrets
import socket
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

from starlette.responses import JSONResponse, RedirectResponse


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
UPLOAD_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".pptx", ".ppt"}
UPLOAD_MAX_BYTES = int(os.getenv("UPLOAD_MAX_BYTES", str(25 * 1024 * 1024)))


def public_base_url() -> str:
    """Return the configured canonical origin without a trailing slash."""
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        parsed = urlparse(configured)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("PUBLIC_BASE_URL must be an absolute http(s) URL")
        return configured
    return "http://localhost:5007"


def is_local_auth_bypass() -> bool:
    return (
        os.getenv("ENVIRONMENT", "").lower() != "production"
        and os.getenv("LOCAL_AUTH_BYPASS", "").lower() in {"1", "true", "yes"}
    )


def is_admin(session: dict | None) -> bool:
    """Use the database-backed admin flag; local bypass remains test-only."""
    if is_local_auth_bypass():
        return True
    user = (session or {}).get("user") or {}
    return bool(user.get("is_admin"))


def require_admin_response(request, session):
    if is_admin(session):
        return None
    accepts_json = "application/json" in request.headers.get("accept", "")
    if accepts_json or request.method in UNSAFE_METHODS:
        return JSONResponse({"error": "Administrator access required"}, status_code=403)
    return RedirectResponse("/app", status_code=303)


def validate_same_origin(request, session: dict | None = None) -> bool:
    """Protect authenticated browser mutations using Fetch Metadata + Origin."""
    if request.method.upper() not in UNSAFE_METHODS:
        return True
    fetch_site = request.headers.get("sec-fetch-site", "").lower()
    if fetch_site in {"cross-site", "none"}:
        return False
    origin = request.headers.get("origin")
    if not origin:
        # Non-browser clients need an explicit CSRF token instead of relying on
        # a missing Origin header.
        supplied = request.headers.get("x-csrf-token", "")
        expected = (session or {}).get("csrf_token", "")
        return bool(supplied and expected and secrets.compare_digest(supplied, expected))
    actual = urlparse(origin)
    configured = {
        public_base_url(),
        *(
            item.strip().rstrip("/")
            for item in os.getenv("ALLOWED_ORIGINS", "").split(",")
            if item.strip()
        ),
    }
    allowed = {
        (parsed.scheme, parsed.netloc)
        for parsed in (urlparse(value) for value in configured)
        if parsed.scheme in {"http", "https"} and parsed.netloc
    }
    return (actual.scheme, actual.netloc) in allowed


def ensure_csrf_token(session: dict) -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def safe_upload_target(root: Path, user_id: str, filename: str) -> tuple[Path, str]:
    """Create an opaque per-user storage path and return it with the document id."""
    ext = Path(filename or "").suffix.lower()
    if ext not in UPLOAD_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext or 'none'}")
    document_id = secrets.token_hex(16) + ext
    user_root = root / str(user_id)
    user_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = (user_root / document_id).resolve()
    if target.parent != user_root.resolve():
        raise ValueError("Invalid upload path")
    return target, document_id


def _is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_url(url: str) -> str:
    """Normalize a URL and reject local, private, metadata and non-http targets."""
    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL is required")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Invalid public URL")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("Local network URLs are not allowed")
    try:
        addresses = {
            info[4][0]
            for info in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        }
    except socket.gaierror as exc:
        raise ValueError("URL hostname could not be resolved") from exc
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise ValueError("Private or reserved network URLs are not allowed")
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{host}{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def validate_redirect_url(base: str, location: str) -> str:
    return validate_public_url(urljoin(base, location))
