# Shipping Policy

This document defines delivery timelines for standard and expedited shipping, and the handling process when an order arrives damaged in transit.

## Standard Shipping

Standard shipping orders are delivered within 10 business days of the order being placed.

## Expedited Shipping

Expedited shipping orders are delivered within 3 business days of the order being placed, for an additional shipping fee of 14.95.

## Damaged in Transit

An order that arrives damaged in transit is handled under the `damaged_shipping` refund reason code. A `damaged_shipping` refund has no return time limit and requires supporting photo evidence before the refund can be processed, per the refund policy's damaged-in-shipping rule.

<!-- TODO: clarify — the Part 1 orders schema has no shipping-method field, so standard and expedited orders cannot currently be distinguished structurally. The standard and expedited delivery windows defined in this document need either a schema addition (e.g. a `shipping_method` column on `orders`) or confirmation that shipping method is tracked in a separate system. -->
