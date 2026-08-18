from app.orchestrator.refund_extraction import extract_refund_request


def test_live_quantity_is_not_folded_into_product_identifier():
    """Reproduces the live bug: a request naming a quantity ('2 Ergonomic
    Desk Chairs') got extracted as product_identifier='2 Ergonomic Desk
    Chairs', which then fails resolve_order_item()'s ILIKE match against
    the real product name, 'Ergonomic Desk Chair'. The number must not
    end up in the extracted product name."""
    result = extract_refund_request(
        "Hi, this is Henry Osei. I bought 2 Ergonomic Desk Chairs and "
        "they're not what I ordered - you sent me the wrong item. "
        "I'd like a refund."
    )
    assert result.product_identifier == "Ergonomic Desk Chair"
