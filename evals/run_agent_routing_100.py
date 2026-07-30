"""Run the deterministic 100-question agent routing and refinement evaluation."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from agents.router import decide_route

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "agent-routing-100.csv"


def load_cases() -> list[dict]:
    with DATASET.open(newline="", encoding="utf-8") as handle:
        cases = list(csv.DictReader(handle))
    if len(cases) != 100:
        raise ValueError(f"Expected exactly 100 evaluation questions, found {len(cases)}")
    return cases


def evaluate() -> dict:
    results = []
    for case in load_cases():
        prior = [part for part in case["prior_messages"].split("||") if part]
        decision = decide_route(
            case["input_text"],
            previous_user_messages=prior,
            active_slug=case["active_slug"] or None,
        )
        results.append({
            "id": int(case["id"]),
            "question": case["input_text"],
            "expected": case["expected_slug"],
            "actual": decision.slug,
            "case_type": case["case_type"],
            "passed": decision.slug == case["expected_slug"],
            "decision": decision.to_dict(),
        })
    passed = sum(row["passed"] for row in results)
    return {
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "accuracy_pct": round(passed / len(results) * 100, 1),
        },
        "results": results,
    }


def main() -> int:
    report = evaluate()
    print(json.dumps(report["summary"], indent=2))
    for row in report["results"]:
        if not row["passed"]:
            print(f"FAIL {row['id']}: {row['expected']} != {row['actual']} — {row['question']}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
