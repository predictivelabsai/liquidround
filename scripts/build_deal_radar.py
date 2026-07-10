"""Build the Daily M&A Deal Radar — score public-buyer ↔ private-Baltic-target
pairs and persist the top-N to liquidround.deal_radar_pairs.

    python -m scripts.build_deal_radar                      # default run
    python -m scripts.build_deal_radar --targets 20 --buyers 4 --top 40
    python -m scripts.build_deal_radar --send               # also email it
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from utils import deal_radar as dr


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-country", type=int, default=3, help="deals kept per country")
    ap.add_argument("--targets", type=int, default=4, help="targets scored per country")
    ap.add_argument("--buyers", type=int, default=3, help="candidate buyers per target")
    ap.add_argument("--countries", nargs="*", help="limit to these countries")
    ap.add_argument("--send", action="store_true", help="email the digest to all opted-in users")
    args = ap.parse_args()

    pairs = dr.build_deal_radar(per_country=args.per_country, targets_per_country=args.targets,
                                buyers_per_target=args.buyers, countries=args.countries, persist=True)
    print(f"scored & persisted {len(pairs)} pairs")
    for p in pairs:
        print(f"  #{p['rank']} {p['composite_score']}  {p['buyer_ticker']:9} "
              f"{p['buyer_name'][:24]:24} -> {p['target_name'][:22]}")
    if args.send:
        from utils.digest import send_digest_to_all
        res = send_digest_to_all()
        print("email:", res)


if __name__ == "__main__":
    main()
