"""get_shipment_status: a single, tightly-scoped read-only lookup by
product, status, and/or expected-delivery date range.

Safety posture, parity with the SQL tool's layers without needing all of
them: there's no arbitrary SQL string to validate (layer 1's job), because
the query shape here is fixed and built entirely with SQLAlchemy Core's
query builder — every filter value is bound as a parameter, never
interpolated into a string, so injection is structurally impossible rather
than caught after the fact. Execution goes through the same restricted
ops_agent_readonly role (readonly_engine) as the SQL tool's layer 3
backstop. Results are capped at DEFAULT_LIMIT, the same row cap the SQL
tool applies (layer 2's practical effect) — there's no EXPLAIN-based cost
gate here since there's no way to construct an expensive query through
this fixed shape (one indexed join path, one bounded result set).
"""

from datetime import datetime

from sqlalchemy import select

from app.db.models import Order, OrderItem, Product, Shipment
from app.query.db_readonly import readonly_engine
from app.query.validation import DEFAULT_LIMIT
from app.shipments.schemas import ShipmentResult, ShipmentStatusResponse

VALID_STATUSES = {"pending", "shipped", "delivered", "delayed"}


def get_shipment_status(
    product_name: str | None = None,
    status: str | None = None,
    expected_delivery_before: str | None = None,
    expected_delivery_after: str | None = None,
) -> ShipmentStatusResponse:
    if status is not None and status not in VALID_STATUSES:
        return ShipmentStatusResponse(
            status="error",
            error_reason=(
                f"'{status}' is not a valid shipment status; "
                f"must be one of {sorted(VALID_STATUSES)}."
            ),
        )

    try:
        before_dt = datetime.fromisoformat(expected_delivery_before) if expected_delivery_before else None
        after_dt = datetime.fromisoformat(expected_delivery_after) if expected_delivery_after else None
    except ValueError as e:
        return ShipmentStatusResponse(
            status="error", error_reason=f"Could not parse a date filter: {e}"
        )

    stmt = select(
        Shipment.id,
        Shipment.order_id,
        Shipment.carrier,
        Shipment.shipped_date,
        Shipment.expected_delivery_date,
        Shipment.actual_delivery_date,
        Shipment.status,
    ).distinct()

    if product_name is not None:
        stmt = (
            stmt.join(Order, Order.id == Shipment.order_id)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(Product, Product.id == OrderItem.product_id)
            .where(Product.name.ilike(f"%{product_name}%"))
        )
    if status is not None:
        stmt = stmt.where(Shipment.status == status)
    if before_dt is not None:
        stmt = stmt.where(Shipment.expected_delivery_date <= before_dt)
    if after_dt is not None:
        stmt = stmt.where(Shipment.expected_delivery_date >= after_dt)

    stmt = stmt.order_by(Shipment.expected_delivery_date).limit(DEFAULT_LIMIT)

    with readonly_engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    shipments = [ShipmentResult(**row) for row in rows]
    return ShipmentStatusResponse(status="success", shipments=shipments, row_count=len(shipments))
