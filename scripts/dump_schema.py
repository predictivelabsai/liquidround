"""Regenerate sql/schema.json from the live database.

Used by routes/analytics.py (text-to-SQL) to tell the LLM what tables/columns
exist. Covers the `liquidround` and `pehero` schemas. Run after schema changes:

    python -m scripts.dump_schema
"""
from __future__ import annotations

import json
from pathlib import Path

from utils.database import get_conn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sql" / "schema.json"
SCHEMAS = ("liquidround", "pehero")
ENUM_MAX = 20  # text columns with <= this many distinct values get an enum hint

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

                enums: dict = {}
                if row_count:
                    for col, dtype in cols:
                        if dtype not in _TEXTY:
                            continue
                        try:
                            cur.execute(
                                f'SELECT DISTINCT "{col}" FROM {schema}."{table}" '
                                f'WHERE "{col}" IS NOT NULL LIMIT {ENUM_MAX + 1}'
                            )
                            vals = [r[0] for r in cur.fetchall()]
                            # only genuine categoricals: few, short, distinct values
                            if 0 < len(vals) <= ENUM_MAX and all(len(str(v)) <= 40 for v in vals):
                                enums[col] = sorted(vals)
                        except Exception:
                            conn.rollback()

                out[qualified] = {"columns": columns, "row_count": row_count, "enums": enums}

    OUT.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT} — {len(out)} tables")


if __name__ == "__main__":
    main()
