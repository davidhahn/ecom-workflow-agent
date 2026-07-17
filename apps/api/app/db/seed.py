"""Re-runnable seed script for the Part 1 schema (customers, products, orders,
order_items, refunds, support_tickets, shipments). Truncates the seven tables
and reinserts deterministic fixture data — safe to run against a fresh or
already-seeded database.

Usage:
    poetry run python -m app.db.seed
"""

import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, text

from app.db.models import (
    Customer,
    Order,
    OrderItem,
    Product,
    Refund,
    Shipment,
    SupportTicket,
)
from app.db.session import engine

NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")
RNG = random.Random(20260706)

ANCHOR = datetime(2026, 1, 1, tzinfo=timezone.utc)


def uid(*parts: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, ":".join(parts))


# ---------------------------------------------------------------------------
# customers
# ---------------------------------------------------------------------------

CUSTOMER_NAMES = [
    "Ava Thompson", "Noah Martinez", "Olivia Chen", "Liam Patel",
    "Emma Rodriguez", "Elijah Kim", "Sophia Nguyen", "James O'Brien",
    "Isabella Novak", "Benjamin Wright", "Mia Fischer", "Lucas Alvarez",
    "Charlotte Dubois", "Henry Osei", "Amelia Larsson", "Jack Romano",
    "Harper Singh", "Sebastian Cole", "Evelyn Brandt", "Daniel Okafor",
]
REGIONS = ["US-West", "US-East", "US-Central", "EU-West", "APAC", None]

customers = []
for i, name in enumerate(CUSTOMER_NAMES, start=1):
    slug = name.lower().replace(" ", ".").replace("'", "")
    customers.append(
        {
            "id": uid("customer", str(i)),
            "name": name,
            "email": f"{slug}@example.com",
            "region": REGIONS[i % len(REGIONS)],
            "created_at": ANCHOR - timedelta(days=RNG.randint(30, 720)),
        }
    )

# ---------------------------------------------------------------------------
# products — includes deliberate near-duplicate names
# ---------------------------------------------------------------------------

PRODUCT_ROWS = [
    ("Wireless Mouse", "Electronics", 1999),
    ("Wireless Mouse V2", "Electronics", 2499),
    ("Wireless Mouse - Refurbished", "Electronics", 1499),
    ("Bluetooth Headphones", "Electronics", 4999),
    ("Bluetooth Headphones Pro", "Electronics", 8999),
    ("USB-C Charging Cable", "Electronics", 999),
    ("USB-C Charging Cable 6ft", "Electronics", 1299),
    ("Stainless Steel Water Bottle", "Home", 1799),
    ("Stainless Steel Water Bottle 32oz", "Home", 2199),
    ("Ceramic Coffee Mug", "Home", 1299),
    ("Memory Foam Pillow", "Home", 3499),
    ("Cotton Bath Towel Set", "Home", 2999),
    ("Men's Running Shoes", "Apparel", 6999),
    ("Women's Running Shoes", "Apparel", 6999),
    ("Fleece Zip Hoodie", "Apparel", 4499),
    ("Organic Green Tea (20ct)", "Grocery", 799),
    ("Organic Green Tea (40ct)", "Grocery", 1399),
    ("Dark Roast Coffee Beans 12oz", "Grocery", 1299),
    ("Wireless Keyboard", "Office", 3999),
    ("Ergonomic Desk Chair", "Office", 15999),
    # edge case: final-sale exclusion (refund_policy.md rule 9) needs
    # products in these categories to test against
    ("Discontinued Bluetooth Speaker", "Clearance", 2999),
    ("Last-Season Winter Jacket", "Final Sale", 8999),
]

products = []
for i, (name, category, price_cents) in enumerate(PRODUCT_ROWS, start=1):
    products.append(
        {
            "id": uid("product", str(i)),
            "sku": f"SKU-{i:04d}",
            "name": name,
            "category": category,
            "price_cents": price_cents,
            "created_at": ANCHOR - timedelta(days=RNG.randint(60, 900)),
        }
    )
