# Refund Policy

This document defines the rules governing refund eligibility, approval, and processing for eCommerce orders.

## Standard Return Window

Items may be returned within 30 days of the purchase date for any reason. Refunds issued under the standard return window are refunded to the original payment method used for the purchase.

## Defective Items

Items returned under the `defective` reason code may be refunded up to 90 days from the purchase date. The 90-day window for a `defective` refund applies regardless of the standard 30-day return window, and takes precedence over the standard 30-day return window when the two conflict.

## Changed Mind

Items returned under the `changed_mind` reason code must be returned within 14 days of the purchase date. The 14-day window for a `changed_mind` refund is shorter than the standard 30-day return window.

## Damaged in Shipping

Items returned under the `damaged_shipping` reason code have no time limit for return. A refund request under the `damaged_shipping` reason code requires supporting photo evidence before the refund can be processed.

<!-- TODO: clarify — the Part 1 refunds schema has no field to store or reference photo evidence. The photo-evidence requirement for `damaged_shipping` refunds cannot currently be verified structurally; it needs either a schema addition (e.g. an evidence URL column) or a defined out-of-band evidence store before it can be enforced. -->

## Wrong Item Shipped

Items returned under the `wrong_item` reason code have no time limit for return. There is no time limit for a `wrong_item` refund because the shipping error is the company's responsibility, not the customer's.

## Approval Threshold

A refund with an amount greater than $200 requires manager approval before the refund can be processed. The $200 approval threshold applies regardless of the refund's reason code.

## Repeat-Refund Flag

A customer with 3 or more approved refunds within a rolling 90-day window is flagged for manual review. Once a customer is flagged for manual review, further refund requests from that customer are not auto-approved, regardless of the individual refund's reason code or amount.

## Partial Refunds

When only some units of a multi-quantity order line are being returned, the refund amount is prorated by the quantity being returned. A partial return of a multi-quantity order line is not treated as a full-line refund of the entire order line.

## Final-Sale Exclusion

Items in a `clearance` or `final_sale` product category are not eligible for a refund. An item in a `clearance` or `final_sale` product category may still be refunded under the `defective` reason code or the `wrong_item` reason code, per the 90-day defective-items window and the no-time-limit wrong-item-shipped rule.

<!-- TODO: clarify — `products.category` in the Part 1 schema is unconstrained free text (no CHECK constraint enumerating allowed values), so there is no governed way to reliably identify `clearance` or `final_sale` items today. This rule needs either a CHECK constraint on `products.category` or a separate boolean flag column before it can be enforced structurally. -->

## Shipping Cost Non-Refundable

The original shipping charge paid on an order is not refunded. An exception to the shipping-cost policy applies when the refund reason code is `damaged_shipping` or `wrong_item`, in which case the original shipping charge is refunded along with the item.
