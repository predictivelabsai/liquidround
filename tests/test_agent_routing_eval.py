"""CI gate for the checked-in 100-question routing evaluation."""
from evals.run_agent_routing_100 import evaluate, load_cases


def test_agent_routing_dataset_has_100_unique_questions():
    cases = load_cases()
    assert len({case["id"] for case in cases}) == 100
    assert len({case["input_text"] for case in cases}) == 100


def test_agent_routing_100_questions_pass():
    report = evaluate()
    failures = [
        f"{row['id']}: expected {row['expected']}, got {row['actual']}"
        for row in report["results"] if not row["passed"]
    ]
    assert report["summary"]["passed"] == 100, "\n".join(failures)