product_by_name = {p["name"]: p for p in products}

# products with a deliberately high refund rate
HIGH_REFUND_PRODUCTS = [
    product_by_name["Bluetooth Headphones Pro"],
    product_by_name["Wireless Mouse - Refurbished"],
]

# ---------------------------------------------------------------------------
# orders + order_items, built together so totals stay consistent
# ---------------------------------------------------------------------------

ORDER_STATUSES = ["placed", "shipped", "delivered", "cancelled"]

orders = []
order_items = []


def add_order(order_date: datetime, customer_index: int, status: str) -> uuid.UUID:
    order_id = uid("order", str(len(orders) + 1))
    orders.append(
        {
            "id": order_id,
            "customer_id": customers[customer_index % len(customers)]["id"],
            "status": status,
            "order_date": order_date,
            "total_cents": 0,  # filled in after items are attached
        }
    )
    return order_id


def add_item(order_id: uuid.UUID, product: dict, quantity: int) -> uuid.UUID:
    item_id = uid("order_item", str(len(order_items) + 1))
    order_items.append(
        {
            "id": item_id,
            "order_id": order_id,
            "product_id": product["id"],
            "quantity": quantity,
            "unit_price_cents": product["price_cents"],
        }
    )
    return item_id


# --- edge case: multi-item order where only ONE item gets refunded ---------
multi_order_id = add_order(ANCHOR - timedelta(days=40), customer_index=0, status="delivered")
multi_item_refunded = add_item(multi_order_id, product_by_name["Bluetooth Headphones"], 1)
multi_item_untouched_a = add_item(multi_order_id, product_by_name["Wireless Mouse"], 1)
multi_item_untouched_b = add_item(multi_order_id, product_by_name["USB-C Charging Cable"], 2)

# --- edge case: changed_mind refund that violates the 14-day window (rule 3)
#     once requested_at - order_date is computed. Time-relative to *now*,
#     not ANCHOR, since this order's age is what the refund-evaluator eval
#     suite's window-violation case (refund-04) actually exercises — a fixed
#     calendar date here decays as real time passes; see DECISIONS.md #14. -
policy_order_id = add_order(
    datetime.now(timezone.utc) - timedelta(days=45), customer_index=1, status="delivered"
)
policy_violation_item = add_item(policy_order_id, product_by_name["Ergonomic Desk Chair"], 1)

# --- edge case: damaged_shipping refunds with evidence_submitted variation
#     (refund_policy.md rule 4's photo-evidence requirement hangs off this
#     column; the orchestrator's enforcement logic is a later step, this is
#     just the data it needs to evaluate against) ---------------------------
evidence_true_order_1 = add_order(ANCHOR - timedelta(days=25), customer_index=7, status="delivered")
evidence_true_item_1 = add_item(evidence_true_order_1, product_by_name["Ceramic Coffee Mug"], 1)

evidence_true_order_2 = add_order(ANCHOR - timedelta(days=18), customer_index=8, status="delivered")
evidence_true_item_2 = add_item(evidence_true_order_2, product_by_name["Memory Foam Pillow"], 1)

evidence_false_order = add_order(ANCHOR - timedelta(days=12), customer_index=9, status="delivered")
evidence_false_item = add_item(evidence_false_order, product_by_name["Cotton Bath Towel Set"], 1)

# --- edge case: refund attempt against a Clearance/Final Sale product under
#     a non-exempt reason code (refund_policy.md rule 9 only exempts
#     defective and wrong_item -- changed_mind is not exempt) --------------
final_sale_order_id = add_order(ANCHOR - timedelta(days=10), customer_index=10, status="delivered")
final_sale_item = add_item(final_sale_order_id, product_by_name["Last-Season Winter Jacket"], 1)

