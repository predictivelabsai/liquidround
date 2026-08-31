"""User-scoped prompt overrides with a global system-prompt baseline."""

from __future__ import annotations

from psycopg2.extras import RealDictCursor

from utils.database import get_conn


# These agents can delegate execution or control external publication. Their
# instructions remain global and only administrators may change them.
ADMIN_PROTECTED_SKILLS = frozenset({
    "hermes_orchestrator",
    "ir_publish",
    "ir_distribute",
})


def is_admin_protected_skill(slug: str) -> bool:
    return slug in ADMIN_PROTECTED_SKILLS


def prompt_scope_user_id(slug: str, user_id: str | None) -> str | None:
    """Return the storage scope: protected skills are always global."""
    return None if is_admin_protected_skill(slug) else user_id


def save_prompt_version(
    slug: str,
    content: str,
    changed_by: str = "web-editor",
    *,
    user_id: str | None = None,
) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO liquidround.prompt_versions "
            "(slug, content, changed_by, status, user_id) "
            "VALUES (%s, %s, %s, 'published', %s) RETURNING id",
            (slug, content, changed_by, user_id),
        )
        return cur.fetchone()[0]


def _scope_clause(user_id: str | None) -> tuple[str, tuple]:
    if user_id:
        return "user_id = %s", (user_id,)
    return "user_id IS NULL", ()


def count_prompt_versions(slug: str, *, user_id: str | None = None) -> int:
    scope_sql, scope_params = _scope_clause(user_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT COUNT(*) FROM liquidround.prompt_versions "
            f"WHERE slug = %s AND {scope_sql}",
            (slug, *scope_params),
        )
        return cur.fetchone()[0]


def get_latest_prompt(slug: str, *, user_id: str | None = None) -> str | None:
    """Return a user's latest override, falling back to the global version."""
    with get_conn() as conn:
        cur = conn.cursor()
        if user_id:
            cur.execute(
                "SELECT content FROM liquidround.prompt_versions "
                "WHERE slug = %s AND status = 'published' "
                "AND (user_id = %s OR user_id IS NULL) "
                "ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END, id DESC LIMIT 1",
                (slug, user_id, user_id),
            )
        else:
            cur.execute(
                "SELECT content FROM liquidround.prompt_versions "
                "WHERE slug = %s AND status = 'published' AND user_id IS NULL "
                "ORDER BY id DESC LIMIT 1",
                (slug,),
            )
        row = cur.fetchone()
        if not row:
            return None
        return row[0] if isinstance(row, (tuple, list)) else row["content"]


def get_prompt_versions(
    slug: str,
    limit: int = 50,
    *,
    user_id: str | None = None,
) -> list[dict]:
    scope_sql, scope_params = _scope_clause(user_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT COUNT(*) FROM liquidround.prompt_versions "
            f"WHERE slug = %s AND {scope_sql}",
            (slug, *scope_params),
        )
        total = cur.fetchone()[0]

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id, slug, content, changed_by, created_at "
            f"FROM liquidround.prompt_versions WHERE slug = %s AND {scope_sql} "
            "ORDER BY id DESC LIMIT %s",
            (slug, *scope_params, limit),
        )
        rows = cur.fetchall()

        versions = []
        for i, r in enumerate(rows):
            versions.append({
                "id": r["id"],
                "version": total - i,
                "slug": r["slug"],
                "preview": r["content"][:200],
                "changed_by": r["changed_by"] or "",
                "created_at": r["created_at"].isoformat() if r["created_at"] else "",
            })
        return versions


def get_prompt_version(version_id: int, *, user_id: str | None = None) -> dict | None:
    scope_sql, scope_params = _scope_clause(user_id)
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id, slug, content, changed_by, created_at "
            f"FROM liquidround.prompt_versions WHERE id = %s AND {scope_sql}",
            (version_id, *scope_params),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "slug": row["slug"],
            "content": row["content"],
            "changed_by": row["changed_by"] or "",
            "created_at": row["created_at"].isoformat() if row["created_at"] else "",
        }


def seed_prompt_versions():
    """Seed prompt_versions from filesystem if table is empty."""
    from pathlib import Path
    prompts_dir = Path(__file__).resolve().parent.parent / "prompts" / "system"

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM liquidround.prompt_versions")
        if cur.fetchone()[0] > 0:
            return 0

        count = 0
        for md in sorted(prompts_dir.glob("*.md")):
            slug = md.stem
            content = md.read_text()
            cur.execute(
                "INSERT INTO liquidround.prompt_versions "
                "(slug, content, changed_by, status, user_id) "
                "VALUES (%s, %s, 'seed', 'published', NULL)",
                (slug, content),
            )
            count += 1
        return count
