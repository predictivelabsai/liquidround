"""Small process-local rate limiter for anonymous lead-magnet endpoints."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


_events: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def allow(key: str, *, limit: int = 10, window_seconds: int = 3600) -> bool:
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _events[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def client_key(request, scope: str) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    host = forwarded or (request.client.host if request.client else "unknown")
    return f"{scope}:{host}"
