from fastapi import APIRouter, Request, Response

from app.query.schemas import SqlQueryRequest, SqlQueryResponse
from app.query.service import run_sql_query
from app.rate_limit import limiter

router = APIRouter()


@router.post("/query/sql", response_model=SqlQueryResponse)
@limiter.limit("20/hour")
def query_sql(request: Request, response: Response, body: SqlQueryRequest) -> SqlQueryResponse:
    # Known gap, intentional for this step: no row-level security or
    # multi-tenant isolation. ops_agent_readonly's column grants restrict
    # *which columns* any caller can see (e.g. no customers.email), but not
    # *which rows* — every caller of this endpoint sees the same full table
    # contents subject to that column restriction. Approval-routing / the
    # $200 threshold rule is also out of scope here; see ARCHITECTURE.md.
    return run_sql_query(body.question)
