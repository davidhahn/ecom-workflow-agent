import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select

from app.db.models import Customer, Order, OrderItem, Product, Refund
from app.db.session import SessionLocal

# Reason -> return window in days; None means no time limit.
# refund_policy.md rules 2 (defective), 3 (changed_mind), 4 (damaged_shipping),
# 5 (wrong_item). All 4 valid reason codes have their own specific window —
# rule 1's standard 30-day window is superseded for every one of them, so
# there's no separate "falls back to 30 days" branch to implement.
REASON_WINDOW_DAYS: dict[str, int | None] = {
    "defective": 90,
    "changed_mind": 14,
    "damaged_shipping": None,
    "wrong_item": None,
}

# The rule that governs a given reason code's eligibility window — also used
# as rule_applied for the terminal "approved" case, since that's the rule
# that's actually permitting the refund when nothing else blocks it.
REASON_RULE_NUMBER: dict[str, int] = {
    "defective": 2,
    "changed_mind": 3,
    "damaged_shipping": 4,
    "wrong_item": 5,
}

FINAL_SALE_CATEGORIES = {"Clearance", "Final Sale"}
EXEMPT_REASONS_FOR_FINAL_SALE = {"defective", "wrong_item"}
APPROVAL_THRESHOLD_CENTS = 20_000  # $200, refund_policy.md rule 6
REPEAT_REFUND_WINDOW_DAYS = 90
REPEAT_REFUND_THRESHOLD = 3


@dataclass
class ResolvedOrderItem:
    order_item_id: uuid.UUID


@dataclass
class RefundEvaluation:
    status: str
    rule_applied: int | None
    reasoning: str


def resolve_order_item(
    product_identifier: str, customer_identifier: str | None
) -> ResolvedOrderItem | None:
    """Look up the most recent order_item matching the extracted product
    and customer identifiers against real DB rows. Returns None if nothing
    matches — callers must not guess an order_item_id.

    customer_identifier is required, not optional: without it, a product-name
    match alone would resolve to whichever customer most recently ordered
    that product, across the entire customer base — a wrong-customer match,
    not just a wrong-order one. Absence of a customer identifier is grounds
    for refusal, so this returns None before running any query."""
    if not customer_identifier:
        return None

    with SessionLocal() as session:
        stmt = (
            select(OrderItem.id)
            .join(Order, OrderItem.order_id == Order.id)
            .join(Product, OrderItem.product_id == Product.id)
            .join(Customer, Order.customer_id == Customer.id)
            .where(Product.name.ilike(f"%{product_identifier}%"))
            .where(
                or_(
                    Customer.name.ilike(f"%{customer_identifier}%"),
                    Customer.email.ilike(f"%{customer_identifier}%"),
                )
            )
            .order_by(Order.order_date.desc())
            .limit(1)
        )
        order_item_id = session.execute(stmt).scalar_one_or_none()

    if order_item_id is None:
        return None
    return ResolvedOrderItem(order_item_id=order_item_id)


def evaluate_refund(
    *,
    order_item_id: uuid.UUID,
    reason: str,
    evidence_submitted: bool,
    requested_at: datetime,
) -> RefundEvaluation:
    """Zero-LLM-call evaluator. Checks real DB rows in a fixed rule order —
    the first rule that decisively applies determines the outcome. Returns a
    decision only; never writes to refunds (Part 1 doesn't execute refunds,
    just evaluates them)."""
    with SessionLocal() as session:
        row = session.execute(
            select(OrderItem, Order, Product)
            .join(Order, OrderItem.order_id == Order.id)
            .join(Product, OrderItem.product_id == Product.id)
            .where(OrderItem.id == order_item_id)
        ).first()
        if row is None:
            raise ValueError(f"order_item {order_item_id} not found")
        order_item, order, product = row

        amount_cents = order_item.quantity * order_item.unit_price_cents

        # 1. Category exclusion (rule 9)
        if product.category in FINAL_SALE_CATEGORIES and reason not in EXEMPT_REASONS_FOR_FINAL_SALE:
            return RefundEvaluation(
                status="denied",
                rule_applied=9,
                reasoning=(
                    f"Product category '{product.category}' is excluded from "
                    f"refunds (rule 9), and reason '{reason}' is not one of the "
                    "exempt reasons (defective, wrong_item)."
                ),
            )

        # 2. Time window (rule 2/3/4/5, whichever governs this reason)
        window_days = REASON_WINDOW_DAYS[reason]
        elapsed_days = (requested_at - order.order_date).days
        if window_days is not None and elapsed_days > window_days:
            rule = REASON_RULE_NUMBER[reason]
            return RefundEvaluation(
                status="denied",
                rule_applied=rule,
                reasoning=(
                    f"{elapsed_days} days have elapsed since purchase, exceeding "
                    f"the {window_days}-day window for reason '{reason}' (rule {rule})."
                ),
            )

        # 3. Evidence check (rule 4) — only damaged_shipping requires it.
        # Denied, not pending: Part 1 has no evidence-upload or
        # re-evaluation flow, so there's no mechanism that ever moves a
        # "pending" request forward — as a one-shot decision with no
        # persisted state, the only accurate answer when evidence is
        # missing at evaluation time is that the refund cannot be
        # processed now, i.e. denied.
        if reason == "damaged_shipping" and not evidence_submitted:
            return RefundEvaluation(
                status="denied",
                rule_applied=4,
                reasoning=(
                    "Reason is damaged_shipping but no photo evidence has been "
                    "submitted (rule 4); cannot be processed without evidence."
                ),
            )

        # 4. Repeat-refund flag (rule 7) — applies regardless of this refund's
        #    own reason or amount, per the rule's own text
        window_start = requested_at - timedelta(days=REPEAT_REFUND_WINDOW_DAYS)
        approved_count = session.execute(
            select(func.count(Refund.id))
            .join(OrderItem, Refund.order_item_id == OrderItem.id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.customer_id == order.customer_id,
                Refund.status == "approved",
                Refund.requested_at >= window_start,
                Refund.requested_at <= requested_at,
            )
        ).scalar_one()
        if approved_count >= REPEAT_REFUND_THRESHOLD:
            return RefundEvaluation(
                status="flagged_for_review",
                rule_applied=7,
                reasoning=(
                    f"Customer has {approved_count} approved refunds within the "
                    f"last {REPEAT_REFUND_WINDOW_DAYS} days (rule 7); flagged for "
                    "manual review regardless of this refund's own reason or amount."
                ),
            )

        # 5. Approval threshold (rule 6)
        if amount_cents > APPROVAL_THRESHOLD_CENTS:
            return RefundEvaluation(
                status="requires_manager_approval",
                rule_applied=6,
                reasoning=(
                    f"Refund amount ${amount_cents / 100:.2f} exceeds the $200 "
                    "approval threshold (rule 6)."
                ),
            )

        # Otherwise approved, under the reason-specific rule that governs it
        rule = REASON_RULE_NUMBER[reason]
        return RefundEvaluation(
            status="approved",
            rule_applied=rule,
            reasoning=(
                "No exclusion, window, evidence, repeat-refund, or threshold rule "
                f"blocked this refund; approved under rule {rule}, which governs "
                f"the '{reason}' reason code."
            ),
        )
