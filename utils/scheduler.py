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


def _run_deal_radar():
    from utils.deal_radar import build_deal_radar
    pairs = build_deal_radar()
    log.info("Deal Radar: scored %d pairs", len(pairs))


def _run_ee_register():
    if datetime.now(timezone.utc).weekday() != 0:  # Monday only
        return
    from scripts.sync_ee_register import main as sync_ee
    result = sync_ee(refresh=False)  # incremental: reuse cached files if fresh
    log.info("EE register: %s", result)


def _run_no_register():
    if datetime.now(timezone.utc).weekday() != 1:  # Tuesday only
        return
    from scripts.sync_no_register import main as sync_no
    result = sync_no(target=3000)  # incremental: limited target count
    log.info("NO register: %s", result)


def _run_dk_register():
    if datetime.now(timezone.utc).weekday() != 2:  # Wednesday only
        return
    from scripts.sync_dk_register import main as sync_dk
    result = sync_dk(target=2000)  # incremental: limited target count
    log.info("DK register: %s", result)


def _run_ipo_pipeline():
    if datetime.now(timezone.utc).weekday() != 3:  # Thursday only
        return
    from utils.ipo_pipeline_fetcher import refresh_pipeline
    n = refresh_pipeline()
    log.info("IPO pipeline: refreshed %d companies", n)


def _run_activist_sync():
    from scripts.sync_activist import sync_days
    result = sync_days(days=30)
    log.info("Activist filings: %s", result)


def _run_merger_news():
    from utils.merger_news import fetch_merger_news, upsert_merger_news
    stored = upsert_merger_news(fetch_merger_news())
    log.info("Merger news: synchronized %d RSS releases", stored)


def _run_treemap_refresh():
    from utils.hedge_fund_db import get_treemap_data
    data = get_treemap_data(min_value=0, fund_filter="", limit=500)
    from routes.hedge_funds import _cache
    import time as _t
    _cache[":0:500"] = (_t.time(), data)
    log.info("Treemap cache refreshed: %d rows", len(data))


CANDIDATE_HOUR = max(HOUR - 2, 0)

JOBS = {
    "digest":           {"fn": _run_digest,           "hour": HOUR},
    "security_returns": {"fn": _run_security_returns, "hour": HOUR},
    "deal_candidates":  {"fn": _run_deal_candidates,  "hour": CANDIDATE_HOUR},
    "deal_radar":       {"fn": _run_deal_radar,        "hour": CANDIDATE_HOUR},
    "ee_register":      {"fn": _run_ee_register,       "hour": CANDIDATE_HOUR},
    "no_register":      {"fn": _run_no_register,       "hour": CANDIDATE_HOUR},
    "dk_register":      {"fn": _run_dk_register,       "hour": CANDIDATE_HOUR},
    "ipo_pipeline":     {"fn": _run_ipo_pipeline,      "hour": CANDIDATE_HOUR},
    "activist_sync":    {"fn": _run_activist_sync,     "hour": CANDIDATE_HOUR},
    "merger_news":      {"fn": _run_merger_news,       "hour": CANDIDATE_HOUR},
    "treemap_refresh":  {"fn": _run_treemap_refresh,   "hour": CANDIDATE_HOUR},
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
            from utils.database import get_conn
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT pg_try_advisory_lock(hashtext(%s))",
                    (f"liquidround:scheduler:{name}",),
                )
                row = cur.fetchone()
                acquired = bool(row and row[0])
                if not acquired:
                    log.info("[%s] skipped; another replica holds the job lock", name)
                    continue
                try:
                    fn()
                finally:
                    cur.execute(
                        "SELECT pg_advisory_unlock(hashtext(%s))",
                        (f"liquidround:scheduler:{name}",),
                    )
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
