from datetime import datetime, timezone

from app.orchestrator.refund_evaluator import evaluate_refund, resolve_order_item
from app.orchestrator.refund_extraction import ExtractionError, extract_refund_request
from app.orchestrator.schemas import RefundEvaluateResponse

# Not one of the task's four decision statuses (approved / denied /
# requires_manager_approval / flagged_for_review) — this covers the "reject/
# flag rather than guess" cases: an unconfident reason mapping, or a product/
# customer that doesn't resolve to any real order_item.
COULD_NOT_PROCESS = "could_not_process"


def _partial_fields(
    product_identifier: str,
    customer_identifier: str | None,
    reason: str | None = None,
    evidence_submitted: bool | None = None,
) -> dict:
    return {
        "product_identifier": product_identifier,
        "customer_identifier": customer_identifier,
        "reason": reason,
        "evidence_submitted": evidence_submitted,
    }


def evaluate_refund_request(request_text: str) -> RefundEvaluateResponse:
    try:
        extraction = extract_refund_request(request_text)
    except ExtractionError as e:
        return RefundEvaluateResponse(
            status=COULD_NOT_PROCESS,
            rule_applied=None,
            reasoning=f"Could not extract a refund request from the text: {e}",
            extracted_fields={},
        )

    if not extraction.reason_confident:
        return RefundEvaluateResponse(
            status=COULD_NOT_PROCESS,
            rule_applied=None,
            reasoning=(
                "Could not confidently map the request text to one of the four "
                "reason codes (defective, wrong_item, changed_mind, "
                "damaged_shipping); refusing to guess."
            ),
            extracted_fields=_partial_fields(
                extraction.product_identifier,
                extraction.customer_identifier,
                extraction.reason,
                extraction.evidence_submitted,
            ),
        )

    resolved = resolve_order_item(extraction.product_identifier, extraction.customer_identifier)
    if resolved is None:
        detail = f"product '{extraction.product_identifier}'"
        if extraction.customer_identifier:
            detail += f" and customer '{extraction.customer_identifier}'"
        return RefundEvaluateResponse(
            status=COULD_NOT_PROCESS,
            rule_applied=None,
            reasoning=f"Could not resolve an order item matching {detail} against the database.",
            extracted_fields=_partial_fields(
                extraction.product_identifier,
                extraction.customer_identifier,
                extraction.reason,
                extraction.evidence_submitted,
            ),
        )

    evaluation = evaluate_refund(
        order_item_id=resolved.order_item_id,
        reason=extraction.reason,
        evidence_submitted=extraction.evidence_submitted,
        requested_at=datetime.now(timezone.utc),
    )

    fields = _partial_fields(
        extraction.product_identifier,
        extraction.customer_identifier,
        extraction.reason,
        extraction.evidence_submitted,
    )
    fields["order_item_id"] = str(resolved.order_item_id)

    return RefundEvaluateResponse(
        status=evaluation.status,
        rule_applied=evaluation.rule_applied,
        reasoning=evaluation.reasoning,
        extracted_fields=fields,
    )
