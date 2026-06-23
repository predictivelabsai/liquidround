"""In-process task scheduler — driven by .env, no external cron.

Env vars (all optional — scheduler is disabled when no jobs are configured):

  DIGEST_FREQUENCY  = daily | weekly | hourly | off   (default: daily)
  DIGEST_HOUR_UTC   = 7          (0-23, when to fire daily/weekly jobs)
  DIGEST_WEEKDAY    = 1          (0=Mon … 6=Sun, only used when weekly)

The scheduler starts a single daemon thread on import of `start()`.
It sleeps until the next fire time, executes, then re-sleeps — no
polling, no third-party libs.
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

log = logging.getLogger("scheduler")

# ── Config from .env ─────────────────────────────────────────────────

FREQ = os.getenv("DIGEST_FREQUENCY", "daily").strip().lower()
HOUR = int(os.getenv("DIGEST_HOUR_UTC", "7"))
WEEKDAY = int(os.getenv("DIGEST_WEEKDAY", "1"))  # 0=Mon


def _next_fire(freq: str, hour: int, weekday: int) -> datetime | None:
    """Return the next UTC datetime this job should fire, or None if off."""
    now = datetime.now(timezone.utc)

    if freq == "hourly":
        target = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        return target

    if freq == "daily":
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    if freq == "weekly":
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        days_ahead = (weekday - target.weekday()) % 7
        target += timedelta(days=days_ahead)
        if target <= now:
            target += timedelta(weeks=1)
        return target

    return None  # "off" or unrecognised


# ── Runner ───────────────────────────────────────────────────────────

def _run_digest():
    from utils.digest import send_digest_to_all
    result = send_digest_to_all()
    log.info("Digest result: sent=%s/%s", result.get("sent"), result.get("total"))


def _run_security_returns():
    from scripts.sync_security_returns import main as sync_returns
    result = sync_returns(limit=2000)
    log.info("Security returns: resolved=%s, skipped=%s, errors=%s",
             result.get("resolved"), result.get("skipped"), result.get("errors"))


def _run_deal_candidates():
    from scripts.sync_deal_candidates import main as sync_candidates
    result = sync_candidates()
    log.info("Deal candidates: inserted=%s, updated=%s, total=%s",
             result.get("inserted"), result.get("updated"), result.get("total"))


CANDIDATE_HOUR = max(HOUR - 2, 0)

JOBS = {
    "digest":           {"fn": _run_digest,           "hour": HOUR},
    "security_returns": {"fn": _run_security_returns, "hour": HOUR},
    "deal_candidates":  {"fn": _run_deal_candidates,  "hour": CANDIDATE_HOUR},
}


def _loop(name: str, fn, freq: str, hour: int, weekday: int):
    while True:
        nxt = _next_fire(freq, hour, weekday)
        if nxt is None:
            log.info("[%s] frequency=%s — scheduler exiting", name, freq)
            return
        wait = (nxt - datetime.now(timezone.utc)).total_seconds()
        log.info("[%s] next fire at %s (in %ds), freq=%s", name, nxt.isoformat(), int(wait), freq)
        time.sleep(max(wait, 1))
        try:
            fn()
        except Exception:
            log.exception("[%s] job failed", name)


# ── Public API ───────────────────────────────────────────────────────

_started = False


def start():
    """Start all scheduled jobs as daemon threads. Safe to call multiple
    times (only the first call spawns threads)."""
    global _started
    if _started:
        return
    _started = True

    if FREQ == "off":
        log.info("Scheduler disabled (DIGEST_FREQUENCY=off)")
        return

    log.info("Scheduler starting: DIGEST_FREQUENCY=%s DIGEST_HOUR_UTC=%s DIGEST_WEEKDAY=%s",
             FREQ, HOUR, WEEKDAY)

    for name, cfg in JOBS.items():
        t = threading.Thread(
            target=_loop, args=(name, cfg["fn"], FREQ, cfg["hour"], WEEKDAY),
            daemon=True, name=f"sched-{name}",
        )
        t.start()