# --- edge case: repeat-refund flag (rule 7) -- 3 approved refunds for one
#     customer, all with requested_at inside the trailing 90-day window from
#     *now* (unlike every other refund in this file, whose requested_at is
#     ANCHOR-relative and has since aged out of that window -- see
#     DECISIONS.md #14). Order dates themselves don't drive any rule outcome
#     here, so they're left ANCHOR-relative like the rest of the file.
#     Charlotte Dubois (customer_index 12) isn't used by any other edge
#     case, to avoid interaction effects. -----------------------------------
repeat_refund_order_1 = add_order(ANCHOR - timedelta(days=60), customer_index=12, status="delivered")
repeat_refund_item_1 = add_item(repeat_refund_order_1, product_by_name["Wireless Keyboard"], 1)

repeat_refund_order_2 = add_order(ANCHOR - timedelta(days=55), customer_index=12, status="delivered")
repeat_refund_item_2 = add_item(repeat_refund_order_2, product_by_name["Wireless Keyboard"], 1)

repeat_refund_order_3 = add_order(ANCHOR - timedelta(days=50), customer_index=12, status="delivered")
repeat_refund_item_3 = add_item(repeat_refund_order_3, product_by_name["Wireless Keyboard"], 1)

# --- high refund-rate products: 5 orders each, most items refunded --------
high_refund_items: dict[str, list[uuid.UUID]] = {p["name"]: [] for p in HIGH_REFUND_PRODUCTS}
for product in HIGH_REFUND_PRODUCTS:
    for j in range(5):
        o_id = add_order(
            ANCHOR - timedelta(days=RNG.randint(10, 150)),
            customer_index=2 + j,
            status=RNG.choice(["delivered", "shipped"]),
        )
        item_id = add_item(o_id, product, 1)
        high_refund_items[product["name"]].append(item_id)
        if product["name"] == "Bluetooth Headphones Pro" and j == 1:
            # refund-05's underlying order (Liam Patel, customer_index 3):
            # its age drives the defective 90-day window eval case, so it's
            # overridden to be time-relative to *now* rather than left
            # pinned to this loop's ANCHOR-relative random draw. Overridden
            # after the fact, not by skipping the RNG call above, so every
            # other order in this loop keeps drawing from the same RNG
            # stream position it always has -- nothing else in this file
            # shifts as a result.
            orders[-1]["order_date"] = datetime.now(timezone.utc) - timedelta(days=150)

# --- remaining filler orders for volume + general realism -----------------
FILLER_PRODUCT_NAMES = [
    "Wireless Mouse V2", "USB-C Charging Cable 6ft", "Stainless Steel Water Bottle",
    "Stainless Steel Water Bottle 32oz", "Ceramic Coffee Mug", "Memory Foam Pillow",
    "Cotton Bath Towel Set", "Men's Running Shoes", "Women's Running Shoes",
    "Fleece Zip Hoodie", "Organic Green Tea (20ct)", "Organic Green Tea (40ct)",
    "Dark Roast Coffee Beans 12oz", "Wireless Keyboard",
]

filler_items: list[uuid.UUID] = []
while len(orders) < 25:
    o_id = add_order(
        ANCHOR - timedelta(days=RNG.randint(1, 300)),
        customer_index=RNG.randint(0, len(customers) - 1),
        status=RNG.choice(ORDER_STATUSES),
    )
    for _ in range(RNG.randint(1, 3)):
        product = product_by_name[RNG.choice(FILLER_PRODUCT_NAMES)]
        item_id = add_item(o_id, product, RNG.randint(1, 2))
        filler_items.append(item_id)

# --- edge case: 12 delayed shipments for the same product, across 12
#     distinct customers -- what get_shipment_status's Part 2 demo query
#     needs to find (past its expected delivery date, never marked
#     delivered). Dates are time-relative to *now*, not ANCHOR, for the same
#     reason as the refund-evaluator fixes: a fixed calendar date would age
#     out of "overdue" relevance as real time passes (see DECISIONS.md #14).
#     Customer indices mix already-used ones with otherwise-untouched ones --
#     shipments have no bearing on refund_evaluator logic, so reuse here
#     creates no interaction effect, unlike the refund-case customer choices.
#     No RNG calls in this block or the contrast block below, so neither
#     shifts the RNG stream position for anything before or after them. -----
DELAYED_SHIPMENT_PRODUCT = product_by_name["Stainless Steel Water Bottle"]
DELAYED_SHIPMENT_CUSTOMER_INDICES = [2, 3, 4, 5, 6, 11, 13, 14, 15, 16, 17, 18]
DELAYED_SHIPMENT_CARRIERS = ["FastFreight", "ParcelPoint", "QuickShip"]

