"""Structural fallback for a gap check_groundedness() can't catch: it only
verifies that a cited rule number was actually retrieved, not that the
*data-driven* part of an answer is backed by any tool result at all. An
answer can be perfectly grounded (every rule citation checks out) while
still fabricating a claim like "3 orders could be at risk of delay" from
orders.status, which has no notion of shipment delay whatsoever.

This is a separate, additional check — it does not modify or replace
check_groundedness(). Same accepted tradeoff as that check's title-matching
(see DECISIONS.md #9): a keyword heuristic, not reading comprehension. It
can false-positive on an answer that uses one of these words generically,
and it will miss a fabrication phrased without any of them. Biased toward
over-flagging on purpose — an unnecessary warning is cheaper than a
confidently fabricated shipment claim going unflagged.
"""

# Topics the current toolset (run_sql_query against the 6 Part 1 tables,
# search_policy) has no way to actually answer from. get_shipment_status
# exists (app/shipments/) but isn't wired into /query/analyze yet — see
# DECISIONS.md; once it is, this list/check should be revisited rather than
# assumed still correct.
UNCOVERED_TOPIC_KEYWORDS = [
    "delay",
    "delayed",
    "shipment",
    "shipping status",
    "tracking",
    "carrier",
    "in transit",
]


def _mentions_uncovered_topic(answer: str) -> bool:
    normalized = answer.lower()
    return any(keyword in normalized for keyword in UNCOVERED_TOPIC_KEYWORDS)


def _sql_referenced_shipments(generated_sql: list[str]) -> bool:
    return any("shipments" in sql.lower() for sql in generated_sql)


def check_topic_coverage(answer: str, sql_used: bool, generated_sql: list[str]) -> bool:
    """True if `answer` talks about a topic the current toolset can't cover
    and no SQL call in this request actually queried the shipments table.

    generated_sql is the actual SQL text from every run_sql_query call made
    during this request (not just the sql_used flag) — a query that ran but
    never touched shipments must still be flagged, same as no query at all.
    """
    if not _mentions_uncovered_topic(answer):
        return False
    if sql_used and _sql_referenced_shipments(generated_sql):
        return False
    return True
