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


def resolve_ticket_context(
    customer_identifier: str | None, product_identifier: str | None
) -> ResolvedTicketContext | None:
    """Same philosophy as refund_evaluator.resolve_order_item (DECISIONS.md
    #16): absence of a customer identifier is grounds for refusal, not a
    best-effort guess. When a product is named, resolution is delegated
    directly to resolve_order_item() — the exact same customer+product ->
    order_item lookup the refund evaluator uses, not a second, parallel
    implementation of the same idea. An explicitly-named but unresolvable
    product is refused (None), not silently dropped."""
    if not customer_identifier:
        return None

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
        return None

    if not product_identifier:
        return ResolvedTicketContext(customer_id=customer_id, order_id=None, product_id=None)

    resolved_item = resolve_order_item(product_identifier, customer_identifier)
    if resolved_item is None:
        return None

    with SessionLocal() as session:
        row = session.execute(
            select(OrderItem.order_id, OrderItem.product_id).where(
                OrderItem.id == resolved_item.order_item_id
            )
        ).one()

    return ResolvedTicketContext(customer_id=customer_id, order_id=row.order_id, product_id=row.product_id)