delayed_shipment_orders: list[uuid.UUID] = []
for i, customer_index in enumerate(DELAYED_SHIPMENT_CUSTOMER_INDICES):
    days_overdue = 3 + i  # spread 3-14 days overdue
    o_id = add_order(
        datetime.now(timezone.utc) - timedelta(days=days_overdue + 10),
        customer_index=customer_index,
        status="shipped",
    )
    add_item(o_id, DELAYED_SHIPMENT_PRODUCT, 1)
    delayed_shipment_orders.append(o_id)

# --- contrast: a handful of normal shipments (delivered on-time, in-transit
#     not yet due, and not-yet-shipped) so "everything is delayed" isn't
#     trivially true for the demo query. -----------------------------------
normal_shipment_order_1 = add_order(
    datetime.now(timezone.utc) - timedelta(days=20), customer_index=0, status="delivered"
)
add_item(normal_shipment_order_1, product_by_name["USB-C Charging Cable"], 1)

normal_shipment_order_2 = add_order(
    datetime.now(timezone.utc) - timedelta(days=15), customer_index=1, status="delivered"
)
add_item(normal_shipment_order_2, product_by_name["Wireless Mouse"], 1)

normal_shipment_order_3 = add_order(
    datetime.now(timezone.utc) - timedelta(days=10), customer_index=7, status="delivered"
)
add_item(normal_shipment_order_3, product_by_name["Organic Green Tea (20ct)"], 1)

normal_shipment_order_4 = add_order(
    datetime.now(timezone.utc) - timedelta(days=2), customer_index=8, status="shipped"
)
add_item(normal_shipment_order_4, product_by_name["Men's Running Shoes"], 1)

normal_shipment_order_5 = add_order(
    datetime.now(timezone.utc) - timedelta(days=1), customer_index=9, status="shipped"
)
add_item(normal_shipment_order_5, product_by_name["Dark Roast Coffee Beans 12oz"], 1)

normal_shipment_order_6 = add_order(
    datetime.now(timezone.utc) - timedelta(days=3), customer_index=19, status="shipped"
)
add_item(normal_shipment_order_6, product_by_name["Fleece Zip Hoodie"], 1)

normal_shipment_order_7 = add_order(
    datetime.now(timezone.utc), customer_index=10, status="placed"
)
add_item(normal_shipment_order_7, product_by_name["Women's Running Shoes"], 1)

normal_shipment_order_8 = add_order(
    datetime.now(timezone.utc), customer_index=0, status="placed"
)
add_item(normal_shipment_order_8, product_by_name["Cotton Bath Towel Set"], 1)

# backfill order totals from their items
totals: dict[uuid.UUID, int] = {}
for item in order_items:
    totals[item["order_id"]] = totals.get(item["order_id"], 0) + (
        item["quantity"] * item["unit_price_cents"]
    )
for order in orders:
    order["total_cents"] = totals.get(order["id"], 0)

# ---------------------------------------------------------------------------
# shipments (Part 2 tool: get_shipment_status)
# ---------------------------------------------------------------------------

shipments: list[dict] = []


def add_shipment(
    order_id: uuid.UUID,
    carrier: str,
    status: str,
    expected_delivery_date: datetime,
    shipped_date: datetime | None = None,
    actual_delivery_date: datetime | None = None,
) -> None:
    shipments.append(
        {
            "id": uid("shipment", str(len(shipments) + 1)),
            "order_id": order_id,
            "carrier": carrier,
            "shipped_date": shipped_date,
            "expected_delivery_date": expected_delivery_date,
            "actual_delivery_date": actual_delivery_date,
            "status": status,
        }
    )


