"""Server-sent-event helpers for LiquidRound's streaming chat endpoint.

Mirrors pehero's chat/sse.py — same event names so a future ported
client-side listener (static/chat.js) can drop in without translation.
"""
from __future__ import annotations

import json
from typing import Any


def event(name: str, data: Any) -> str:
    """Format a single SSE message."""
    return f"event: {name}\ndata: {json.dumps(data, default=str)}\n\n"


AGENT_ROUTE = "agent_route"
TOKEN       = "token"
TOOL_START  = "tool_start"
TOOL_END    = "tool_end"
ARTIFACT    = "artifact_show"
SESSION     = "session"
DONE        = "done"
ERROR       = "error"
