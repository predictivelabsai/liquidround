from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from routes.analytics import _guard_sql
from utils.hermes_agent import run_hermes
from utils.security import (
    safe_upload_target,
    validate_public_url,
    validate_same_origin,
)
from utils.html_sanitizer import sanitize_html


def test_analytics_accepts_only_approved_relations():
    _guard_sql("SELECT sector, count(*) FROM pehero.companies GROUP BY sector LIMIT 20")
    with pytest.raises(ValueError):
        _guard_sql("SELECT email FROM liquidround.users")
    with pytest.raises(ValueError):
        _guard_sql("SELECT api_token FROM pehero.user_integrations")
    with pytest.raises(ValueError):
        _guard_sql("SELECT pg_sleep(10) FROM pehero.companies")
    with pytest.raises(ValueError):
        _guard_sql("WITH removed AS (DELETE FROM pehero.companies RETURNING *) SELECT * FROM removed")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost:5007",
        "http://169.254.169.254/latest/meta-data",
        "file:///etc/passwd",
        "ftp://example.com",
    ],
)
def test_public_url_validator_blocks_ssrf_targets(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_public_url_validator_accepts_public_dns(monkeypatch):
    monkeypatch.setattr(
        "utils.security.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    assert validate_public_url("example.com/about") == "https://example.com/about"


def test_upload_target_is_opaque_and_user_scoped(tmp_path):
    target, document_id = safe_upload_target(tmp_path, "user-123", "../../board.pdf")
    assert target.parent == (tmp_path / "user-123").resolve()
    assert target.name == document_id
    assert document_id.endswith(".pdf")
    assert "board" not in document_id


def test_upload_target_rejects_unsupported_extension(tmp_path):
    with pytest.raises(ValueError):
        safe_upload_target(tmp_path, "user-123", "payload.html")


def test_csrf_same_origin_uses_canonical_origin(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://liquidround.ai")
    good = SimpleNamespace(
        method="POST",
        headers={"origin": "https://liquidround.ai", "sec-fetch-site": "same-origin"},
    )
    bad = SimpleNamespace(
        method="POST",
        headers={"origin": "https://evil.example", "sec-fetch-site": "cross-site"},
    )
    assert validate_same_origin(good, {})
    assert not validate_same_origin(bad, {})


def test_csrf_accepts_explicit_secondary_origin(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://liquidround.ai")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://liquidround.com")
    request = SimpleNamespace(
        method="POST",
        headers={"origin": "https://liquidround.com", "sec-fetch-site": "same-origin"},
    )
    assert validate_same_origin(request, {})


def test_generated_html_sanitizer_removes_active_content():
    rendered = sanitize_html(
        '<p>Hello <strong>deal</strong></p><script>alert(1)</script>'
        '<a href="javascript:alert(2)" onclick="alert(3)">link</a>'
    )
    assert "<strong>deal</strong>" in rendered
    assert "script" not in rendered
    assert "alert" not in rendered
    assert "onclick" not in rendered


def test_hermes_disabled_is_explicit(monkeypatch):
    monkeypatch.setattr("utils.hermes_agent.config.hermes_enabled", False)
    assert "disabled" in run_hermes("analyze this").lower()


def test_live_value_schema_snapshot_is_not_present():
    assert not Path("sql/schema.json").exists()