for i, o_id in enumerate(delayed_shipment_orders):
    days_overdue = 3 + i
    add_shipment(
        o_id,
        carrier=DELAYED_SHIPMENT_CARRIERS[i % len(DELAYED_SHIPMENT_CARRIERS)],
        status="delayed",
        shipped_date=datetime.now(timezone.utc) - timedelta(days=days_overdue + 8),
        expected_delivery_date=datetime.now(timezone.utc) - timedelta(days=days_overdue),
        actual_delivery_date=None,
    )

# contrast: delivered on-time
add_shipment(
    normal_shipment_order_1,
    carrier="FastFreight",
    status="delivered",
    shipped_date=datetime.now(timezone.utc) - timedelta(days=18),
    expected_delivery_date=datetime.now(timezone.utc) - timedelta(days=15),
    actual_delivery_date=datetime.now(timezone.utc) - timedelta(days=14),
)
add_shipment(
    normal_shipment_order_2,
    carrier="ParcelPoint",
    status="delivered",
    shipped_date=datetime.now(timezone.utc) - timedelta(days=13),
    expected_delivery_date=datetime.now(timezone.utc) - timedelta(days=10),
    actual_delivery_date=datetime.now(timezone.utc) - timedelta(days=10),
)
add_shipment(
    normal_shipment_order_3,
    carrier="QuickShip",
    status="delivered",
    shipped_date=datetime.now(timezone.utc) - timedelta(days=8),
    expected_delivery_date=datetime.now(timezone.utc) - timedelta(days=6),
    actual_delivery_date=datetime.now(timezone.utc) - timedelta(days=6),
)

# contrast: shipped, in transit, not yet due
add_shipment(
    normal_shipment_order_4,
    carrier="FastFreight",
    status="shipped",
    shipped_date=datetime.now(timezone.utc) - timedelta(days=2),
    expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=5),
    actual_delivery_date=None,
)
add_shipment(
    normal_shipment_order_5,
    carrier="ParcelPoint",
    status="shipped",
    shipped_date=datetime.now(timezone.utc) - timedelta(days=1),
    expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=6),
    actual_delivery_date=None,
)
add_shipment(
    normal_shipment_order_6,
    carrier="QuickShip",
    status="shipped",
    shipped_date=datetime.now(timezone.utc) - timedelta(days=3),
    expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=4),
    actual_delivery_date=None,
)

# contrast: not yet shipped
add_shipment(
    normal_shipment_order_7,
    carrier="FastFreight",
    status="pending",
    shipped_date=None,
    expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=10),
    actual_delivery_date=None,
)
add_shipment(
    normal_shipment_order_8,
    carrier="ParcelPoint",
    status="pending",
    shipped_date=None,
    expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=12),
    actual_delivery_date=None,
)

# ---------------------------------------------------------------------------
# refunds
# ---------------------------------------------------------------------------

refunds = []


def add_refund(
    order_item_id: uuid.UUID,
    amount_cents: int,
    reason: str,
    status: str,
    requested_at: datetime,
    evidence_submitted: bool = False,
) -> None:
    refunds.append(
        {
            "id": uid("refund", str(len(refunds) + 1)),
            "order_item_id": order_item_id,
            "amount_cents": amount_cents,
            "reason": reason,
            "status": status,
            "requested_at": requested_at,
            "evidence_submitted": evidence_submitted,
        }
    )


def item_lookup(item_id: uuid.UUID) -> dict:
    return next(i for i in order_items if i["id"] == item_id)


def order_lookup(order_id: uuid.UUID) -> dict:
    return next(o for o in orders if o["id"] == order_id)


# multi-item order: only the headphones item is refunded
_item = item_lookup(multi_item_refunded)
add_refund(
    multi_item_refunded,
    _item["quantity"] * _item["unit_price_cents"],
    "defective",
    "approved",
    order_lookup(multi_order_id)["order_date"] + timedelta(days=6),
)

