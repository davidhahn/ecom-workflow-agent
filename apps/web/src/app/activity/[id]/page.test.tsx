import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RoleProvider } from "@/lib/role-context";
import { SCENARIOS } from "@/lib/scenarios";
import type { RequestLogDetailRow } from "@/lib/api";
import ExecutionTracePage from "./page";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "test-id" }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, getRequestLog: vi.fn() };
});

import { getRequestLog } from "@/lib/api";

function baseDetail(overrides: Partial<RequestLogDetailRow>): RequestLogDetailRow {
  return {
    id: "test-id",
    request_type: "refund_evaluate",
    input: "some request text",
    output: { status: "approved" },
    latency_ms: 500,
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

function renderTracePage() {
  return render(
    <RoleProvider>
      <ExecutionTracePage />
    </RoleProvider>
  );
}

describe("Execution Trace page", () => {
  it("shows a loading state while the trace is being fetched", () => {
    vi.mocked(getRequestLog).mockReturnValue(new Promise(() => {}));

    renderTracePage();

    expect(screen.getByText(/loading trace/i)).toBeInTheDocument();
  });

  it("shows an understandable error, and still offers a way back, when the trace fails to load", async () => {
    vi.mocked(getRequestLog).mockRejectedValue(new Error("/observability/requests/test-id failed (404): not found"));

    renderTracePage();

    await waitFor(() => expect(screen.getByText(/failed \(404\): not found/)).toBeInTheDocument());
    // A bad id must never strand the viewer with no way back. The link must
    // name its own destination — "Activity" alone told a reviewer nothing.
    expect(screen.getByRole("link", { name: /back to the full request log/i })).toBeInTheDocument();
  });

  it("renders every section without throwing when optional trace fields are all missing", async () => {
    vi.mocked(getRequestLog).mockResolvedValue(
      baseDetail({
        tool_calls: null,
        rag_chunks_retrieved: null,
        retry_count: null,
        grounded: null,
        input_tokens: null,
        output_tokens: null,
        estimated_cost_usd: null,
        cached: false,
        output: { status: "approved" },
      })
    );

    renderTracePage();

    await waitFor(() => expect(screen.getByText("some request text")).toBeInTheDocument());
    expect(screen.getByText("No tool calls made for this request.")).toBeInTheDocument();
    expect(screen.getByText(/no guardrail checks apply/i)).toBeInTheDocument();
    expect(screen.getByText("no token usage")).toBeInTheDocument();
    expect(screen.getByText("not cached")).toBeInTheDocument();
    // retry_count is null, not 0 — the "N retries" line must not appear at
    // all rather than rendering a misleading "null retries".
    expect(screen.queryByText(/retr(y|ies)/)).not.toBeInTheDocument();
    // No RAG data at all for this request type — the raw-chunks section
    // must not render an empty/misleading block.
    expect(screen.queryByText(/retrieved policy chunks/i)).not.toBeInTheDocument();
  });

  it("does not claim a guardrail ran when the trace data can't support that claim", async () => {
    // sql/rag/ticket_* rows carry no grounded/topic-coverage signal at all —
    // the guardrails section must say so plainly, not show empty badges.
    vi.mocked(getRequestLog).mockResolvedValue(
      baseDetail({ request_type: "sql", output: { status: "success", sql_executed: "SELECT 1" } })
    );

    renderTracePage();

    await waitFor(() =>
      expect(screen.getByText(/no guardrail checks apply to this request type/i)).toBeInTheDocument()
    );
    expect(screen.queryByText("Groundedness")).not.toBeInTheDocument();
  });

  it("links back to the originating scenario when the request came from a curated card", async () => {
    const scenario = SCENARIOS[0];
    vi.mocked(getRequestLog).mockResolvedValue(
      baseDetail({ request_type: scenario.endpoint === "analyze" ? "analyze" : "refund_evaluate", input: scenario.input })
    );

    renderTracePage();

    await waitFor(() =>
      expect(screen.getByRole("link", { name: new RegExp(scenario.name, "i") })).toHaveAttribute(
        "href",
        `/#${scenario.id}`
      )
    );
    // Only one back-link when the origin is known — the generic "full
    // request log" link would be redundant next to a link that already
    // says exactly where this came from.
    expect(screen.queryByRole("link", { name: /back to the full request log/i })).not.toBeInTheDocument();
  });

  it("does not show a scenario back-link for a request that didn't come from a curated card", async () => {
    vi.mocked(getRequestLog).mockResolvedValue(baseDetail({ input: "some one-off free-form question" }));

    renderTracePage();

    await waitFor(() => expect(screen.getByText("some one-off free-form question")).toBeInTheDocument());
    expect(screen.queryByText(/on the scenario demo/i)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to the full request log/i })).toBeInTheDocument();
  });

  it("shows a cache banner and reuses the original trace's numbers, not empty ones, on a cached response", async () => {
    vi.mocked(getRequestLog).mockResolvedValue(
      baseDetail({
        request_type: "analyze",
        output: { sql_used: true, rag_used: false, grounded: true, incomplete: false },
        cached: true,
        latency_ms: 12329,
        llm_latency_ms: 12245,
        input_tokens: 3702,
        output_tokens: 400,
        tool_calls: [{ tool_name: "run_sql_query", input: {}, output: {}, latency_ms: 84, sequence: 0 }],
      })
    );

    renderTracePage();

    await waitFor(() => expect(screen.getByText(/served from cache/i)).toBeInTheDocument());
    // The banner explains this is the original run's data, not a fresh one.
    expect(screen.getByText(/original request that produced this answer/i)).toBeInTheDocument();
    expect(screen.queryByText("No tool calls made for this request.")).not.toBeInTheDocument();
  });

  it("breaks total latency into LLM, tool, and other time when llm_latency_ms is captured", async () => {
    vi.mocked(getRequestLog).mockResolvedValue(
      baseDetail({
        request_type: "analyze",
        output: { sql_used: true, rag_used: false, grounded: true, incomplete: false },
        latency_ms: 12329,
        llm_latency_ms: 12245,
        tool_calls: [{ tool_name: "run_sql_query", input: {}, output: {}, latency_ms: 60, sequence: 0 }],
      })
    );

    renderTracePage();

    await waitFor(() => expect(screen.getByText("12245 ms in Claude API calls")).toBeInTheDocument());
    expect(screen.getByText("60 ms in tools")).toBeInTheDocument();
    expect(screen.getByText("24 ms other (network, logging)")).toBeInTheDocument();
  });

  it("spells out input/output tokens instead of the unexplained 'in/out' shorthand", async () => {
    vi.mocked(getRequestLog).mockResolvedValue(baseDetail({ input_tokens: 1042, output_tokens: 111 }));

    renderTracePage();

    await waitFor(() => expect(screen.getByText("1042 input tokens / 111 output tokens")).toBeInTheDocument());
  });
});
