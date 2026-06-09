"""
LiquidRound AI evaluation framework using DeepEval.

Reads ground-truth.csv, sends each question through the LiquidRound agent
router, compares AI output against expected answers using DeepEval metrics,
and writes results to eval-results/.

Usage:
    pip install deepeval
    python -m evals.run_evals                    # run all evals
    python -m evals.run_evals --dry-run          # print questions, skip LLM calls
    python -m evals.run_evals --rows 0-4         # run subset
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = ROOT / "evals" / "ground-truth.csv"
RESULTS_DIR = ROOT / "eval-results"


def load_ground_truth(path: Path = GROUND_TRUTH) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_ai_answer(question: str) -> str:
    """Send a question through the LiquidRound agent router and return the response."""
    sys.path.insert(0, str(ROOT))
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    from agents.router import route
    from agents.base import cached_agent
    from langchain_core.messages import HumanMessage

    slug = route(question)
    agent = cached_agent(slug)
    result = agent.invoke({"messages": [HumanMessage(content=question)]})

    final_msg = result["messages"][-1]
    return final_msg.content if hasattr(final_msg, "content") else str(final_msg)


def run_deepeval(rows: list[dict]) -> list[dict]:
    """Run DeepEval metrics on each row."""
    try:
        from deepeval import evaluate
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
            GEval,
        )
        from deepeval.test_case import LLMTestCase
    except ImportError:
        print("deepeval not installed — run: pip install deepeval")
        print("Falling back to keyword-match evaluation.")
        return run_keyword_eval(rows)

    eval_model = os.getenv("DEEPEVAL_MODEL", "gpt-4o-mini")

    relevancy = AnswerRelevancyMetric(threshold=0.6, model=eval_model)
    correctness = GEval(
        name="Correctness",
        criteria=(
            "Determine whether the AI answer is factually correct and covers "
            "the key points from the expected answer. Minor phrasing differences "
            "are acceptable. Missing key facts should be penalized."
        ),
        evaluation_params=[
            GEval.ACTUAL_OUTPUT,
            GEval.EXPECTED_OUTPUT,
        ],
        threshold=0.6,
        model=eval_model,
    )

    test_cases = []
    for row in rows:
        tc = LLMTestCase(
            input=row["question"],
            actual_output=row["ai_answer"],
            expected_output=row["expected_answer"],
        )
        test_cases.append(tc)

    results = []
    for i, tc in enumerate(test_cases):
        row = rows[i]
        try:
            relevancy.measure(tc)
            correctness.measure(tc)
            passed = relevancy.score >= relevancy.threshold and correctness.score >= correctness.threshold
            results.append({
                "question": row["question"],
                "expected_answer": row["expected_answer"],
                "ai_answer": row["ai_answer"],
                "relevancy_score": round(relevancy.score, 3),
                "correctness_score": round(correctness.score, 3),
                "result": "PASS" if passed else "FAIL",
                "relevancy_reason": relevancy.reason,
                "correctness_reason": correctness.reason,
            })
        except Exception as e:
            results.append({
                "question": row["question"],
                "expected_answer": row["expected_answer"],
                "ai_answer": row["ai_answer"],
                "relevancy_score": 0,
                "correctness_score": 0,
                "result": "ERROR",
                "error": str(e),
            })
        print(f"  [{i+1}/{len(rows)}] {'PASS' if results[-1]['result'] == 'PASS' else results[-1]['result']}: {row['question'][:60]}")

    return results


def run_keyword_eval(rows: list[dict]) -> list[dict]:
    """Fallback: keyword overlap scoring when deepeval is not available."""
    results = []
    for row in rows:
        expected_words = set(row["expected_answer"].lower().split())
        ai_words = set(row["ai_answer"].lower().split())
        overlap = len(expected_words & ai_words)
        total = len(expected_words)
        score = overlap / total if total > 0 else 0
        results.append({
            "question": row["question"],
            "expected_answer": row["expected_answer"],
            "ai_answer": row["ai_answer"],
            "keyword_overlap_score": round(score, 3),
            "result": "PASS" if score >= 0.3 else "FAIL",
        })
    return results


def save_results(results: list[dict], tag: str = ""):
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    fname = f"eval-{tag + '-' if tag else ''}{ts}.json"
    out_path = RESULTS_DIR / fname

    summary = {
        "timestamp": ts,
        "total": len(results),
        "passed": sum(1 for r in results if r["result"] == "PASS"),
        "failed": sum(1 for r in results if r["result"] == "FAIL"),
        "errors": sum(1 for r in results if r["result"] == "ERROR"),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2, ensure_ascii=False)

    print(f"\nResults: {summary['passed']}/{summary['total']} passed")
    print(f"Saved to {out_path}")

    gt_path = GROUND_TRUTH
    rows_all = load_ground_truth()
    updated = False
    for res in results:
        for row in rows_all:
            if row["question"] == res["question"]:
                row["ai_answer"] = res.get("ai_answer", "")
                row["result"] = res["result"]
                updated = True
    if updated:
        with open(gt_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["question", "expected_answer", "ai_answer", "result"])
            writer.writeheader()
            writer.writerows(rows_all)
        print(f"Updated {gt_path}")

    return out_path


def main():
    parser = argparse.ArgumentParser(description="LiquidRound AI evals")
    parser.add_argument("--dry-run", action="store_true", help="Print questions without running LLM")
    parser.add_argument("--rows", type=str, default=None, help="Row range, e.g. 0-4")
    parser.add_argument("--tag", type=str, default="", help="Tag for output filename")
    parser.add_argument("--skip-llm", action="store_true", help="Skip AI calls, use existing ai_answer column")
    args = parser.parse_args()

    rows = load_ground_truth()

    if args.rows:
        start, end = map(int, args.rows.split("-"))
        rows = rows[start : end + 1]

    if args.dry_run:
        for i, row in enumerate(rows):
            print(f"  [{i}] {row['question'][:80]}")
        print(f"\n{len(rows)} questions loaded. Pass without --dry-run to execute.")
        return

    if not args.skip_llm:
        print(f"Running {len(rows)} questions through LiquidRound agents...\n")
        for i, row in enumerate(rows):
            print(f"  [{i+1}/{len(rows)}] Querying: {row['question'][:60]}...")
            t0 = time.time()
            try:
                row["ai_answer"] = get_ai_answer(row["question"])
            except Exception as e:
                row["ai_answer"] = f"ERROR: {e}"
            elapsed = time.time() - t0
            print(f"           -> {elapsed:.1f}s, {len(row['ai_answer'])} chars")

    print(f"\nEvaluating {len(rows)} answers...\n")
    results = run_deepeval(rows)
    save_results(results, tag=args.tag)


if __name__ == "__main__":
    main()