# structurally valid refund that violates the 14-day changed_mind window.
# Offset from this order's own (now time-relative) order_date rather than a
# fixed day count from ANCHOR, so it stays a past timestamp (order_date is
# now - 45 days) instead of landing in the future.
_item = item_lookup(policy_violation_item)
add_refund(
    policy_violation_item,
    _item["quantity"] * _item["unit_price_cents"],
    "changed_mind",
    "approved",
    order_lookup(policy_order_id)["order_date"] + timedelta(days=20),
)

# damaged_shipping refunds with photo evidence submitted (approvable)
for item_id, order_id in [
    (evidence_true_item_1, evidence_true_order_1),
    (evidence_true_item_2, evidence_true_order_2),
]:
    _item = item_lookup(item_id)
    add_refund(
        item_id,
        _item["quantity"] * _item["unit_price_cents"],
        "damaged_shipping",
        "approved",
        order_lookup(order_id)["order_date"] + timedelta(days=4),
        evidence_submitted=True,
    )

# damaged_shipping refund WITHOUT photo evidence -- the case the
# orchestrator's enforcement logic (not yet built) needs to reject or flag
_item = item_lookup(evidence_false_item)
add_refund(
    evidence_false_item,
    _item["quantity"] * _item["unit_price_cents"],
    "damaged_shipping",
    "denied",
    order_lookup(evidence_false_order)["order_date"] + timedelta(days=3),
    evidence_submitted=False,
)

# final-sale exclusion test case: changed_mind is not an exempt reason code
# (only defective/wrong_item are, per refund_policy.md rule 9) -- this is
# the row that should get blocked once the orchestrator enforces the rule
_item = item_lookup(final_sale_item)
add_refund(
    final_sale_item,
    _item["quantity"] * _item["unit_price_cents"],
    "changed_mind",
    "pending",
    order_lookup(final_sale_order_id)["order_date"] + timedelta(days=5),
    evidence_submitted=False,
)

# repeat-refund flag (rule 7): 3 approved refunds within 90 days of *now*
for item_id, days_ago, reason in [
    (repeat_refund_item_1, 10, "defective"),
    (repeat_refund_item_2, 30, "wrong_item"),
    (repeat_refund_item_3, 55, "changed_mind"),
]:
    _item = item_lookup(item_id)
    add_refund(
        item_id,
        _item["quantity"] * _item["unit_price_cents"],
        reason,
        "approved",
        datetime.now(timezone.utc) - timedelta(days=days_ago),
    )

# high refund-rate products: 4 of 5 items refunded (approved), within policy
for product_name, item_ids in high_refund_items.items():
    for item_id in item_ids[:4]:
        _item = item_lookup(item_id)
        _order = order_lookup(_item["order_id"])
        add_refund(
            item_id,
            _item["quantity"] * _item["unit_price_cents"],
            RNG.choice(["defective", "damaged_shipping"]),
            "approved",
            _order["order_date"] + timedelta(days=RNG.randint(3, 20)),
        )

# filler refunds against the general filler items, to reach >= 20 total
FILLER_REASONS = ["defective", "wrong_item", "changed_mind", "damaged_shipping"]
FILLER_STATUSES = ["approved", "denied", "pending"]

needed = max(0, 20 - len(refunds))
candidates = RNG.sample(filler_items, k=min(needed + 3, len(filler_items)))
for item_id in candidates[:needed]:
    _item = item_lookup(item_id)
    _order = order_lookup(_item["order_id"])
    add_refund(
        item_id,
        _item["quantity"] * _item["unit_price_cents"],
        RNG.choice(FILLER_REASONS),
        RNG.choice(FILLER_STATUSES),
        _order["order_date"] + timedelta(days=RNG.randint(2, 30)),
    )

# ---------------------------------------------------------------------------
# support_tickets
# ---------------------------------------------------------------------------

support_tickets = []


