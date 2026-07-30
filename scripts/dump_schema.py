"""Regenerate an ignored structural schema snapshot from the live database.

This diagnostic excludes row samples and enum values. Runtime analytics uses
an explicit allowlist in routes/analytics.py.

    python -m scripts.dump_schema
"""
from __future__ import annotations

import json
from pathlib import Path

from utils.database import get_conn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sql" / "schema.local.json"
SCHEMAS = ("liquidround", "pehero")

_TYPE_MAP = {
    "integer": "INTEGER", "bigint": "BIGINT", "smallint": "INTEGER",
    "text": "TEXT", "character varying": "TEXT", "character": "TEXT", "citext": "TEXT",
    "date": "DATE", "timestamp with time zone": "TIMESTAMP",
    "timestamp without time zone": "TIMESTAMP", "time without time zone": "TIME",
    "double precision": "REAL", "real": "REAL", "numeric": "NUMERIC",
    "boolean": "BOOLEAN", "jsonb": "JSONB", "json": "JSONB", "bytea": "BYTEA",
    "uuid": "UUID", "ARRAY": "ARRAY",
}
_TEXTY = {"text", "character varying", "character", "citext"}


def main():
    out: dict = {}
    with get_conn() as conn:
        cur = conn.cursor()
        for schema in SCHEMAS:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
                (schema,),
            )
            tables = [r[0] for r in cur.fetchall()]
            for table in tables:
                qualified = f"{schema}.{table}"
                cur.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
                    (schema, table),
                )
                cols = cur.fetchall()
                columns = [{"name": c, "type": _TYPE_MAP.get(d, d.upper())} for c, d in cols]

                cur.execute(f'SELECT count(*) FROM {schema}."{table}"')
                row_count = cur.fetchone()[0]

                out[qualified] = {"columns": columns, "row_count": row_count}

    OUT.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT} — {len(out)} tables")


if __name__ == "__main__":
    main()
