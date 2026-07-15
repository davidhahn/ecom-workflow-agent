"""Tests for refund_evaluator.resolve_order_item()'s customer-identifier
guard (Fix 1: an empty customer_identifier must not fall back to a
product-only lookup across the entire customer base)."""

from unittest.mock import patch

from app.orchestrator.refund_evaluator import resolve_order_item
from app.orchestrator.refund_extraction import ExtractionResult
from app.orchestrator.refund_service import evaluate_refund_request

# A real product with at least one real order in the seeded DB (see
# apps/api/app/db/seed.py's high-refund-rate products) - if the customer
# guard weren't in place, a product-only lookup would resolve to whichever
# customer most recently ordered it.
_REAL_PRODUCT_WITH_ORDERS = "Bluetooth Headphones Pro"


def test_resolve_order_item_refuses_empty_customer_identifier():
    assert resolve_order_item(_REAL_PRODUCT_WITH_ORDERS, "") is None
    assert resolve_order_item(_REAL_PRODUCT_WITH_ORDERS, None) is None


def test_resolve_order_item_still_resolves_with_a_real_customer():
    # Confirms the guard didn't just break resolution outright - the same
    # product does resolve once a customer identifier is actually given.
    # ("a" matches broadly via ILIKE against real seeded customer names, so
    # this only proves the guard is specifically about the missing-identifier
    # case, not that resolution is broken generally.)
    assert resolve_order_item(_REAL_PRODUCT_WITH_ORDERS, "") is None
    assert resolve_order_item(_REAL_PRODUCT_WITH_ORDERS, "a") is not None


def test_evaluate_refund_request_returns_could_not_process_for_missing_customer():
    fake_extraction = ExtractionResult(
        product_identifier=_REAL_PRODUCT_WITH_ORDERS,
        customer_identifier="",
        reason_confident=True,
        reason="defective",
        evidence_submitted=False,
    )
    with patch(
        "app.orchestrator.refund_service.extract_refund_request",
        return_value=fake_extraction,
    ):
        response = evaluate_refund_request(
            "My Bluetooth Headphones Pro are defective, I want a refund."
        )

    assert response.status == "could_not_process"
    assert response.rule_applied is None
    assert "customer" in response.reasoning.lower()