def add_ticket(
    customer_index: int,
    category: str,
    description: str,
    created_at: datetime,
    order_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    resolved_at: datetime | None = None,
) -> None:
    support_tickets.append(
        {
            "id": uid("ticket", str(len(support_tickets) + 1)),
            "customer_id": customers[customer_index % len(customers)]["id"],
            "order_id": order_id,
            "product_id": product_id,
            "category": category,
            "description": description,
            "created_at": created_at,
            "resolved_at": resolved_at,
        }
    )


# edge case: general inquiry, not tied to any order or product
add_ticket(
    3,
    "other",
    "Asked whether we ship to a new APAC region not yet listed at checkout.",
    ANCHOR - timedelta(days=15),
    resolved_at=ANCHOR - timedelta(days=14),
)

# shipping ticket tied to an order but no specific product
add_ticket(
    4,
    "shipping",
    "Package shows delivered but customer says it never arrived.",
    ANCHOR - timedelta(days=20),
    order_id=multi_order_id,
)

# product-defect tickets tied to the high-refund-rate products
for product in HIGH_REFUND_PRODUCTS:
    item_id = high_refund_items[product["name"]][0]
    _item = item_lookup(item_id)
    add_ticket(
        5,
        "product_defect",
        f"Customer reports the {product['name']} stopped working within a week.",
        order_lookup(_item["order_id"])["order_date"] + timedelta(days=2),
        order_id=_item["order_id"],
        product_id=product["id"],
        resolved_at=order_lookup(_item["order_id"])["order_date"] + timedelta(days=9),
    )

# billing ticket, no product, tied to an order
add_ticket(
    6,
    "billing",
    "Customer was charged twice for the same order and wants a refund of the duplicate charge.",
    ANCHOR - timedelta(days=50),
    order_id=policy_order_id,
)

# filler tickets to reach >= 20 rows total
TICKET_CATEGORIES = ["shipping", "product_defect", "billing", "other"]
FILLER_DESCRIPTIONS = [
    "Customer asking for an order status update.",
    "Requesting invoice copy for expense reporting.",
    "Item arrived with visible shipping damage.",
    "Question about return window for a recent purchase.",
    "Complaint about slow delivery time.",
    "Asked to update billing address on file.",
    "Reported a minor cosmetic defect on arrival.",
    "General question about loyalty program points.",
]

while len(support_tickets) < 20:
    category = RNG.choice(TICKET_CATEGORIES)
    order_id = None
    product_id = None
    if category != "other" and RNG.random() < 0.7:
        order = RNG.choice(orders)
        order_id = order["id"]
        items_for_order = [i for i in order_items if i["order_id"] == order_id]
        if items_for_order and RNG.random() < 0.6:
            product_id = RNG.choice(items_for_order)["product_id"]
    created = ANCHOR - timedelta(days=RNG.randint(1, 250))
    resolved = created + timedelta(days=RNG.randint(1, 10)) if RNG.random() < 0.5 else None
    add_ticket(
        RNG.randint(0, len(customers) - 1),
        category,
        RNG.choice(FILLER_DESCRIPTIONS),
        created,
        order_id=order_id,
        product_id=product_id,
        resolved_at=resolved,
    )


# ---------------------------------------------------------------------------
# seed
# ---------------------------------------------------------------------------

def seed() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE support_tickets, refunds, shipments, order_items, "
                "orders, products, customers CASCADE"
            )
        )
        conn.execute(insert(Customer), customers)
        conn.execute(insert(Product), products)
        conn.execute(insert(Order), orders)
        conn.execute(insert(OrderItem), order_items)
        conn.execute(insert(Shipment), shipments)
        conn.execute(insert(Refund), refunds)
        conn.execute(insert(SupportTicket), support_tickets)

    print(
        f"Seeded {len(customers)} customers, {len(products)} products, "
        f"{len(orders)} orders, {len(order_items)} order_items, "
        f"{len(shipments)} shipments, {len(refunds)} refunds, "
        f"{len(support_tickets)} support_tickets."
    )


if __name__ == "__main__":
    seed()
