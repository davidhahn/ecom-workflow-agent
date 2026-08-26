// Pure derivations for the Execution Trace page. RequestLogDetailRow.output
// is untyped JSON with a shape that varies by request_type, so everything
// here reads it defensively. Labels only claim what the backend recorded.
// Which SQL safety layer rejected a query lives in query_audit_log, not in
// anything this file can reach, so that label stays general.

import type { BadgeTone } from "@/components/Badge";
import type { RequestLogDetailRow, ToolCallEntry } from "@/lib/api";

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

// Best-effort "what did this request end in" label, generic across every
// request_type, including ones the current UI never links to (sql, rag,
// ticket_*, invoice_*), reachable only by a direct /activity/[id] URL.
export function deriveConcreteStatus(detail: RequestLogDetailRow): string {
  const out = asRecord(detail.output);
  if (!out) return detail.request_type;

  // refund_evaluate and sql both return a literal `status` string already
  // shaped for display (approved/denied/.../could_not_process, or
  // success/rejected/error). Reuse it verbatim, don't reformat it.
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

// received -> routed -> tools -> checks -> final only applies to analyze's
// tool-call loop. Every other request type collapses to received -> final,
// since the backend never records intermediate phases for them. Labels read
// as plain sentence fragments, so a first-time reader doesn't need "checks"
// or "routed" explained.
export function deriveWorkflowPhases(detail: RequestLogDetailRow): WorkflowPhase[] {
  const out = asRecord(detail.output);
  const phases: WorkflowPhase[] = [{ label: "Request received", state: "done" }];

  if (detail.request_type !== "analyze" || !out) {
    phases.push({ label: `Result: ${deriveConcreteStatus(detail)}`, state: "done" });
    return phases;
  }

  const sqlUsed = out.sql_used === true;
  const ragUsed = out.rag_used === true;
  const routedLabel =
    sqlUsed && ragUsed
      ? "Claude routed to SQL + policy lookup"
      : sqlUsed
        ? "Claude routed to SQL lookup"
        : ragUsed
          ? "Claude routed to policy lookup"
          : "Claude answered directly";
  phases.push({ label: routedLabel, state: "done" });

  const toolCalls = detail.tool_calls ?? [];
  phases.push({
    label: toolCalls.length > 0 ? "Tool ran" : "No tool needed",
    state: toolCalls.length > 0 ? "done" : "skipped",
  });

  const incomplete = out.incomplete === true;
  phases.push({
    label: incomplete ? "Guardrail checks skipped" : "Guardrail checks ran",
    state: incomplete ? "skipped" : "done",
  });

  phases.push({ label: `Result: ${deriveConcreteStatus(detail)}`, state: "done" });
  return phases;
}

export type ReliabilityOutcome = { label: string; tone: BadgeTone };

// Answers "did this request succeed cleanly, succeed after recovery, refuse
// intentionally, or fail?" using only retry_count plus the concrete status
// already derived above.
export function deriveReliabilityOutcome(detail: RequestLogDetailRow): ReliabilityOutcome {
  const status = deriveConcreteStatus(detail);
  if (status === "could_not_process") return { label: "Refused: could not process", tone: "neutral" };
  if (status === "rejected") return { label: "Refused: validation rejected", tone: "neutral" };
  if (status === "incomplete") return { label: "Incomplete", tone: "warning" };
  if (status === "error") return { label: "Failed", tone: "danger" };
  const retried = (detail.retry_count ?? 0) > 0;
  return retried
    ? { label: "Succeeded after recovery", tone: "warning" }
    : { label: "Succeeded cleanly", tone: "success" };
}

export type GuardrailField = { label: string; caption: string; value: string; tone: BadgeTone };

// Only returns fields that apply to this specific request, never a fixed
// set padded out empty. caption states what the check verifies, so a
// reader doesn't need to ask what "Groundedness" means.
export function deriveGuardrails(detail: RequestLogDetailRow): GuardrailField[] {
  const out = asRecord(detail.output);
  if (!out) return [];
  const fields: GuardrailField[] = [];

  if (out.error === "permission_denied") {
    fields.push({
      label: "Permission",
      caption: "Code checks the requesting role against the tool's required permission before the model ever runs.",
      value: `Denied: role lacks '${String(out.required_permission ?? "?")}' permission`,
      tone: "danger",
    });
    return fields;
  }

  if (detail.request_type === "analyze" && out.incomplete !== true) {
    fields.push({
      label: "Groundedness",
      caption: "Checks that every policy rule the answer cites was retrieved for this request.",
      value: out.grounded ? "Grounded" : "Ungrounded claim detected",
      tone: out.grounded ? "success" : "danger",
    });
    if (out.topic_coverage_warning === true) {
      fields.push({
        label: "Topic coverage",
        caption: "Checks whether the answer states something about data this request never looked up.",
        value: "May reference unavailable data",
        tone: "warning",
      });
    }
  }

  if (detail.request_type === "refund_evaluate") {
    if (out.status === "could_not_process") {
      fields.push({
        label: "Refusal reason",
        caption: "The deterministic refund rule engine refuses to guess when it can't confidently resolve who's asking.",
        value: String(out.reasoning ?? ""),
        tone: "neutral",
      });
    } else if (out.status === "requires_manager_approval") {
      fields.push({
        label: "Approval required",
        caption: "The refund rule engine routes anything above its dollar threshold to a manager, no exceptions.",
        value: `Manager approval: rule ${String(out.rule_applied ?? "?")}`,
        tone: "warning",
      });
    } else if (out.status === "flagged_for_review") {
      fields.push({
        label: "Flagged for review",
        caption: "The refund rule engine flagged this pattern for manual review. It didn't decide on its own.",
        value: `rule ${String(out.rule_applied ?? "?")}`,
        tone: "warning",
      });
    }
  }

  if (detail.request_type === "sql" && out.status === "rejected") {
    // Which of the 4 safety layers rejected it lives in query_audit_log's
    // layer_outcomes, not in this response. See the module comment above.
    fields.push({
      label: "SQL validation",
      caption: "The deterministic SQL safety layer rejected this query before it ever reached the database.",
      value: String(out.rejection_reason ?? "rejected"),
      tone: "danger",
    });
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
  // {message: ...} shape when nothing cleared the relevance threshold.
  // Returns [], not null, so the caller's "no chunks retrieved" empty
  // state still renders for this call.
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

export type LatencyBreakdown = {
  totalMs: number;
  // null only for rows logged before llm_latency_ms existed. 0 is a real
  // measurement too: a cache hit made zero calls this time.
  llmMs: number | null;
  toolMs: number;
  otherMs: number | null;
};

// Splits total latency into where it went. The old version lumped
// everything but tool time into one bucket, which quietly swallowed the
// LLM call itself, often nearly the whole number on a slow request.
export function deriveLatencyBreakdown(detail: RequestLogDetailRow): LatencyBreakdown {
  const toolMs = (detail.tool_calls ?? []).reduce((sum, call) => sum + call.latency_ms, 0);
  if (detail.llm_latency_ms == null) {
    return { totalMs: detail.latency_ms, llmMs: null, toolMs, otherMs: null };
  }
  const otherMs = Math.max(0, detail.latency_ms - detail.llm_latency_ms - toolMs);
  return { totalMs: detail.latency_ms, llmMs: detail.llm_latency_ms, toolMs, otherMs };
}
