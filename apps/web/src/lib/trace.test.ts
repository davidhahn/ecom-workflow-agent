import { describe, expect, it } from "vitest";
import type { RequestLogDetailRow, ToolCallEntry } from "@/lib/api";
import {
  deriveConcreteStatus,
  deriveGuardrails,
  deriveLatencyBreakdown,
  deriveReliabilityOutcome,
  deriveWorkflowPhases,
  ragToolSummary,
  sqlToolSummary,
} from "@/lib/trace";

// Minimal valid row; each test overrides only what it's exercising, so a
// bad default can't silently make an unrelated assertion pass.
function detail(overrides: Partial<RequestLogDetailRow>): RequestLogDetailRow {
  return {
    id: "00000000-0000-0000-0000-000000000000",
    request_type: "analyze",
    input: "test question",
    output: {},
    latency_ms: 100,
    input_tokens: null,
    output_tokens: null,
    estimated_cost_usd: null,
    grounded: null,
    sql_query_audit_id: null,
    rag_chunks_retrieved: null,
    cached: false,
    retry_count: null,
    llm_latency_ms: null,
    created_at: "2026-08-19T00:00:00Z",
    tool_calls: null,
    ...overrides,
  };
}

describe("deriveConcreteStatus", () => {
  it("reads refund_evaluate's status field verbatim", () => {
    expect(deriveConcreteStatus(detail({ request_type: "refund_evaluate", output: { status: "approved" } }))).toBe(
      "approved"
    );
  });

  it("reads sql's status field verbatim", () => {
    expect(deriveConcreteStatus(detail({ request_type: "sql", output: { status: "rejected" } }))).toBe("rejected");
  });

  it("flags an incomplete analyze request before checking groundedness", () => {
    expect(deriveConcreteStatus(detail({ request_type: "analyze", output: { incomplete: true } }))).toBe(
      "incomplete"
    );
  });

  it("flags an ungrounded analyze answer", () => {
    expect(deriveConcreteStatus(detail({ request_type: "analyze", output: { grounded: false } }))).toBe(
      "answered (ungrounded flagged)"
    );
  });

  it("reports a grounded analyze answer as answered", () => {
    expect(deriveConcreteStatus(detail({ request_type: "analyze", output: { grounded: true } }))).toBe("answered");
  });

  it("distinguishes rag retrieval hits from misses", () => {
    expect(deriveConcreteStatus(detail({ request_type: "rag", output: { chunks: [{}] } }))).toBe("chunks retrieved");
    expect(deriveConcreteStatus(detail({ request_type: "rag", output: { chunks: [] } }))).toBe("no relevant chunks");
  });

  it("falls back to a generic error/completed label for other request types", () => {
    expect(deriveConcreteStatus(detail({ request_type: "ticket_draft", output: { error: "boom" } }))).toBe("error");
    expect(deriveConcreteStatus(detail({ request_type: "ticket_draft", output: {} }))).toBe("completed");
  });

  it("does not throw when output is null and falls back to request_type", () => {
    expect(deriveConcreteStatus(detail({ request_type: "invoice_draft", output: null }))).toBe("invoice_draft");
  });
});

describe("deriveWorkflowPhases", () => {
  it("builds the full analyze ribbon when tools ran and checks completed", () => {
    const phases = deriveWorkflowPhases(
      detail({
        request_type: "analyze",
        output: { sql_used: true, rag_used: true, incomplete: false },
        tool_calls: [{ tool_name: "run_sql_query", input: {}, output: {}, latency_ms: 1, sequence: 0 }],
      })
    );
    expect(phases.map((p) => p.label)).toEqual([
      "Request received",
      "Claude routed to SQL + policy lookup",
      "Tool ran",
      "Guardrail checks ran",
      "Result: answered",
    ]);
    expect(phases.every((p) => p.state === "done")).toBe(true);
  });

  it("marks tools skipped when no tool call ran", () => {
    const phases = deriveWorkflowPhases(
      detail({ request_type: "analyze", output: { sql_used: false, rag_used: false }, tool_calls: [] })
    );
    expect(phases.find((p) => p.label === "No tool needed")?.state).toBe("skipped");
    expect(phases.find((p) => p.label === "Claude answered directly")).toBeTruthy();
  });

  it("marks tools skipped when tool_calls is null, not just empty", () => {
    const phases = deriveWorkflowPhases(detail({ request_type: "analyze", output: {}, tool_calls: null }));
    expect(phases.find((p) => p.label === "No tool needed")?.state).toBe("skipped");
  });

  it("marks checks skipped when the request never reached groundedness evaluation", () => {
    const phases = deriveWorkflowPhases(detail({ request_type: "analyze", output: { incomplete: true } }));
    expect(phases.find((p) => p.label === "Guardrail checks skipped")?.state).toBe("skipped");
  });

  it("collapses to received -> final for non-analyze request types", () => {
    const phases = deriveWorkflowPhases(detail({ request_type: "refund_evaluate", output: { status: "denied" } }));
    expect(phases.map((p) => p.label)).toEqual(["Request received", "Result: denied"]);
  });

  it("collapses to received -> final when analyze output is missing entirely", () => {
    const phases = deriveWorkflowPhases(detail({ request_type: "analyze", output: null }));
    expect(phases.map((p) => p.label)).toEqual(["Request received", "Result: analyze"]);
  });
});

