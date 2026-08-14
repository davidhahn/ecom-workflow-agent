"""Tests for _check_no_select_star(), the layer 1 AST check that rejects a
bare SELECT * but has to let COUNT(*) through. DECISIONS.md #34 first found
this as a validator bug: find(exp.Star) searched the whole expression tree,
so it caught the Star buried inside COUNT(*) too. These tests cover the fix
directly, since nothing tested this check on its own before now."""

import pytest

from app.query.validation import SqlRejected, validate_ast


def test_bare_select_star_is_rejected():
    with pytest.raises(SqlRejected):
        validate_ast("SELECT * FROM products")


def test_qualified_select_star_is_rejected():
    with pytest.raises(SqlRejected):
        validate_ast("SELECT p.* FROM products p")


def test_count_star_is_allowed():
    validate_ast("SELECT COUNT(*) AS total FROM products")


def test_count_star_without_alias_is_allowed():
    validate_ast("SELECT COUNT(*) FROM products")


def test_count_distinct_star_is_allowed():
    validate_ast("SELECT COUNT(DISTINCT *) FROM products")


def test_multiplication_is_allowed():
    validate_ast("SELECT quantity * unit_price_cents AS line_total FROM order_items")
