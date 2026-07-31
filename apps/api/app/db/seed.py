"""Re-runnable seed script for the Part 1 schema (customers, products, orders,
order_items, refunds, support_tickets, shipments) plus the Part 3 web_analytics
and campaigns tables. Truncates the nine tables and reinserts deterministic
fixture data — safe to run against a fresh or already-seeded database.

Usage:
    poetry run python -m app.db.seed
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import insert, text

from app.db.models import (
    Campaign,
    Customer,
    Order,
    OrderItem,
    Product,
    Refund,
    Shipment,
    SupportTicket,
    WebAnalytics,
)
from app.db.session import engine

NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")
RNG = random.Random(20260706)

ANCHOR = datetime(2026, 1, 1, tzinfo=timezone.utc)

# Shared "now" for eval-relevant rows; everything else stays ANCHOR-relative
# (see DECISIONS.md #14).
NOW = datetime.now(timezone.utc)


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

# --- edge case: changed_mind refund violating the 14-day window (rule 3).
#     NOW-relative so refund-04 stays reachable — see DECISIONS.md #14. ----
policy_order_id = add_order(NOW - timedelta(days=45), customer_index=1, status="delivered")
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

# --- edge case: repeat-refund flag (rule 7) -- 3 approved refunds within
#     90 days of NOW (see DECISIONS.md #14). Order dates don't matter here,
#     so they stay ANCHOR-relative. Charlotte Dubois (customer_index 12)
#     isn't reused elsewhere, to avoid interaction effects. -----------------
repeat_refund_order_1 = add_order(ANCHOR - timedelta(days=60), customer_index=12, status="delivered")
repeat_refund_item_1 = add_item(repeat_refund_order_1, product_by_name["Wireless Keyboard"], 1)

repeat_refund_order_2 = add_order(ANCHOR - timedelta(days=55), customer_index=12, status="delivered")
repeat_refund_item_2 = add_item(repeat_refund_order_2, product_by_name["Wireless Keyboard"], 1)

repeat_refund_order_3 = add_order(ANCHOR - timedelta(days=50), customer_index=12, status="delivered")
repeat_refund_item_3 = add_item(repeat_refund_order_3, product_by_name["Wireless Keyboard"], 1)

# --- edge case: approval threshold (rule 6) -- 2x Ergonomic Desk Chair
#     ($159.99 each) = $319.98, over the $200 threshold. wrong_item has no
#     time window, so ANCHOR-relative is fine here. ------------------------
threshold_order_id = add_order(ANCHOR - timedelta(days=8), customer_index=13, status="delivered")
threshold_item = add_item(threshold_order_id, product_by_name["Ergonomic Desk Chair"], 2)

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
            # refund-05 needs this order (Liam Patel) ~90 days old, so it's
            # overridden to NOW-relative here, after the RNG draw above --
            # keeps every other order in this loop unaffected.
            orders[-1]["order_date"] = NOW - timedelta(days=150)

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

# ---------------------------------------------------------------------------
# revenue-dip story (Part 3 demo query: "why did revenue drop last week?")
# -- NOW-relative (shared NOW from the top of the file) so the dip stays in
# the trailing 14 days across reseeds. Revenue is never stored directly --
# it's SUM(order_items.quantity * unit_price_cents) over these orders. -----


def _dip_order(days_ago: int, product_name: str, customer_index: int) -> uuid.UUID:
    o_id = add_order(NOW - timedelta(days=days_ago), customer_index=customer_index, status="delivered")
    add_item(o_id, product_by_name[product_name], 1)
    return o_id


# Same product rotation/price range in both weeks -- the dip is driven by
# fewer orders, not by swapping in cheaper products, so a "lower order
# values" story isn't accidentally smuggled in alongside the "fewer
# orders" one. Counts here (14 vs 4) are chosen net of the pre-existing
# normal_shipment_order_*/delayed_shipment_orders rows immediately above,
# which land unevenly across these same two windows by construction (they
# exist to test shipment-delay/contrast logic, not this story) -- 2 of
# them fall in the prior window, 5 in the recent one, at fixed day-offsets
# that don't shift across reseeds. Net of that fixed skew, the *combined*
# result queried straight off `orders`/`order_items` (below, not just
# these rows in isolation) is still a clean ~28% revenue drop on ~44%
# fewer orders -- confirmed by direct SQL, not just this arithmetic.
DIP_ROTATION = [
    "Bluetooth Headphones", "Men's Running Shoes", "Fleece Zip Hoodie",
    "Wireless Keyboard", "Memory Foam Pillow", "Cotton Bath Towel Set",
]

# prior week (days 13-7 ago): normal volume, 14 orders across 7 days
dip_prior_orders = [
    _dip_order(13, DIP_ROTATION[0], 0), _dip_order(13, DIP_ROTATION[1], 1),
    _dip_order(12, DIP_ROTATION[2], 2), _dip_order(12, DIP_ROTATION[3], 3),
    _dip_order(11, DIP_ROTATION[4], 4), _dip_order(11, DIP_ROTATION[5], 5),
    _dip_order(10, DIP_ROTATION[0], 6), _dip_order(10, DIP_ROTATION[1], 7),
    _dip_order(9, DIP_ROTATION[2], 8), _dip_order(9, DIP_ROTATION[3], 9),
    _dip_order(8, DIP_ROTATION[4], 10), _dip_order(8, DIP_ROTATION[5], 11),
    _dip_order(7, DIP_ROTATION[0], 12), _dip_order(7, DIP_ROTATION[1], 13),
]

# recent week (days 6-0 ago): the drop -- just 4 orders across the same 7
# days, one per active day, real (not discounted) product prices so the
# dip reads as fewer people buying, not a clearance-style value collapse.
dip_recent_orders = [
    _dip_order(6, "Ergonomic Desk Chair", 14),
    _dip_order(4, DIP_ROTATION[3], 15),
    _dip_order(2, DIP_ROTATION[4], 16),
    _dip_order(0, DIP_ROTATION[5], 17),
]

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
        NOW - timedelta(days=days_ago),
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

# revenue-dip story: refunds against the dip orders above, at roughly the
# SAME rate in both windows once combined with the pre-existing orders
# that also land in these two windows (2 refunds / 16 combined prior
# orders = 12.5%, 1 refund / 9 combined recent orders = 11.1%) -- the
# deliberate red herring. A correct investigation checks refunds, finds
# this rate essentially unchanged on both sides of the drop, and rules
# refunds out rather than wrongly attributing the revenue dip to them.
# All "defective"/"approved" so a rate computed either as
# all-refunds/orders or approved-refunds/orders comes out the same.
for order_id in [dip_prior_orders[0], dip_prior_orders[8]]:
    item_id = next(i["id"] for i in order_items if i["order_id"] == order_id)
    _item = item_lookup(item_id)
    add_refund(
        item_id,
        _item["quantity"] * _item["unit_price_cents"],
        "defective",
        "approved",
        order_lookup(order_id)["order_date"] + timedelta(days=3),
    )
for order_id in [dip_recent_orders[0]]:
    item_id = next(i["id"] for i in order_items if i["order_id"] == order_id)
    _item = item_lookup(item_id)
    add_refund(
        item_id,
        _item["quantity"] * _item["unit_price_cents"],
        "defective",
        "approved",
        order_lookup(order_id)["order_date"] + timedelta(days=1),
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
# web_analytics + campaigns (Part 3 demo query). NOW-relative, not ANCHOR --
# see DECISIONS.md #14. No revenue column here; revenue is computed from
# orders (see above).
# ---------------------------------------------------------------------------

web_analytics = []

# prior week (days 13-7 ago): normal baseline.
_PRIOR_ANALYTICS = [
    (13, 1280, 4200, "0.0305"), (12, 1350, 4450, "0.0320"), (11, 1310, 4300, "0.0298"),
    (10, 1290, 4180, "0.0312"), (9, 1400, 4700, "0.0335"), (8, 1330, 4300, "0.0301"),
    (7, 1360, 4450, "0.0318"),
]
# recent week (days 6-0 ago): sessions and conversion_rate both ~25-27%
# below the prior week's daily average -- a real, deliberate signal, not
# day-to-day noise. Begins the day after the campaign below ends.
_RECENT_ANALYTICS = [
    (6, 950, 3050, "0.0230"), (5, 1020, 3300, "0.0245"), (4, 980, 3150, "0.0220"),
    (3, 1005, 3220, "0.0238"), (2, 940, 3010, "0.0215"), (1, 1010, 3260, "0.0250"),
    (0, 990, 3180, "0.0228"),
]
for days_ago, sessions, page_views, conversion_rate in _PRIOR_ANALYTICS + _RECENT_ANALYTICS:
    web_analytics.append(
        {
            "id": uid("web_analytics", str(len(web_analytics) + 1)),
            "date": (NOW - timedelta(days=days_ago)).date(),
            "sessions": sessions,
            "page_views": page_views,
            "conversion_rate": Decimal(conversion_rate),
        }
    )

# The campaign whose end_date lines up with the drop: ends 1 day before the
# recent (lower-performing) week begins. paid_social, a channel plausibly
# responsible for a traffic dip when it stops running -- see
# docs/notes/campaign-launch-notes.md for the narrative context a caller
# investigating this would want alongside these rows.
campaign_end_date = (NOW - timedelta(days=7)).date()
campaigns = [
    {
        "id": uid("campaign", "1"),
        "name": "Paid Social Growth Push",
        "channel": "paid_social",
        "start_date": campaign_end_date - timedelta(days=30),
        "end_date": campaign_end_date,
        "budget_cents": 1_850_000,
        "status": "ended",
    }
]


# ---------------------------------------------------------------------------
# seed
# ---------------------------------------------------------------------------

def seed() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE support_tickets, refunds, shipments, order_items, "
                "orders, products, customers, web_analytics, campaigns CASCADE"
            )
        )
        conn.execute(insert(Customer), customers)
        conn.execute(insert(Product), products)
        conn.execute(insert(Order), orders)
        conn.execute(insert(OrderItem), order_items)
        conn.execute(insert(Shipment), shipments)
        conn.execute(insert(Refund), refunds)
        conn.execute(insert(SupportTicket), support_tickets)
        conn.execute(insert(WebAnalytics), web_analytics)
        conn.execute(insert(Campaign), campaigns)

    print(
        f"Seeded {len(customers)} customers, {len(products)} products, "
        f"{len(orders)} orders, {len(order_items)} order_items, "
        f"{len(shipments)} shipments, {len(refunds)} refunds, "
        f"{len(support_tickets)} support_tickets, "
        f"{len(web_analytics)} web_analytics, {len(campaigns)} campaigns."
    )


if __name__ == "__main__":
    seed()
