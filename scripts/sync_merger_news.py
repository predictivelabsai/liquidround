"""Synchronize merger-topic publisher RSS feeds."""
from __future__ import annotations

import argparse

from utils.merger_news import fetch_merger_news, upsert_merger_news


def main(max_items_per_feed: int | None = None, dry_run: bool = False) -> dict:
    records = fetch_merger_news(max_items_per_feed=max_items_per_feed)
    stored = 0 if dry_run else upsert_merger_news(records)
    by_source = {}
    for record in records:
        by_source[record["source"]] = by_source.get(record["source"], 0) + 1
    return {"discovered": len(records), "stored": stored, "by_source": by_source,
            "dry_run": dry_run}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items-per-feed", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(main(args.max_items_per_feed, args.dry_run))
