from __future__ import annotations

from types import SimpleNamespace

import pytest

from agents.base import cached_agent, load_system_prompt
from routes.instructions import (
    _can_edit,
    _scope_for,
    ar,
    api_prompt_version,
    instruction_save,
)
from utils.auth import is_configured_admin_email, resolve_google_user
from utils.prompts import ADMIN_PROTECTED_SKILLS
from utils.request_context import reset_current_user_id, set_current_user_id


class JsonRequest:
    def __init__(self, payload: dict):
        self.payload = payload

    async def json(self):
        return self.payload


def _session(user_id: str = "11111111-1111-1111-1111-111111111111", *, admin=False):
    return {
        "user": {
            "user_id": user_id,
            "email": "owner@example.com",
            "is_admin": admin,
        }
    }


def test_only_three_operational_skills_are_admin_protected():
    assert ADMIN_PROTECTED_SKILLS == {
        "hermes_orchestrator",
        "ir_publish",
        "ir_distribute",
    }


def test_skill_editor_get_does_not_shadow_save_post():
    matching_methods = [
        methods
        for _handler, path, methods, *_rest in ar.routes
        if path == "/app/skills/{slug}"
    ]
    assert matching_methods == [["GET"], ["POST"]]


def test_ordinary_skill_scope_is_the_signed_in_user():
    session = _session()
    assert _can_edit(session, "target_scanner")
    assert _scope_for(session, "target_scanner") == session["user"]["user_id"]


def test_protected_skill_is_read_only_for_member_and_global_for_admin():
    member = _session()
    admin = _session(admin=True)
    assert not _can_edit(member, "hermes_orchestrator")
    assert _can_edit(admin, "hermes_orchestrator")
    assert _scope_for(admin, "hermes_orchestrator") is None


@pytest.mark.asyncio
async def test_member_saves_personal_skill_version(monkeypatch):
    saved = {}

    def fake_save(slug, content, changed_by, *, user_id):
        saved.update(slug=slug, content=content, changed_by=changed_by, user_id=user_id)
        return 41

    monkeypatch.setattr("routes.instructions.save_prompt_version", fake_save)
    monkeypatch.setattr("routes.instructions.count_prompt_versions", lambda *_a, **_k: 2)

    response = await instruction_save(
        JsonRequest({"content": "# My sourcing rules\nProceed with the supplied mandate."}),
        _session(),
        "target_scanner",
    )

    assert response.status_code == 200
    assert saved["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert saved["changed_by"] == "owner@example.com"


@pytest.mark.asyncio
async def test_member_cannot_save_admin_protected_skill(monkeypatch):
    monkeypatch.setattr(
        "routes.instructions.save_prompt_version",
        lambda *_a, **_k: pytest.fail("protected skill must not be saved"),
    )
    response = await instruction_save(
        JsonRequest({"content": "unsafe override"}),
        _session(),
        "hermes_orchestrator",
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_saves_protected_skill_as_global_version(monkeypatch):
    saved = {}

    def fake_save(slug, content, changed_by, *, user_id):
        saved.update(slug=slug, user_id=user_id)
        return 42

    monkeypatch.setattr("routes.instructions.save_prompt_version", fake_save)
    monkeypatch.setattr("routes.instructions.count_prompt_versions", lambda *_a, **_k: 1)
    response = await instruction_save(
        JsonRequest({"content": "# Safe delegation\nRequire explicit bounded tasks."}),
        _session(admin=True),
        "hermes_orchestrator",
    )
    assert response.status_code == 200
    assert saved == {"slug": "hermes_orchestrator", "user_id": None}


def test_version_lookup_does_not_cross_user_boundary(monkeypatch):
    requested_scopes = []

    def fake_get(_version_id, *, user_id):
        requested_scopes.append(user_id)
        return None

    monkeypatch.setattr("routes.instructions.get_prompt_version", fake_get)
    response = api_prompt_version(_session(), 99)
    assert response.status_code == 404
    assert requested_scopes == ["11111111-1111-1111-1111-111111111111"]


def test_prompt_loader_requests_the_current_user_override(monkeypatch):
    seen = {}

    def fake_latest(slug, *, user_id):
        seen.update(slug=slug, user_id=user_id)
        return "USER OVERRIDE SENTINEL"

    monkeypatch.setattr("utils.prompts.get_latest_prompt", fake_latest)
    prompt = load_system_prompt("target_scanner", user_id="user-a")
    assert "USER OVERRIDE SENTINEL" in prompt
    assert seen == {"slug": "target_scanner", "user_id": "user-a"}


def test_agent_cache_key_uses_request_identity(monkeypatch):
    monkeypatch.setattr("agents.base._cached_agent", lambda slug, user_id: (slug, user_id))
    token = set_current_user_id("user-a")
    try:
        assert cached_agent("target_scanner") == ("target_scanner", "user-a")
    finally:
        reset_current_user_id(token)


def test_configured_admin_email_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "ops@example.com, KALJUVEE@GMAIL.COM")
    assert is_configured_admin_email("kaljuvee@gmail.com")


def test_google_sso_links_to_existing_password_user(monkeypatch):
    password_user = {
        "user_id": "canonical-user",
        "email": "kaljuvee@gmail.com",
        "is_admin": True,
    }
    calls = {"created": 0}

    monkeypatch.setattr("utils.auth.get_user_by_google_id", lambda _sub: None)
    monkeypatch.setattr("utils.auth.get_user_by_email", lambda _email: password_user)
    monkeypatch.setattr("utils.auth.link_google_id", lambda _email, _sub: password_user)
    monkeypatch.setattr(
        "utils.auth.create_user",
        lambda **_kwargs: calls.__setitem__("created", calls["created"] + 1),
    )
    monkeypatch.setattr("utils.auth.ensure_configured_admin", lambda user: user)

    user = resolve_google_user(
        google_id="google-subject",
        email="KALJUVEE@gmail.com",
        display_name="Julian",
        email_verified=True,
    )
    assert user["user_id"] == "canonical-user"
    assert calls["created"] == 0


def test_google_sso_rejects_unverified_email():
    with pytest.raises(ValueError, match="not verified"):
        resolve_google_user(
            google_id="google-subject",
            email="person@example.com",
            email_verified=False,
        )
