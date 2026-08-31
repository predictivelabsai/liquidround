# LiquidRound Skills Management

This document explains how LiquidRound authorizes skill editing, renders the
browser editor, stores versioned instructions, and selects the effective system
prompt at runtime.

> The product calls agent system prompts **skills** in the user interface. The
> implementation still uses `prompt` and `instruction` terminology in several
> module, route, and database names.

## Overview

LiquidRound currently implements a two-role authorization model:

| Capability | Authenticated member | Administrator |
|---|---:|---:|
| Open the Skills directory | Yes | Yes |
| Review any skill | Yes | Yes |
| Edit an ordinary skill | Yes, personal copy | Yes, personal copy |
| View ordinary-skill history | Own versions only | Own versions only |
| Edit an admin-protected skill | No | Yes, global copy |
| View protected-skill history | No | Yes, global versions |
| Revert an editable skill | Yes, within own scope | Yes, within effective scope |

There is no roles or permissions table. The role is derived from
`liquidround.users.is_admin`, while the protected-skill policy is a code-level
allowlist in `utils/prompts.py`.

The three admin-protected skills are:

- `hermes_orchestrator`
- `ir_publish`
- `ir_distribute`

With 32 registered agents, this leaves 29 skills that each signed-in user can
personalize privately.

## Authorization and identity

### Authentication boundary

The beforeware in `main.py` protects `/app/*` and related application routes.
An unauthenticated request to `/app/skills` is redirected to `/signin`. The
public contextual-news and shared-chat routes are separate explicit
exceptions; the Skills routes are not public.

After password or Google login, `routes/auth.py::_session_login()` stores a
small signed-cookie session identity:

```python
session["user"] = {
    "user_id": "...",
    "email": "...",
    "display_name": "...",
    "is_admin": False,
}
```

Authorization decisions use the database-derived `is_admin` value copied into
that session. In production, an empty or missing user is never an
administrator. `LOCAL_AUTH_BYPASS` is test-only; even there, an explicit
non-admin test user remains non-admin.

### Administrator assignment

Administrators are assigned in two complementary ways:

1. `liquidround.users.is_admin` is the persistent source of truth.
2. `ADMIN_EMAILS` is a comma-separated deployment setting that promotes a
   matching normalized email during account creation or successful login.

Migration `sql/21-user-skill-overrides.sql` also promotes the original operator
account so existing installations receive the correct role.

`ADMIN_EMAILS` only promotes accounts; removing an email from the environment
does not demote the existing database row. To revoke administration, update the
database flag and invalidate or refresh the user's existing login session.

### Password and Google identity mapping

Password and Google authentication resolve to the same `users` row:

- Emails are normalized to lowercase.
- Google login requires `email_verified` from Google.
- An existing account with the same email receives the Google `sub` in
  `google_id` rather than creating a duplicate user.
- The session receives the same `user_id` and `is_admin` regardless of the
  authentication method.

This mapping is important because skill ownership is keyed by `user_id`, not by
email or authentication provider.

## Skill-level RBAC

`utils/prompts.py` contains the policy:

```python
ADMIN_PROTECTED_SKILLS = frozenset({
    "hermes_orchestrator",
    "ir_publish",
    "ir_distribute",
})
```

Two helper decisions are used throughout the editor and storage layer:

```python
editable = not is_admin_protected_skill(slug) or is_admin(session)
scope_user_id = None if is_admin_protected_skill(slug) else session_user_id
```

The first decision controls whether the current user may mutate a skill. The
second determines where versions are stored:

- Ordinary skill: `user_id = current user`, including when the current user is
  an administrator.
- Protected skill: `user_id IS NULL`, representing the shared global version.

The server repeats these checks on every save, history, version-read, and
revert endpoint. Hiding browser controls is only a usability measure, not the
security boundary.

## Front-end editor

The FastHTML routes are in `routes/instructions.py`; browser behavior is in
`static/instructions.js`.

### Directory

`GET /app/skills` renders all registered agents and describes each as one of:

- **Personal**: no user override exists yet.
- **Your versions · N**: the user has private versions.
- **Admin controlled**: protected and read-only for the current member.
- **Admin default**: protected and editable by the current administrator.

Legacy `/app/instructions` bookmarks redirect permanently to `/app/skills`.

### Editor modes

`GET /app/skills/{slug}` renders three synchronized views:

1. **Editor** — Quill WYSIWYG, initialized from Markdown using `marked`.
2. **Markdown** — direct source editing.
3. **History** — version list with View and Revert actions.

For a protected skill viewed by a non-admin:

- Quill is initialized with `readOnly: true` and no toolbar.
- The Markdown textarea is read-only.
- History and Save controls are omitted.
- A visible Admin controlled notice explains the restriction.

The browser converts a subset of Quill formatting back to Markdown before
saving: headings, ordered and unordered lists, bold, italic, inline code,
links, and code blocks. The Markdown source remains the canonical value sent to
the server.

### Browser API

| Method and route | Purpose | Authorization and scope |
|---|---|---|
| `GET /app/skills` | Skill directory | Signed-in users |
| `GET /app/skills/{slug}` | Editor or read-only review | Signed-in users |
| `POST /app/skills/{slug}` | Save a new published version | Personal scope, or admin for protected skills |
| `GET /app/api/prompt-versions/{slug}` | List history | Same editable scope |
| `GET /app/api/prompt-version/{id}` | Load one version | Own version; admins may also load protected global versions |
| `POST /app/api/prompt-versions/{slug}/revert` | Copy an old value into a new version | Same editable scope |

