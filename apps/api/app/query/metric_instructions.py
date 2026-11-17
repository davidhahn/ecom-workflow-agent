"""Metric definitions shared by both SQL-generating model paths."""

SQL_METRIC_INSTRUCTIONS = """When a question asks for a rate or percentage over order line items (e.g.
"refund rate"), compute both sides of the ratio in the same unit as the
question — use SUM(order_items.quantity), not a row count, since one
order_items row can represent more than one unit sold. Only count a refund
toward a rate if it reflects a completed outcome (refunds.status =
'approved') — a pending or denied refund hasn't actually happened.

Example — "What is the refund rate for a product category?"
  Wrong: COUNT(DISTINCT refunds.id) / COUNT(DISTINCT order_items.id)
    (counts rows, not units, and counts every refund regardless of status)
  Right: SUM(order_items.quantity) FILTER (WHERE refunds.status = 'approved')
         / SUM(order_items.quantity)
    (counts units sold, and only refunds that were actually approved)"""
