import json
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.caching.cache import cache_get, cache_set, normalize_key
from app.observability.logger import request_log_span
from app.query.audit import record_attempt
from app.query.claude_client import ClaudeProposalError, ProposedQuery, propose_sql
from app.query.db_readonly import readonly_engine
from app.query.schemas import SqlQueryResponse
from app.query.validation import (
    DEFAULT_LIMIT,
    SqlRejected,
    apply_default_limit,
    check_cost,
    render_sql,
    validate_ast,
)

# Postgres SQLSTATE codes: 42501 = insufficient_privilege, 57014 = query_canceled
# (statement_timeout). Both are the layer 3 DB-level backstop catching what
# layers 1-2 were supposed to have already stopped.
_INSUFFICIENT_PRIVILEGE = "42501"
_QUERY_CANCELED = "57014"


@dataclass
class ExecutedQuery:
    response: SqlQueryResponse
    audit_id: uuid.UUID


def _pg_sqlstate(exc: Exception) -> str | None:
    orig = getattr(exc, "orig", None)
    return getattr(orig, "sqlstate", None)


def _get_estimated_cost(sql: str) -> float:
    with readonly_engine.connect() as conn:
        result = conn.execute(text(f"EXPLAIN (FORMAT JSON) {sql}"))
        raw = result.scalar()
    plan = raw if isinstance(raw, list) else json.loads(raw)
    return float(plan[0]["Plan"]["Total Cost"])


def run_sql_query(question: str, *, bypass_cache: bool = False) -> SqlQueryResponse:
    with request_log_span("sql", question) as log:
        cache_key = normalize_key(question)
        cached = None if bypass_cache else cache_get("sql", cache_key)
        if cached is not None:
            log.cached = True
            log.input_tokens = 0
            log.output_tokens = 0
            response = cached.model_copy(update={"cached": True})
            log.output = response.model_dump(mode="json")
            return response

        try:
            proposed = propose_sql(question)
        except ClaudeProposalError as e:
            audit_id = record_attempt(
                question=question,
                generated_sql=None,
                stated_intent=None,
                status="error",
                layer_outcomes={"claude_proposal": {"passed": False, "reason": str(e)}},
                rejection_reason=str(e),
            )
            log.sql_query_audit_id = audit_id
            response = SqlQueryResponse(status="error", rejection_reason=str(e))
            log.output = response.model_dump(mode="json")
            return response

        log.add_usage(proposed.usage)
        executed = execute_proposed_query(question, proposed)
        log.sql_query_audit_id = executed.audit_id
        log.output = executed.response.model_dump(mode="json")
        if not bypass_cache:
            cache_set("sql", cache_key, executed.response)
        return executed.response


