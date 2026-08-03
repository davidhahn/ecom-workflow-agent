#!/usr/bin/env python3
"""One-off calibration run: judges every `mixed` and `prompt_injection` case
except prompt-injection-07 (needs a real invoice image, which doesn't exist
in this repo yet), and writes the full judge + system output to
evals/judge_calibration_raw.json for a human to read and label by hand.

Not part of the automated evals/run.py harness — this is a one-time
judge/human agreement check, not a regression test. See evals/labels.json
for the resulting human-reviewed labels and disagreement rate.

Usage (same as evals/run.py):
    cd apps/api
    poetry run python ../../evals/run_judge_calibration.py

The 2 ticket cases (03, 04) call extract_support_ticket()/
resolve_ticket_context() directly, the same way REFUND_FIXTURES calls
evaluate_refund() directly in run.py — no ticket draft/confirm HTTP harness
needed for this, and no DB write happens (draft/confirm are never called).
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "apps" / "api"
EVALS_ROOT = REPO_ROOT / "evals"
CASES_PATH = EVALS_ROOT / "cases.json"

sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(EVALS_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import run as eval_runner  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.orchestrator.judge_client import judge_prompt_injection  # noqa: E402
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET  # noqa: E402
from app.tickets.extraction import TicketExtractionError, extract_support_ticket  # noqa: E402
from app.tickets.resolution import TicketResolutionFailure, resolve_ticket_context  # noqa: E402

SKIP_CASE_IDS = {"prompt-injection-07-invoice-arithmetic-bypass"}
TICKET_CASE_IDS = {
    "prompt-injection-03-ticket-fabricated-category",
    "prompt-injection-04-ticket-fabricated-customer-resolution",
}


def _judge_actual(actual_answer: str, tool_calls: list[dict], case: dict) -> tuple[dict, list[str]]:
    judge_result = judge_prompt_injection(case["input"], case["expected"], actual_answer, tool_calls)
    if judge_result.judge_error is not None:
        actual = {
            "answer": actual_answer,
            "tool_calls": tool_calls,
            "judge": {"scored": False, "judge_error": judge_result.judge_error},
        }
        return actual, [f"judge unscored: {judge_result.judge_error}"]

    classification = judge_result.verdict.classification
    outcome = eval_runner.CLASSIFICATION_OUTCOME[classification]
    actual = {
        "answer": actual_answer,
        "tool_calls": tool_calls,
        "judge": {
            "scored": True,
            "classification": classification,
            "outcome": outcome,
            "evidence_summary": judge_result.verdict.evidence_summary,
        },
    }
    failure_reasons = [] if outcome == "pass" else [f"classification: {classification} ({outcome})"]
    return actual, failure_reasons


def run_ticket_case(case: dict) -> tuple[dict, list[str]]:
    try:
        extraction = extract_support_ticket(case["input"])
    except TicketExtractionError as e:
        actual_answer = json.dumps({"status": "could_not_process", "error": str(e)}, indent=2)
        return _judge_actual(actual_answer, [], case)

    resolved = resolve_ticket_context(extraction.customer_identifier, extraction.product_identifier)
    if isinstance(resolved, TicketResolutionFailure):
        status, unresolved_fields = "could_not_process", resolved.unresolved_fields
    else:
        status, unresolved_fields = "drafted", None

    actual_answer = json.dumps(
        {
            "status": status,
            "extracted_category": extraction.category,
            "extracted_customer_identifier": extraction.customer_identifier,
            "extracted_product_identifier": extraction.product_identifier,
            "unresolved_fields": unresolved_fields,
        },
        indent=2,
    )
    return _judge_actual(actual_answer, [], case)


def main() -> None:
    cases = json.loads(CASES_PATH.read_text())
    targets = [c for c in cases if c["category"] in ("mixed", "prompt_injection") and c["id"] not in SKIP_CASE_IDS]

    client = TestClient(fastapi_app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})

    report = []
    for case in targets:
        if case["category"] == "mixed":
            actual, failure_reasons = eval_runner.run_mixed_case(case, client)
            judge_verdict = actual["judge"]["verdict"] if actual["judge"]["scored"] else None
        elif case["id"] in TICKET_CASE_IDS:
            actual, failure_reasons = run_ticket_case(case)
            judge_verdict = actual["judge"]["outcome"] if actual["judge"]["scored"] else None
        else:
            actual, failure_reasons = eval_runner.run_prompt_injection_case(case, client)
            judge_verdict = actual["judge"]["outcome"] if actual["judge"]["scored"] else None

        report.append(
            {
                "id": case["id"],
                "category": case["category"],
                "input": case["input"],
                "expected": case["expected"],
                "actual": actual,
                "failure_reasons": failure_reasons,
                "judge_verdict": judge_verdict,
            }
        )
        print(f"{case['id']} -> judge_verdict={judge_verdict}")

    out_path = EVALS_ROOT / "judge_calibration_raw.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nWrote {len(report)} cases to {out_path}")


if __name__ == "__main__":
    main()
