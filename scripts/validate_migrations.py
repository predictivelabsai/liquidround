"""Validate ordered SQL migration filenames and basic safety invariants."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
NAME = re.compile(r"^(?P<number>\d{2})(?P<suffix>[a-z]?)-[a-z0-9-]+\.sql$")


def validate() -> list[str]:
    errors: list[str] = []
    stems: set[str] = set()
    files = sorted(path for path in SQL_DIR.glob("*.sql") if path.name != "create-tables.sql")
    for path in files:
        match = NAME.match(path.name)
        if not match:
            errors.append(f"Invalid migration filename: {path.name}")
            continue
        key = match.group("number") + match.group("suffix")
        if key in stems:
            errors.append(f"Duplicate migration order key: {key}")
        stems.add(key)
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bDROP\s+(?:SCHEMA|DATABASE)\b", text, re.IGNORECASE):
            errors.append(f"Destructive broad DROP in {path.name}")
    if not files:
        errors.append("No migrations found")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("\n".join(errors))
        return 1
    print("SQL migration manifest is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
