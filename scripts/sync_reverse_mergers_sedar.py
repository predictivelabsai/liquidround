"""Discover and store recent Canadian reverse-merger filings from SEDAR+.

Drives a headless Chromium browser against the public sedarplus.ca document
search, downloads each matching filing, parses it through the canonical
``filing_intelligence`` pipeline, and upserts CA records into the same
``liquidround.reverse_merger_transactions`` / ``reverse_merger_filings``
tables used by the EDGAR pipeline.

Usage::

    python -m scripts.sync_reverse_mergers_sedar --days 365 --limit 40
    python -m scripts.sync_reverse_mergers_sedar --dry-run
    python -m scripts.sync_reverse_mergers_sedar --no-headless  # visible browser (debugging)
"""
from __future__ import annotations

import argparse

from utils.reverse_mergers import discover_sedarplus_candidates, upsert_transactions


def main(days: int = 365, limit: int = 40, dry_run: bool = False,
         headless: bool = True) -> dict:
    records = discover_sedarplus_candidates(days=days, limit=limit, headless=headless)
    stored = 0 if dry_run else upsert_transactions(records)
    return {"discovered": len(records), "stored": stored, "dry_run": dry_run}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-headless", action="store_true",
                        help="Run Chromium visibly (useful for debugging selectors).")
    args = parser.parse_args()
    print(main(args.days, args.limit, args.dry_run, headless=not args.no_headless))
