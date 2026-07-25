"""Data Analyst step of the investigation pipeline: given a plan (see
app/orchestrator/investigation_planner.py), execute each signal and produce
an evidence entry for it. Reuses run_sql_query/query_rag directly — the
same SQL-generation (Claude + layers 1-4) and retrieval (embed + cosine
search) implementations every other caller in this codebase uses, not a
second, parallel implementation of either.

Each signal is executed independently. A signal whose check errors or
comes back empty is recorded as such (status "failed"/"empty") rather than
raised or silently dropped — one signal failing must not prevent the
others from completing, since a partial evidence bundle is still useful
and a caller (eventually the Report Writer, not built yet) needs to know
exactly which signals it can and can't trust.
"""

from dataclasses import dataclass
from typing import Literal

from app.orchestrator.investigation_planner import (
    InvestigationPlan,
    InvestigationSignal,
    plan_investigation,
)
from app.query.schemas import SqlQueryResponse
from app.query.service import run_sql_query
from app.rag.schemas import RagQueryResponse
from app.rag.service import query_rag

EvidenceStatus = Literal["success", "failed", "empty"]


@dataclass
class EvidenceEntry:
    name: str
    method: Literal["sql", "rag"]
    intent: str
    status: EvidenceStatus
    # Human-readable note for a non-"success" status: the rejection/error
    # reason for a failed SQL signal, or why a RAG signal came back empty.
    # None when status is "success" - the result itself is the detail.
    detail: str | None = None
    sql_result: SqlQueryResponse | None = None
    rag_result: RagQueryResponse | None = None


@dataclass
class EvidenceBundle:
    plan: InvestigationPlan
    evidence: list[EvidenceEntry]


def _gather_sql_evidence(signal: InvestigationSignal) -> EvidenceEntry:
    # Broad except is deliberate: run_sql_query() itself never raises for an
    # ordinary rejected/failed query (it returns a status field - see
    # app/query/service.py), so anything that does escape here is an
    # unexpected failure (e.g. a DB connection problem). Either way, this
    # signal is unusable and must be recorded as "failed", not allowed to
    # crash the rest of the investigation.
    try:
        result = run_sql_query(signal.intent)
    except Exception as e:  # noqa: BLE001 - see comment above
        return EvidenceEntry(
            name=signal.name, method="sql", intent=signal.intent, status="failed", detail=str(e)
        )

    if result.status != "success":
        return EvidenceEntry(
            name=signal.name,
            method="sql",
            intent=signal.intent,
            status="failed",
            detail=result.rejection_reason or f"query {result.status}",
            sql_result=result,
        )

    return EvidenceEntry(
        name=signal.name, method="sql", intent=signal.intent, status="success", sql_result=result
    )


def _gather_rag_evidence(signal: InvestigationSignal) -> EvidenceEntry:
    try:
        result = query_rag(signal.intent)
    except Exception as e:  # noqa: BLE001 - same reasoning as _gather_sql_evidence
        return EvidenceEntry(
            name=signal.name, method="rag", intent=signal.intent, status="failed", detail=str(e)
        )

    if not result.chunks:
        return EvidenceEntry(
            name=signal.name,
            method="rag",
            intent=signal.intent,
            status="empty",
            detail="No matching policy/notes chunks were retrieved for this intent.",
            rag_result=result,
        )

    return EvidenceEntry(
        name=signal.name, method="rag", intent=signal.intent, status="success", rag_result=result
    )


def gather_evidence(plan: InvestigationPlan) -> list[EvidenceEntry]:
    evidence: list[EvidenceEntry] = []
    for signal in plan.signals:
        if signal.method == "sql":
            evidence.append(_gather_sql_evidence(signal))
        elif signal.method == "rag":
            evidence.append(_gather_rag_evidence(signal))
        else:
            # Structurally shouldn't happen - Method is a Literal["sql", "rag"]
            # - but the plan came from an LLM tool call, not a type checker;
            # an unrecognized method must fail this one entry, not the loop.
            evidence.append(
                EvidenceEntry(
                    name=signal.name,
                    method=signal.method,
                    intent=signal.intent,
                    status="failed",
                    detail=f"Unknown signal method '{signal.method}'.",
                )
            )
    return evidence


def investigate_gather_evidence(question: str) -> EvidenceBundle:
    """Planner + Data Analyst, wired together, for testing this pipeline in
    isolation. No Report Writer, no endpoint - see
    app/orchestrator/investigation_planner.py's module docstring."""
    plan = plan_investigation(question)
    evidence = gather_evidence(plan)
    return EvidenceBundle(plan=plan, evidence=evidence)
