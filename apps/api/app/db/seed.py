"""Re-runnable seed script for the Part 1 schema (customers, products, orders,
order_items, refunds, support_tickets). Truncates the six tables and reinserts
deterministic fixture data — safe to run against a fresh or already-seeded
database.

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

# --- edge case: refund that is structurally valid but outside the 45-day
#     policy window once requested_at - order_date is computed -------------
policy_order_id = add_order(ANCHOR - timedelta(days=200), customer_index=1, status="delivered")
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

# backfill order totals from their items
totals: dict[uuid.UUID, int] = {}
for item in order_items:
    totals[item["order_id"]] = totals.get(item["order_id"], 0) + (
        item["quantity"] * item["unit_price_cents"]
    )
for order in orders:
    order["total_cents"] = totals.get(order["id"], 0)

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

# structurally valid refund that violates the 45-day policy window
_item = item_lookup(policy_violation_item)
add_refund(
    policy_violation_item,
    _item["quantity"] * _item["unit_price_cents"],
    "changed_mind",
    "approved",
    order_lookup(policy_order_id)["order_date"] + timedelta(days=60),
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
                "TRUNCATE TABLE support_tickets, refunds, order_items, "
                "orders, products, customers CASCADE"
            )
        )
        conn.execute(insert(Customer), customers)
        conn.execute(insert(Product), products)
        conn.execute(insert(Order), orders)
        conn.execute(insert(OrderItem), order_items)
        conn.execute(insert(Refund), refunds)
        conn.execute(insert(SupportTicket), support_tickets)

    print(
        f"Seeded {len(customers)} customers, {len(products)} products, "
        f"{len(orders)} orders, {len(order_items)} order_items, "
        f"{len(refunds)} refunds, {len(support_tickets)} support_tickets."
    )


if __name__ == "__main__":
    seed()
