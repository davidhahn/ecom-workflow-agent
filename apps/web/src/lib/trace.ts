// Pure derivations for the Execution Trace page. Everything here reads only
// fields the backend actually returns (RequestLogDetailRow.output is
// untyped JSON — apps/api/app/db/observability_models.py stores it as
// JSONB, and its shape varies by request_type). Nothing here invents a
// workflow phase or status the backend doesn't record; where the data can't
// support something precisely (e.g. which of the 4 SQL safety layers
// rejected a query — apps/api/app/query/validation.py's layer_outcomes dict
// is written to query_audit_log, not to any response the frontend can
// reach), the label says so in general terms rather than guessing.

import type { BadgeTone } from "@/components/Badge";
import type { RequestLogDetailRow, ToolCallEntry } from "@/lib/api";

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

// Best-effort "what did this request end in" label, generic across every
// request_type — including ones the current UI never links to (sql, rag,
// ticket_*, invoice_*), reachable only by a direct /activity/[id] URL.
export function deriveConcreteStatus(detail: RequestLogDetailRow): string {
  const out = asRecord(detail.output);
  if (!out) return detail.request_type;

  // refund_evaluate and sql both return a literal `status` string already
  // shaped for display (approved/denied/.../could_not_process, or
  // success/rejected/error) — reuse it verbatim rather than reformatting.
  if (typeof out.status === "string") return out.status;

  if (detail.request_type === "analyze") {
    if (out.incomplete === true) return "incomplete";
    return out.grounded === false ? "answered (ungrounded flagged)" : "answered";
  }

  if (detail.request_type === "rag") {
    const chunks = Array.isArray(out.chunks) ? out.chunks : [];
    return chunks.length > 0 ? "chunks retrieved" : "no relevant chunks";
  }

  if (typeof out.error === "string") return "error";
  return "completed";
}

export type WorkflowPhase = { label: string; state: "done" | "skipped" };

// received -> routed -> tools -> checks -> final only applies where analyze's
// tool-call loop actually produces those phases. Every other request type
// collapses to received -> final — a simpler representation, not a guess at
// phases the backend never recorded (see module comment above).
export function deriveWorkflowPhases(detail: RequestLogDetailRow): WorkflowPhase[] {
  const out = asRecord(detail.output);
  const phases: WorkflowPhase[] = [{ label: "received", state: "done" }];

  if (detail.request_type !== "analyze" || !out) {
    phases.push({ label: `final: ${deriveConcreteStatus(detail)}`, state: "done" });
    return phases;
  }

  const sqlUsed = out.sql_used === true;
  const ragUsed = out.rag_used === true;
  const routedLabel =
    sqlUsed && ragUsed ? "routed: SQL + policy" : sqlUsed ? "routed: SQL" : ragUsed ? "routed: policy" : "routed: direct answer";
  phases.push({ label: routedLabel, state: "done" });

  const toolCalls = detail.tool_calls ?? [];
  phases.push({ label: "tools", state: toolCalls.length > 0 ? "done" : "skipped" });

  const incomplete = out.incomplete === true;
  phases.push({ label: "checks", state: incomplete ? "skipped" : "done" });

  phases.push({ label: `final: ${deriveConcreteStatus(detail)}`, state: "done" });
  return phases;
}

export type ReliabilityOutcome = { label: string; tone: BadgeTone };

// Answers "did this request succeed cleanly, succeed after recovery, refuse
// intentionally, or fail?" using only retry_count plus the concrete status
// already derived above.
export function deriveReliabilityOutcome(detail: RequestLogDetailRow): ReliabilityOutcome {
  const status = deriveConcreteStatus(detail);
  if (status === "could_not_process") return { label: "Refused — could not process", tone: "neutral" };
  if (status === "rejected") return { label: "Refused — validation rejected", tone: "neutral" };
  if (status === "incomplete") return { label: "Incomplete", tone: "warning" };
  if (status === "error") return { label: "Failed", tone: "danger" };
  const retried = (detail.retry_count ?? 0) > 0;
  return retried
    ? { label: "Succeeded after recovery", tone: "warning" }
    : { label: "Succeeded cleanly", tone: "success" };
}

export type GuardrailField = { label: string; value: string; tone: BadgeTone };

// Only ever returns fields that actually apply to this specific request —
// never a fixed set of badges padded out empty.
export function deriveGuardrails(detail: RequestLogDetailRow): GuardrailField[] {
  const out = asRecord(detail.output);
  if (!out) return [];
  const fields: GuardrailField[] = [];

  if (out.error === "permission_denied") {
    fields.push({
      label: "Permission",
      value: `Denied — role lacks '${String(out.required_permission ?? "?")}' permission`,
      tone: "danger",
    });
    return fields;
  }

  if (detail.request_type === "analyze" && out.incomplete !== true) {
    fields.push({
      label: "Groundedness",
      value: out.grounded ? "Grounded" : "Ungrounded claim detected",
      tone: out.grounded ? "success" : "danger",
    });
    if (out.topic_coverage_warning === true) {
      fields.push({ label: "Topic coverage", value: "May reference unavailable data", tone: "warning" });
    }
  }

  if (detail.request_type === "refund_evaluate") {
    if (out.status === "could_not_process") {
      fields.push({ label: "Refusal reason", value: String(out.reasoning ?? ""), tone: "neutral" });
    } else if (out.status === "requires_manager_approval") {
      fields.push({
        label: "Approval required",
        value: `Manager approval — rule ${String(out.rule_applied ?? "?")}`,
        tone: "warning",
      });
    } else if (out.status === "flagged_for_review") {
      fields.push({ label: "Flagged for review", value: `rule ${String(out.rule_applied ?? "?")}`, tone: "warning" });
    }
  }

  if (detail.request_type === "sql" && out.status === "rejected") {
    // Which of the 4 safety layers rejected it lives in query_audit_log's
    // layer_outcomes, not in this response — see module comment.
    fields.push({ label: "SQL validation", value: String(out.rejection_reason ?? "rejected"), tone: "danger" });
  }

  return fields;
}

export type SqlToolSummary = {
  sql: string | null;
  status: string | null;
  rejectionReason: string | null;
  promptVersion: string | null;
};

export function sqlToolSummary(call: ToolCallEntry): SqlToolSummary | null {
  if (call.tool_name !== "run_sql_query") return null;
  const out = asRecord(call.output);
  if (!out) return null;
  return {
    sql: typeof out.sql_executed === "string" ? out.sql_executed : null,
    status: typeof out.status === "string" ? out.status : null,
    rejectionReason: typeof out.rejection_reason === "string" ? out.rejection_reason : null,
    promptVersion: typeof out.prompt_version === "string" ? out.prompt_version : null,
  };
}

export type RagChunkSummary = { ruleNumber: number | null; sourceDoc: string; similarity: number | null };

export function ragToolSummary(call: ToolCallEntry): RagChunkSummary[] | null {
  if (call.tool_name !== "search_policy") return null;
  // {message: ...} shape when nothing cleared the relevance threshold — []
  // (not null) so the caller's "no chunks retrieved" empty state still
  // renders for this call, rather than silently rendering nothing at all.
  if (!Array.isArray(call.output)) return [];
  return call.output.map((chunk) => {
    const c = asRecord(chunk) ?? {};
    return {
      ruleNumber: typeof c.rule_number === "number" ? c.rule_number : null,
      sourceDoc: typeof c.source_doc === "string" ? c.source_doc : "",
      similarity: typeof c.similarity === "number" ? c.similarity : null,
    };
  });
}