describe("deriveReliabilityOutcome", () => {
  it("labels a refund refusal as refused, not failed", () => {
    expect(
      deriveReliabilityOutcome(detail({ request_type: "refund_evaluate", output: { status: "could_not_process" } }))
    ).toEqual({ label: "Refused: could not process", tone: "secondary" });
  });

  it("labels a rejected SQL query as refused", () => {
    expect(deriveReliabilityOutcome(detail({ request_type: "sql", output: { status: "rejected" } }))).toEqual({
      label: "Refused: validation rejected",
      tone: "secondary",
    });
  });

  it("labels an incomplete analyze loop as incomplete, not failed", () => {
    expect(
      deriveReliabilityOutcome(detail({ request_type: "analyze", output: { incomplete: true } }))
    ).toEqual({ label: "Incomplete", tone: "warning" });
  });

  it("labels a generic error as failed", () => {
    expect(deriveReliabilityOutcome(detail({ request_type: "ticket_draft", output: { error: "boom" } }))).toEqual({
      label: "Failed",
      tone: "danger",
    });
  });

  it("distinguishes a clean success from one that needed a retry", () => {
    expect(
      deriveReliabilityOutcome(
        detail({ request_type: "refund_evaluate", output: { status: "approved" }, retry_count: 0 })
      )
    ).toEqual({ label: "Succeeded cleanly", tone: "success" });

    expect(
      deriveReliabilityOutcome(
        detail({ request_type: "refund_evaluate", output: { status: "approved" }, retry_count: 2 })
      )
    ).toEqual({ label: "Succeeded after recovery", tone: "warning" });
  });

  it("treats a null retry_count as no retry", () => {
    expect(
      deriveReliabilityOutcome(
        detail({ request_type: "refund_evaluate", output: { status: "approved" }, retry_count: null })
      ).label
    ).toBe("Succeeded cleanly");
  });
});

describe("deriveGuardrails", () => {
  it("returns nothing when output is missing", () => {
    expect(deriveGuardrails(detail({ output: null }))).toEqual([]);
  });

  it("short-circuits on a permission denial and reports nothing else", () => {
    const fields = deriveGuardrails(
      detail({
        request_type: "analyze",
        output: { error: "permission_denied", required_permission: "write", grounded: false },
      })
    );
    expect(fields).toEqual([
      {
        label: "Permission",
        caption: "Code checks the requesting role against the tool's required permission before the model ever runs.",
        value: "Denied: role lacks 'write' permission",
        tone: "danger",
      },
    ]);
  });

  it("reports groundedness and topic coverage for a completed analyze request", () => {
    const fields = deriveGuardrails(
      detail({
        request_type: "analyze",
        output: { incomplete: false, grounded: false, topic_coverage_warning: true },
      })
    );
    expect(fields).toEqual([
      {
        label: "Groundedness",
        caption: "Checks that every policy rule the answer cites was retrieved for this request.",
        value: "Ungrounded claim detected",
        tone: "danger",
      },
      {
        label: "Topic coverage",
        caption: "Checks whether the answer states something about data this request never looked up.",
        value: "May reference unavailable data",
        tone: "warning",
      },
    ]);
  });

  it("omits groundedness entirely for an incomplete analyze request", () => {
    expect(deriveGuardrails(detail({ request_type: "analyze", output: { incomplete: true } }))).toEqual([]);
  });

  it("surfaces the refusal reason for a could_not_process refund", () => {
    const fields = deriveGuardrails(
      detail({
        request_type: "refund_evaluate",
        output: { status: "could_not_process", reasoning: "no customer identified" },
      })
    );
    expect(fields).toEqual([
      {
        label: "Refusal reason",
        caption: "The deterministic refund rule engine refuses to guess when it can't confidently resolve who's asking.",
        value: "no customer identified",
        tone: "secondary",
      },
    ]);
  });

  it("surfaces the approval requirement for requires_manager_approval", () => {
    const fields = deriveGuardrails(
      detail({ request_type: "refund_evaluate", output: { status: "requires_manager_approval", rule_applied: 6 } })
    );
    expect(fields).toEqual([
      {
        label: "Approval required",
        caption: "The refund rule engine routes anything above its dollar threshold to a manager, no exceptions.",
        value: "Manager approval: rule 6",
        tone: "warning",
      },
    ]);
  });

  it("reports nothing extra for a clean refund approval", () => {
    expect(
      deriveGuardrails(detail({ request_type: "refund_evaluate", output: { status: "approved", rule_applied: 4 } }))
    ).toEqual([]);
  });

  it("surfaces the SQL validation outcome on rejection only", () => {
    expect(
      deriveGuardrails(detail({ request_type: "sql", output: { status: "rejected", rejection_reason: "blocked table" } }))
    ).toEqual([
      {
        label: "SQL validation",
        caption: "The deterministic SQL safety layer rejected this query before it ever reached the database.",
        value: "blocked table",
        tone: "danger",
      },
    ]);
    expect(deriveGuardrails(detail({ request_type: "sql", output: { status: "success" } }))).toEqual([]);
  });
});

