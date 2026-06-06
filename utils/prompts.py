"""Prompt version helpers — PostgreSQL audit trail for system prompts."""

from __future__ import annotations

from utils.database import get_conn
from psycopg2.extras import RealDictCursor


def save_prompt_version(slug: str, content: str, changed_by: str = "web-editor") -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO liquidround.prompt_versions (slug, content, changed_by) "
            "VALUES (%s, %s, %s) RETURNING id",
            (slug, content, changed_by),
        )
        return cur.fetchone()[0]


def count_prompt_versions(slug: str) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM liquidround.prompt_versions WHERE slug = %s", (slug,)
        )
        return cur.fetchone()[0]


def get_prompt_versions(slug: str, limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM liquidround.prompt_versions WHERE slug = %s",
            (slug,),
        )
        total = cur.fetchone()[0]

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id, slug, content, changed_by, created_at "
            "FROM liquidround.prompt_versions WHERE slug = %s ORDER BY id DESC LIMIT %s",
            (slug, limit),
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


def get_prompt_version(version_id: int) -> dict | None:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id, slug, content, changed_by, created_at "
            "FROM liquidround.prompt_versions WHERE id = %s",
            (version_id,),
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
                "INSERT INTO liquidround.prompt_versions (slug, content, changed_by) "
                "VALUES (%s, %s, 'seed')",
                (slug, content),
            )
            count += 1
        return count