def execute_proposed_query(question: str, proposed: ProposedQuery) -> ExecutedQuery:
    """Runs an already-proposed (query, intent) pair through layers 1-4.

    Split out from run_sql_query so callers that already have a Claude-
    generated query in hand — e.g. the /query/analyze orchestrator, which
    gets run_sql_query's tool call as part of its own tool loop — can reuse
    the exact same safety pipeline without a second, redundant Claude call
    to re-derive the same query.
    """
    layer_outcomes: dict = {"claude_proposal": {"passed": True}}

    # Layer 1 — static AST validation
    try:
        statement = validate_ast(proposed.query)
    except SqlRejected as e:
        layer_outcomes["layer1_ast"] = {"passed": False, "reason": e.reason}
        audit_id = record_attempt(
            question=question,
            generated_sql=proposed.query,
            stated_intent=proposed.intent,
            status="rejected",
            layer_outcomes=layer_outcomes,
            rejection_reason=e.reason,
        )
        return ExecutedQuery(
            response=SqlQueryResponse(
                status="rejected", sql_executed=proposed.query, rejection_reason=e.reason
            ),
            audit_id=audit_id,
        )
    layer_outcomes["layer1_ast"] = {"passed": True}

    had_explicit_limit = statement.args.get("limit") is not None
    statement = apply_default_limit(statement)
    final_sql = render_sql(statement)

    # Layer 2 — cost gate (EXPLAIN, pre-execution)
    try:
        estimated_cost = _get_estimated_cost(final_sql)
    except DBAPIError as e:
        sqlstate = _pg_sqlstate(e)
        if sqlstate == _INSUFFICIENT_PRIVILEGE:
            reason = f"database denied access while planning the query: {e.orig}"
            layer_outcomes["layer3_db"] = {"passed": False, "reason": reason}
            audit_id = record_attempt(
                question=question,
                generated_sql=final_sql,
                stated_intent=proposed.intent,
                status="rejected",
                layer_outcomes=layer_outcomes,
                rejection_reason=reason,
            )
            return ExecutedQuery(
                response=SqlQueryResponse(
                    status="rejected", sql_executed=final_sql, rejection_reason=reason
                ),
                audit_id=audit_id,
            )
        reason = f"failed to plan query: {e}"
        layer_outcomes["layer2_cost"] = {"passed": False, "reason": reason}
        audit_id = record_attempt(
            question=question,
            generated_sql=final_sql,
            stated_intent=proposed.intent,
            status="error",
            layer_outcomes=layer_outcomes,
            rejection_reason=reason,
        )
        return ExecutedQuery(
            response=SqlQueryResponse(
                status="error", sql_executed=final_sql, rejection_reason=reason
            ),
            audit_id=audit_id,
        )

    try:
        check_cost(estimated_cost)
    except SqlRejected as e:
        layer_outcomes["layer2_cost"] = {
            "passed": False,
            "reason": e.reason,
            "estimated_cost": estimated_cost,
        }
        audit_id = record_attempt(
            question=question,
            generated_sql=final_sql,
            stated_intent=proposed.intent,
            status="rejected",
            layer_outcomes=layer_outcomes,
            rejection_reason=e.reason,
            estimated_cost=estimated_cost,
        )
        return ExecutedQuery(
            response=SqlQueryResponse(
                status="rejected",
                sql_executed=final_sql,
                rejection_reason=e.reason,
                estimated_cost=estimated_cost,
            ),
            audit_id=audit_id,
        )
    layer_outcomes["layer2_cost"] = {"passed": True, "estimated_cost": estimated_cost}

    # Layer 3 — execute through the restricted ops_agent_readonly role
    # (statement_timeout and column grants are enforced DB-side; see the
    # role/grant Alembic migration).
    start = time.perf_counter()
    try:
        with readonly_engine.connect() as conn:
            result = conn.execute(text(final_sql))
            rows = [dict(row) for row in result.mappings().all()]
    except DBAPIError as e:
        sqlstate = _pg_sqlstate(e)
        execution_time_ms = int((time.perf_counter() - start) * 1000)
        if sqlstate == _INSUFFICIENT_PRIVILEGE:
            reason = f"database denied access while executing the query: {e.orig}"
            status = "rejected"
        elif sqlstate == _QUERY_CANCELED:
            reason = "query exceeded the 5s statement_timeout enforced by the ops_agent_readonly role"
            status = "rejected"
        else:
            reason = f"query execution failed: {e}"
            status = "error"
        layer_outcomes["layer3_db"] = {"passed": False, "reason": reason}
        audit_id = record_attempt(
            question=question,
            generated_sql=final_sql,
            stated_intent=proposed.intent,
            status=status,
            layer_outcomes=layer_outcomes,
            rejection_reason=reason,
            execution_time_ms=execution_time_ms,
            estimated_cost=estimated_cost,
        )
        return ExecutedQuery(
            response=SqlQueryResponse(
                status=status,
                sql_executed=final_sql,
                rejection_reason=reason,
                execution_time_ms=execution_time_ms,
                estimated_cost=estimated_cost,
            ),
            audit_id=audit_id,
        )

    execution_time_ms = int((time.perf_counter() - start) * 1000)
    row_count = len(rows)
    truncated = not had_explicit_limit and row_count == DEFAULT_LIMIT
    layer_outcomes["layer3_db"] = {"passed": True}
    layer_outcomes["layer4_audit"] = {"passed": True}

    audit_id = record_attempt(
        question=question,
        generated_sql=final_sql,
        stated_intent=proposed.intent,
        status="success",
        layer_outcomes=layer_outcomes,
        row_count=row_count,
        execution_time_ms=execution_time_ms,
        estimated_cost=estimated_cost,
    )

    return ExecutedQuery(
        response=SqlQueryResponse(
            status="success",
            sql_executed=final_sql,
            rows=rows,
            row_count=row_count,
            truncated=truncated,
            execution_time_ms=execution_time_ms,
            estimated_cost=estimated_cost,
        ),
        audit_id=audit_id,
    )