Saves reject unknown agents, empty content, and content larger than 100,000
characters. A member attempting to mutate a protected skill receives HTTP 403.
Authenticated browser mutations also pass the same-origin/CSRF beforeware in
`main.py` and `utils/security.py`.

Revert is append-only: it creates a new published row containing the selected
older content. It does not overwrite or delete history.

## Database tables

### `liquidround.users`

Created by `sql/02-create-users.sql` and the baseline schema.

| Column | Relevant purpose |
|---|---|
| `user_id UUID` | Stable skill owner and session identity |
| `email VARCHAR(255)` | Unique normalized login email |
| `password_hash VARCHAR(255)` | Optional bcrypt password credential |
| `google_id VARCHAR(255)` | Optional unique Google subject identifier |
| `display_name VARCHAR(255)` | UI display value |
| `is_admin BOOLEAN` | Persistent administrator flag |
| `is_active BOOLEAN` | Login eligibility |
| `created_at`, `updated_at` | Account audit timestamps |

A user can have both `password_hash` and `google_id`, which is how password and
Google SSO access the same personal skill history.

### `liquidround.prompt_versions`

The table evolved through three migrations:

- `sql/05-prompt-versions.sql` creates the append-only prompt history.
- `sql/20-security-and-agent-runs.sql` adds `status` and the published index.
- `sql/21-user-skill-overrides.sql` adds nullable `user_id` ownership.

The effective shape is:

| Column | Purpose |
|---|---|
| `id BIGSERIAL` | Monotonic version identifier |
| `slug TEXT` | Agent/skill slug |
| `content TEXT` | Canonical Markdown system instructions |
| `changed_by TEXT` | Actor email or seed/revert label |
| `status TEXT` | `published` for versions used by the editor/runtime |
| `user_id UUID NULL` | Owner; `NULL` means global baseline |
| `created_at TIMESTAMPTZ` | Version creation time |

`user_id` references `liquidround.users(user_id)` with `ON DELETE CASCADE`.
The partial runtime index is:

```sql
CREATE INDEX ix_prompt_versions_user_published
ON liquidround.prompt_versions (user_id, slug, id DESC)
WHERE status = 'published';
```

There is intentionally no unique constraint on `(user_id, slug)`: every save
creates another history row. The current version is the newest applicable
published row.

## Effective prompt selection

The runtime path is implemented by `agents/base.py`, `utils/prompts.py`, and
`utils/request_context.py`.

```text
authenticated chat request
        │
        ▼
request ContextVar receives session user_id
        │
        ▼
cached_agent(slug, user_id)
        │
        ▼
load shared LiquidRound context
        │
        ├── load prompts/system/{slug}.md as deployment fallback
        │
        └── query prompt_versions
              ├── ordinary skill: newest user version
              ├── otherwise: newest global version
              └── protected skill: global version only
```

For an ordinary skill, `get_latest_prompt()` orders the user's published row
ahead of a global published row. If neither exists—or the database is
unavailable—the checked-in `prompts/system/{slug}.md` file remains the fallback.
Shared context from `prompts/shared/liquidround_context.md` is prepended in all
cases.

Agents are cached by both slug and effective user identity, preventing one
user's built prompt graph from being reused for another user. A successful Save
or Revert clears the agent cache so the next chat rebuilds with the new
instructions. Both the primary SSE chat path and legacy chat path set and reset
the request-scoped user identity.

## Security properties

- Authentication is required for all Skills pages and APIs.
- Authorization is enforced server-side for every mutation and history read.
- Personal version queries always include the current `user_id` scope.
- Ordinary members cannot fall back to another user's version by numeric ID.
- Only administrators may read or mutate global protected-skill versions.
- Browser mutations are protected by same-origin/CSRF checks.
- Prompt content is length-validated and stored through parameterized SQL.
- Agent graphs are cached per user and invalidated after changes.
- Verified Google email linking prevents duplicate password/SSO identities.

Relevant automated coverage lives in:

- `tests/test_user_skills.py`
- `tests/test_security_hardening.py`
- `tests/test_e2e_smoke.py`

## Operational changes

### Add or remove an admin-protected skill

1. Update `ADMIN_PROTECTED_SKILLS` in `utils/prompts.py`.
2. Confirm the skill slug exists in `agents/registry.py`.
3. Add or update RBAC and prompt-scope tests in `tests/test_user_skills.py`.
4. Validate member read-only behavior and administrator editing locally.

Because protected versions use `user_id IS NULL`, changing a formerly personal
skill to protected does not automatically promote a user's private version to
the global baseline.

### Add or revoke an administrator

- Add an email to `ADMIN_EMAILS` to promote it on creation or next successful
  login.
- For immediate assignment, update `liquidround.users.is_admin` through an
  approved administration workflow.
- For revocation, remove the email from `ADMIN_EMAILS`, set `is_admin = FALSE`
  in the database, and refresh active sessions.

### Seed global baselines

`utils/prompts.py::seed_prompt_versions()` can seed checked-in prompt files as
global published versions when `prompt_versions` is completely empty. Normal
deployments continue to retain existing database history.

## Current limitations

The current design is intentionally simple:

- It supports member and administrator roles only; there are no organization,
  team, reviewer, or per-skill grant tables.
- Protected-skill policy is deployed in code, not editable in the UI.
- `changed_by` is descriptive text rather than an immutable actor foreign key.
- The editor publishes immediately; there is no draft/approval workflow.
- Quill and `marked` are loaded from public CDNs.

If LiquidRound later needs workspace-specific skill ownership or approval
workflows, introduce explicit role/permission and workspace-skill tables rather
than expanding the hard-coded allowlist.
