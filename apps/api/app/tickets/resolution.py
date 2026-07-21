import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select

from app.db.models import Customer, OrderItem
from app.db.session import SessionLocal
from app.orchestrator.refund_evaluator import resolve_order_item


@dataclass
class ResolvedTicketContext:
    customer_id: uuid.UUID
    order_id: uuid.UUID | None
    product_id: uuid.UUID | None


@dataclass
class TicketResolutionFailure:
    """Which piece(s) of context failed to resolve — surfaced explicitly so
    a caller (the API response, an eval harness) doesn't have to
    string-parse a human-readable message to find out. Never empty."""

    unresolved_fields: list[str]  # "customer" and/or "product"


def resolve_ticket_context(
    customer_identifier: str | None, product_identifier: str | None
) -> ResolvedTicketContext | TicketResolutionFailure:
    """Same philosophy as refund_evaluator.resolve_order_item (DECISIONS.md
    #16): absence of a customer identifier is grounds for refusal, not a
    best-effort guess. When a product is named, resolution is delegated
    directly to resolve_order_item() — the exact same customer+product ->
    order_item lookup the refund evaluator uses, not a second, parallel
    implementation of the same idea. An explicitly-named but unresolvable
    product is refused (None), not silently dropped.

    Customer and product resolution are checked independently rather than
    short-circuited on the first failure, so a caller can be told exactly
    which one(s) failed — the matching rules themselves are unchanged
    (either failure still means the whole ticket can't be drafted), only
    the reporting is more precise. Product resolution is skipped (and not
    counted as a failure) when no customer_identifier was given at all,
    since resolve_order_item requires one; "customer" alone is the
    complete, accurate reason in that case."""
    unresolved_fields: list[str] = []

    customer_id: uuid.UUID | None = None
    if not customer_identifier:
        unresolved_fields.append("customer")
    else:
        with SessionLocal() as session:
            customer_id = session.execute(
                select(Customer.id).where(
                    or_(
                        Customer.name.ilike(f"%{customer_identifier}%"),
                        Customer.email.ilike(f"%{customer_identifier}%"),
                    )
                )
            ).scalars().first()
        if customer_id is None:
            unresolved_fields.append("customer")

    resolved_item = None
    if product_identifier and customer_identifier:
        resolved_item = resolve_order_item(product_identifier, customer_identifier)
        if resolved_item is None:
            unresolved_fields.append("product")

    if unresolved_fields:
        return TicketResolutionFailure(unresolved_fields=unresolved_fields)

    if not product_identifier:
        return ResolvedTicketContext(customer_id=customer_id, order_id=None, product_id=None)

    with SessionLocal() as session:
        row = session.execute(
            select(OrderItem.order_id, OrderItem.product_id).where(
                OrderItem.id == resolved_item.order_item_id
            )
        ).one()

    return ResolvedTicketContext(customer_id=customer_id, order_id=row.order_id, product_id=row.product_id)
