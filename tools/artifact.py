"""Artifact emission helper — keeps the `__ARTIFACT__` contract in one place."""
from __future__ import annotations

import json
from typing import Any

ARTIFACT_PREFIX = "__ARTIFACT__"


def emit(*, kind: str, title: str, subtitle: str = "",
         columns: list[str] | None = None,
         rows: list[dict] | None = None,
         items: list[dict] | None = None,
         body_md: str | None = None,
         summary: dict[str, Any] | None = None,
         **extra: Any) -> str:
    """Return the agreed SSE-digestible artifact payload string.

    Consumers look for the ARTIFACT_PREFIX and JSON-parse the rest.
    """
    payload: dict[str, Any] = {"kind": kind, "title": title}
    if subtitle:
        payload["subtitle"] = subtitle
    if columns is not None:
        payload["columns"] = columns
    if rows is not None:
        payload["rows"] = rows
    if items is not None:
        payload["items"] = items
    if body_md is not None:
        payload["body_md"] = body_md
    if summary is not None:
        payload["summary"] = summary
    payload.update(extra)
    return ARTIFACT_PREFIX + json.dumps(payload, default=str)


def is_artifact(s: str) -> bool:
    return isinstance(s, str) and s.startswith(ARTIFACT_PREFIX)


def parse_artifact(s: str) -> dict:
    if not is_artifact(s):
        raise ValueError("not an artifact payload")
    return json.loads(s[len(ARTIFACT_PREFIX):])
