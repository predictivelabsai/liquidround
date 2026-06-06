"""Send the Daily Deals digest email via Postmark.

Usage:
    python -m scripts.daily_deals                  # uses env defaults
    python -m scripts.daily_deals --to user@example.com
    python -m scripts.daily_deals --dry-run         # print HTML, don't send

Schedule via cron (e.g. daily at 07:00 UTC):
    0 7 * * * cd /path/to/liquidround && python -m scripts.daily_deals
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from utils.deals_scanner import (
    scan_top_companies, scan_recent_additions, fetch_ma_news,
    build_digest_html, build_digest_text,
)
from utils.email import send_email

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Send LiquidRound Daily Deals digest")
    parser.add_argument("--to", default=os.getenv("TO_EMAIL", "kaljuvee@gmail.com"))
    parser.add_argument("--from-email", default=os.getenv("FROM_EMAIL", "info@liquidround.com"))
    parser.add_argument("--dry-run", action="store_true", help="Print HTML without sending")
    parser.add_argument("--companies", type=int, default=10, help="Number of top companies")
    parser.add_argument("--news", type=int, default=8, help="Number of news items")
    args = parser.parse_args()

    log.info("Scanning top companies...")
    companies = scan_top_companies(limit=args.companies)
    log.info(f"Found {len(companies)} companies")

    log.info("Scanning recent additions...")
    recent = scan_recent_additions(limit=5)
    log.info(f"Found {len(recent)} recent additions")

    log.info("Fetching M&A news...")
    news = fetch_ma_news(num_results=args.news)
    log.info(f"Found {len(news)} news items")

    html = build_digest_html(companies, news, recent)
    text = build_digest_text(companies, news)

    today = datetime.now().strftime("%b %d, %Y")
    subject = f"LiquidRound Daily Deals — {today}"

    if args.dry_run:
        print(html)
        log.info(f"Dry run complete. Subject: {subject}")
        return

    log.info(f"Sending to {args.to} from {args.from_email}...")
    result = send_email(
        to=args.to,
        subject=subject,
        html_body=html,
        text_body=text,
        from_email=args.from_email,
        tag="daily-deals",
    )

    if result.get("ErrorCode") == 0:
        log.info(f"Sent! MessageID: {result.get('MessageID')}")
    elif result.get("error"):
        log.error(f"Failed: {result['error']}")
        sys.exit(1)
    else:
        log.error(f"Postmark error: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
