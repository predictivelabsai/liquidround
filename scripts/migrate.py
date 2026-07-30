"""Apply idempotent LiquidRound SQL migrations with checksum tracking."""
from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.validate_migrations import SQL_DIR, validate
from utils.database import get_conn


def _files() -> list[Path]:
    return [SQL_DIR / "create-tables.sql", *sorted(
        path for path in SQL_DIR.glob("*.sql") if path.name != "create-tables.sql"
    )]


def main() -> int:
    errors = validate()
    if errors:
        raise RuntimeError("; ".join(errors))
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS liquidround")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS liquidround.schema_migrations (
                filename TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.commit()
        for path in _files():
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            cur.execute(
                "SELECT checksum FROM liquidround.schema_migrations WHERE filename = %s",
                (path.name,),
            )
            row = cur.fetchone()
            if row:
                recorded = row[0] if isinstance(row, (tuple, list)) else row["checksum"]
                if recorded != checksum:
                    raise RuntimeError(f"Applied migration changed: {path.name}")
                continue
            cur.execute(sql)
            cur.execute(
                "INSERT INTO liquidround.schema_migrations (filename, checksum) VALUES (%s, %s)",
                (path.name, checksum),
            )
            conn.commit()
            print(f"Applied {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
