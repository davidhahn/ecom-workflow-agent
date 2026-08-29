import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RoleProvider } from "@/lib/role-context";
import type { AnalyzeResponse, RefundEvaluateResponse } from "@/lib/api";
import type { Scenario } from "@/lib/scenarios";
import { ScenarioCard } from "@/components/ScenarioCard";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, analyzeQuestion: vi.fn(), evaluateRefund: vi.fn() };
});

// The test scenarios below use ids that don't exist in the real captured
// scenario-snapshots.json, so the snapshot lookup itself is mocked too,
// keyed on endpoint the same way the real capture is keyed on scenario id.
vi.mock("@/lib/snapshots", () => ({
  SNAPSHOT_CAPTURED_AT: "2026-08-28T00:00:00.000Z",
  getScenarioSnapshot: vi.fn(),
}));

import { analyzeQuestion, evaluateRefund, RateLimitedError } from "@/lib/api";
import { getScenarioSnapshot } from "@/lib/snapshots";

const analyzeScenario: Scenario = {
  id: "test-analyze",
  name: "Test analyze scenario",
  businessContext: "An analyst wants to know the highest-refund category.",
  expectedBehavior: "The agent should query the data and identify the highest category.",
  endpoint: "analyze",
  input: "Which category has the highest refund rate?",
};

const refundScenario: Scenario = {
  id: "test-refund",
  name: "Test refund scenario",
  businessContext: "A refund request arrives with no identifiable customer.",
  expectedBehavior: "The agent should refuse because no customer can be identified.",
  endpoint: "refund",
  input: "I want a refund for my broken headphones.",
};

const ANALYZE_SNAPSHOT: AnalyzeResponse = {
  request_log_id: "snapshot-analyze",
  answer: "Captured answer: Electronics has the highest refund rate.",
  sql_used: true,
  rag_used: false,
  grounded: true,
  ungrounded_claims: [],
  sources: [],
  incomplete: false,
  cached: false,
  topic_coverage_warning: false,
};

const REFUND_SNAPSHOT: RefundEvaluateResponse = {
  request_log_id: "snapshot-refund",
  status: "could_not_process",
  rule_applied: null,
  reasoning: "Captured reasoning: no customer identified.",
  extracted_fields: {},
};

beforeEach(() => {
  vi.mocked(getScenarioSnapshot).mockImplementation((scenario) =>
    scenario.endpoint === "analyze" ? ANALYZE_SNAPSHOT : REFUND_SNAPSHOT
  );
});

function renderCard(scenario: Scenario) {
  return render(
    <RoleProvider>
      <ScenarioCard scenario={scenario} />
    </RoleProvider>
  );
}

describe("ScenarioCard", () => {
  it("renders the scenario's name, context, and expected behavior, plus its captured snapshot, before anything is run", () => {
    renderCard(analyzeScenario);

    expect(screen.getByRole("heading", { name: analyzeScenario.name })).toBeInTheDocument();
    expect(screen.getByText(analyzeScenario.businessContext)).toBeInTheDocument();
    expect(screen.getByText(analyzeScenario.expectedBehavior)).toBeInTheDocument();
    expect(screen.getByText(/captured from a real run/i)).toBeInTheDocument();
    expect(screen.getByText(ANALYZE_SNAPSHOT.answer)).toBeInTheDocument();
    // A captured snapshot's own request_log_id may point at a row the demo
    // DB has already reset, so it never gets a trace link.
    expect(screen.queryByRole("link", { name: "View execution trace" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run it fresh" })).toBeInTheDocument();
  });

  it("running an analyze scenario calls the right endpoint with its exact input and replaces the snapshot with a live result", async () => {
    vi.mocked(analyzeQuestion).mockResolvedValue({
      data: {
        request_log_id: "trace-1",
        answer: "Electronics has the highest refund rate.",
        sql_used: true,
        rag_used: false,
        grounded: true,
        ungrounded_claims: [],
        sources: [],
        incomplete: false,
        cached: false,
        topic_coverage_warning: false,
      },
      rateLimit: { limit: 10, remaining: 9 },
    });

    renderCard(analyzeScenario);
    fireEvent.click(screen.getByRole("button", { name: "Run it fresh" }));

    expect(analyzeQuestion).toHaveBeenCalledWith(analyzeScenario.input, "read_only_viewer");
    await waitFor(() => expect(screen.getByText(/highest refund rate/i)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "View execution trace" })).toHaveAttribute(
      "href",
      "/activity/trace-1"
    );
    // The snapshot's own answer is gone, replaced by the fresh one.
    expect(screen.queryByText(ANALYZE_SNAPSHOT.answer)).not.toBeInTheDocument();
  });

  it("displays a refusal result correctly when a refund scenario is run", async () => {
    vi.mocked(evaluateRefund).mockResolvedValue({
      data: {
        request_log_id: "trace-2",
        status: "could_not_process",
        rule_applied: null,
        reasoning: "Could not identify which customer is making this request.",
        extracted_fields: { product_identifier: "wireless headphones", customer_identifier: null },
      },
      rateLimit: { limit: 15, remaining: 14 },
    });

    renderCard(refundScenario);
    fireEvent.click(screen.getByRole("button", { name: "Run it fresh" }));

    expect(evaluateRefund).toHaveBeenCalledWith(refundScenario.input, "read_only_viewer");
    await waitFor(() =>
      expect(screen.getByText(/could not identify which customer is making this request\./i)).toBeInTheDocument()
    );
  });

  it("shows an understandable message, not a raw error, when the request is rate limited", async () => {
    vi.mocked(evaluateRefund).mockRejectedValue(new RateLimitedError("Rate limit exceeded.", 30));

    renderCard(refundScenario);
    fireEvent.click(screen.getByRole("button", { name: "Run it fresh" }));

    await waitFor(() => expect(screen.getByText(/try again in 30 seconds/i)).toBeInTheDocument());
  });

  it("shows the request's error message when the call fails for a non-rate-limit reason", async () => {
    vi.mocked(analyzeQuestion).mockRejectedValue(new Error("/query/analyze failed (500): boom"));

    renderCard(analyzeScenario);
    fireEvent.click(screen.getByRole("button", { name: "Run it fresh" }));

    await waitFor(() => expect(screen.getByText(/failed \(500\): boom/)).toBeInTheDocument());
  });

  it("disables the button and shows a running state while the request is in flight", async () => {
    let resolvePromise: (value: Awaited<ReturnType<typeof analyzeQuestion>>) => void;
    vi.mocked(analyzeQuestion).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve;
      })
    );

    renderCard(analyzeScenario);
    fireEvent.click(screen.getByRole("button", { name: "Run it fresh" }));

    const button = screen.getByRole("button", { name: "Running…" });
    expect(button).toBeDisabled();

    resolvePromise!({
      data: {
        request_log_id: "trace-3",
        answer: "done",
        sql_used: false,
        rag_used: false,
        grounded: true,
        ungrounded_claims: [],
        sources: [],
        incomplete: false,
        cached: false,
        topic_coverage_warning: false,
      },
      rateLimit: { limit: null, remaining: null },
    });
    await waitFor(() => expect(screen.getByText("done")).toBeInTheDocument());
  });
});
