"""Discover and store the last three years of US reverse-merger filings."""
from __future__ import annotations

import argparse

from utils.reverse_mergers import discover_edgar_candidates, upsert_transactions


def main(years: int = 3, limit: int = 100, dry_run: bool = False) -> dict:
    records = discover_edgar_candidates(years=years, limit=limit)
    stored = 0 if dry_run else upsert_transactions(records)
    return {"discovered": len(records), "stored": stored, "dry_run": dry_run}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(main(args.years, args.limit, args.dry_run))