describe("deriveLatencyBreakdown", () => {
  it("splits total latency into LLM, tool, and other time when llm_latency_ms is captured", () => {
    const breakdown = deriveLatencyBreakdown(
      detail({
        latency_ms: 1000,
        llm_latency_ms: 800,
        tool_calls: [{ tool_name: "run_sql_query", input: {}, output: {}, latency_ms: 150, sequence: 0 }],
      })
    );
    expect(breakdown).toEqual({ totalMs: 1000, llmMs: 800, toolMs: 150, otherMs: 50 });
  });

  it("treats llm_latency_ms of 0 as a real measurement, not a missing one", () => {
    const breakdown = deriveLatencyBreakdown(detail({ latency_ms: 5, llm_latency_ms: 0, tool_calls: [] }));
    expect(breakdown).toEqual({ totalMs: 5, llmMs: 0, toolMs: 0, otherMs: 5 });
  });

  it("returns null llmMs/otherMs for a row logged before this column existed", () => {
    const breakdown = deriveLatencyBreakdown(
      detail({
        latency_ms: 1000,
        llm_latency_ms: null,
        tool_calls: [{ tool_name: "run_sql_query", input: {}, output: {}, latency_ms: 150, sequence: 0 }],
      })
    );
    expect(breakdown).toEqual({ totalMs: 1000, llmMs: null, toolMs: 150, otherMs: null });
  });

  it("never returns a negative otherMs from rounding overlap", () => {
    const breakdown = deriveLatencyBreakdown(detail({ latency_ms: 100, llm_latency_ms: 90, tool_calls: [
      { tool_name: "run_sql_query", input: {}, output: {}, latency_ms: 40, sequence: 0 },
    ] }));
    expect(breakdown.otherMs).toBe(0);
  });
});

function toolCall(overrides: Partial<ToolCallEntry>): ToolCallEntry {
  return { tool_name: "run_sql_query", input: {}, output: {}, latency_ms: 1, sequence: 0, ...overrides };
}

describe("sqlToolSummary", () => {
  it("extracts the generated SQL and validation outcome", () => {
    expect(
      sqlToolSummary(
        toolCall({ output: { sql_executed: "SELECT 1", status: "success", prompt_version: "v3" } })
      )
    ).toEqual({ sql: "SELECT 1", status: "success", rejectionReason: null, promptVersion: "v3" });
  });

  it("returns null for a non-SQL tool call", () => {
    expect(sqlToolSummary(toolCall({ tool_name: "search_policy" }))).toBeNull();
  });

  it("does not throw on a malformed output and returns null instead", () => {
    expect(sqlToolSummary(toolCall({ output: "not an object" }))).toBeNull();
  });
});

describe("ragToolSummary", () => {
  it("extracts rule numbers and similarity scores from retrieved chunks", () => {
    expect(
      ragToolSummary(
        toolCall({
          tool_name: "search_policy",
          output: [{ content: "...", source_doc: "refund_policy.md", rule_number: 4, similarity: 0.83 }],
        })
      )
    ).toEqual([{ ruleNumber: 4, sourceDoc: "refund_policy.md", similarity: 0.83 }]);
  });

  it("returns an empty array (not null) when nothing cleared the relevance threshold", () => {
    // Real shape from apps/api/app/rag/service.py when nothing matches:
    // {message: "..."}, an object, not an array. This must stay
    // distinguishable from "not a RAG call at all" (null).
    expect(ragToolSummary(toolCall({ tool_name: "search_policy", output: { message: "no relevant evidence" } }))).toEqual(
      []
    );
  });

  it("returns null for a non-RAG tool call", () => {
    expect(ragToolSummary(toolCall({ tool_name: "run_sql_query" }))).toBeNull();
  });
});
