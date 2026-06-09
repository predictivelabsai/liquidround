"""
Evaluate agent routing accuracy against ground-truth routing cases.

Reads test-data/routing_cases.csv, runs each input through the router,
and checks if the correct agent slug is selected.

Usage:
    python -m evals.run_routing_eval
    python -m evals.run_routing_eval --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ROUTING_CSV = ROOT / "test-data" / "routing_cases.csv"
RESULTS_DIR = ROOT / "eval-results"


def load_cases() -> list[dict]:
    with open(ROUTING_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_routing_eval(cases: list[dict]) -> list[dict]:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    from agents.router import route

    results = []
    for i, case in enumerate(cases):
        input_text = case["input_text"]
        expected = case["expected_slug"]
        try:
            actual = route(input_text)
            passed = actual == expected
        except Exception as e:
            actual = f"ERROR: {e}"
            passed = False

        results.append({
            "input": input_text,
            "expected_slug": expected,
            "actual_slug": actual,
            "expected_category": case["expected_category"],
            "notes": case["notes"],
            "result": "PASS" if passed else "FAIL",
        })
        status = "PASS" if passed else f"FAIL (got {actual})"
        print(f"  [{i+1}/{len(cases)}] {status}: {input_text[:50]}")

    return results


def save_results(results: list[dict]):
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    out_path = RESULTS_DIR / f"routing-eval-{ts}.json"

    summary = {
        "timestamp": ts,
        "total": len(results),
        "passed": sum(1 for r in results if r["result"] == "PASS"),
        "failed": sum(1 for r in results if r["result"] == "FAIL"),
        "accuracy_pct": round(100 * sum(1 for r in results if r["result"] == "PASS") / len(results), 1) if results else 0,
    }

    prefix_cases = [r for r in results if "explicit" in r.get("notes", "")]
    freeform_cases = [r for r in results if "free-form" in r.get("notes", "")]
    summary["prefix_accuracy_pct"] = round(100 * sum(1 for r in prefix_cases if r["result"] == "PASS") / len(prefix_cases), 1) if prefix_cases else 0
    summary["freeform_accuracy_pct"] = round(100 * sum(1 for r in freeform_cases if r["result"] == "PASS") / len(freeform_cases), 1) if freeform_cases else 0

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print(f"\nRouting accuracy: {summary['passed']}/{summary['total']} ({summary['accuracy_pct']}%)")
    print(f"  Prefix routing: {summary['prefix_accuracy_pct']}%")
    print(f"  Free-form routing: {summary['freeform_accuracy_pct']}%")
    print(f"Saved to {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cases = load_cases()

    if args.dry_run:
        for i, c in enumerate(cases):
            print(f"  [{i}] {c['input_text'][:60]} -> expected: {c['expected_slug']}")
        print(f"\n{len(cases)} cases. Run without --dry-run to execute.")
        return

    print(f"Running {len(cases)} routing cases...\n")
    results = run_routing_eval(cases)
    save_results(results)


if __name__ == "__main__":
    main()
