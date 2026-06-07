"""Send the Daily Deals digest email via Postmark.

Usage:
    python -m scripts.daily_deals                    # send to TO_EMAIL
    python -m scripts.daily_deals --to user@x.com    # send to specific address
    python -m scripts.daily_deals --all              # send to all opted-in users
    python -m scripts.daily_deals --dry-run          # print HTML, don't send
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from utils.digest import build_digest, render_email_html, send_digest_email, send_digest_to_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Send LiquidRound Daily Deals digest")
    parser.add_argument("--to", default=os.getenv("TO_EMAIL", "kaljuvee@gmail.com"))
    parser.add_argument("--all", action="store_true", help="Send to all opted-in users")
    parser.add_argument("--dry-run", action="store_true", help="Print HTML without sending")
    parser.add_argument("--companies", type=int, default=10, help="Number of companies")
    args = parser.parse_args()

    if args.all and not args.dry_run:
        log.info("Sending digest to ALL opted-in users...")
        result = send_digest_to_all()
        log.info("Done: sent=%s/%s", result.get("sent"), result.get("total"))
        for r in result.get("results", []):
            status = "OK" if r.get("ok") else f"FAIL: {r.get('error', '?')}"
            log.info("  %s — %s", r.get("email"), status)
        return

    log.info("Building digest (%d companies)...", args.companies)
    digest = build_digest(n_companies=args.companies)
    html = render_email_html(digest)

    if args.dry_run:
        print(html)
        log.info("Dry run complete — %d companies, featured: %s",
                 len(digest.get("companies", [])),
                 digest.get("featured", {}).get("name", "N/A"))
        return

    log.info("Sending to %s...", args.to)
    result = send_digest_email(html, to_email=args.to)
    if result.get("ok"):
        log.info("Sent! MessageID: %s", result.get("message_id"))
    else:
        log.error("Failed: %s", result.get("error"))
        sys.exit(1)


if __name__ == "__main__":
    main()
