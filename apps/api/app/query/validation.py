import os

import sqlglot
from sqlglot import exp

from app.query.constants import ALLOWED_TABLES, BLOCKED_COLUMNS, BLOCKED_FUNCTIONS

DIALECT = "postgres"
DEFAULT_LIMIT = 500
DEFAULT_COST_THRESHOLD = 10_000.0


class SqlRejected(Exception):
    def __init__(self, layer: str, reason: str):
        self.layer = layer
        self.reason = reason
        super().__init__(reason)


def _blocked_column_names() -> set[str]:
    return {column for _, column in BLOCKED_COLUMNS}


def validate_ast(sql: str) -> exp.Select:
    """Layer 1 — static AST validation. Raises SqlRejected on any violation,
    otherwise returns the parsed, validated Select node."""
    try:
        statements = sqlglot.parse(sql, read=DIALECT)
    except sqlglot.errors.ParseError as e:
        raise SqlRejected("layer1_ast", f"SQL failed to parse: {e}") from e

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SqlRejected(
            "layer1_ast",
            f"expected exactly one SQL statement, got {len(statements)}",
        )

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        raise SqlRejected(
            "layer1_ast", f"statement must be a SELECT, got {type(statement).__name__}"
        )

    _check_table_allowlist(statement)
    _check_no_select_star(statement)
    _check_no_blocked_columns(statement)
    _check_no_blocked_functions(statement)

    return statement


def _check_table_allowlist(statement: exp.Select) -> None:
    for table in statement.find_all(exp.Table):
        if table.db:
            raise SqlRejected(
                "layer1_ast",
                f"query references schema-qualified table '{table.sql(dialect=DIALECT)}', "
                "only the 6 Part 1 tables in the default schema are allowed",
            )
        if table.name not in ALLOWED_TABLES:
            raise SqlRejected(
                "layer1_ast",
                f"query references disallowed table '{table.name}'",
            )


def _check_no_select_star(statement: exp.Select) -> None:
    # Only a real SELECT * or SELECT t.* counts - a Star buried inside a
    # function argument, like COUNT(*), is a row count, not a wildcard
    # column list. find(exp.Star) used to match both, since it searches
    # the whole subtree instead of just the top of each select expression.
    for select_expr in statement.expressions:
        core = select_expr.this if isinstance(select_expr, exp.Alias) else select_expr
        is_bare_star = isinstance(core, exp.Star)
        is_qualified_star = isinstance(core, exp.Column) and isinstance(core.this, exp.Star)
        if is_bare_star or is_qualified_star:
            raise SqlRejected(
                "layer1_ast",
                "bare SELECT * is not allowed; list columns explicitly",
            )


def _check_no_blocked_columns(statement: exp.Select) -> None:
    blocked = _blocked_column_names()
    for select_expr in statement.expressions:
        for column in select_expr.find_all(exp.Column):
            if column.name.lower() in blocked:
                raise SqlRejected(
                    "layer1_ast",
                    f"query selects blocked column '{column.name}'",
                )


def _check_no_blocked_functions(statement: exp.Select) -> None:
    for node in statement.walk():
        if not isinstance(node, exp.Func):
            continue
        name = node.name if isinstance(node.name, str) else ""
        if not name and isinstance(node.this, str):
            name = node.this
        if name.lower() in BLOCKED_FUNCTIONS:
            raise SqlRejected(
                "layer1_ast",
                f"query calls disallowed function '{name}'",
            )


def apply_default_limit(statement: exp.Select) -> exp.Select:
    """Layer 2 (part 1) — auto-append LIMIT 500 if the query has no limit clause."""
    if statement.args.get("limit") is None:
        statement = statement.limit(DEFAULT_LIMIT)
    return statement


def render_sql(statement: exp.Select) -> str:
    return statement.sql(dialect=DIALECT)


def check_cost(estimated_cost: float) -> None:
    """Layer 2 (part 2) — reject if the EXPLAIN cost exceeds the configured threshold."""
    threshold = float(os.environ.get("QUERY_COST_THRESHOLD", DEFAULT_COST_THRESHOLD))
    if estimated_cost > threshold:
        raise SqlRejected(
            "layer2_cost",
            f"estimated cost {estimated_cost:.1f} exceeds threshold {threshold:.1f}",
        )
