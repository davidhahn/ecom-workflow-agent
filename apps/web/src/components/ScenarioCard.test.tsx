import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RoleProvider } from "@/lib/role-context";
import type { Scenario } from "@/lib/scenarios";
import { ScenarioCard } from "@/components/ScenarioCard";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, analyzeQuestion: vi.fn(), evaluateRefund: vi.fn() };
});

import { analyzeQuestion, evaluateRefund, RateLimitedError } from "@/lib/api";

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

function renderCard(scenario: Scenario) {
  return render(
    <RoleProvider>
      <ScenarioCard scenario={scenario} />
    </RoleProvider>
  );
}

describe("ScenarioCard", () => {
  it("renders the scenario's name, business context, and expected behavior up front", () => {
    renderCard(analyzeScenario);

    expect(screen.getByRole("heading", { name: analyzeScenario.name })).toBeInTheDocument();
    expect(screen.getByText(analyzeScenario.businessContext)).toBeInTheDocument();
    expect(screen.getByText(analyzeScenario.expectedBehavior)).toBeInTheDocument();
    // No result yet — nothing claiming an outcome before the scenario runs.
    expect(screen.queryByRole("link", { name: "View execution trace" })).not.toBeInTheDocument();
  });

  it("running an analyze scenario calls the right endpoint with its exact input and renders the result", async () => {
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
    fireEvent.click(screen.getByRole("button", { name: "Run scenario" }));

    expect(analyzeQuestion).toHaveBeenCalledWith(analyzeScenario.input, "read_only_viewer");
    await waitFor(() => expect(screen.getByText(/highest refund rate/i)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "View execution trace" })).toHaveAttribute(
      "href",
      "/activity/trace-1"
    );
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
    fireEvent.click(screen.getByRole("button", { name: "Run scenario" }));

    expect(evaluateRefund).toHaveBeenCalledWith(refundScenario.input, "read_only_viewer");
    await waitFor(() => expect(screen.getByText("could_not_process")).toBeInTheDocument());
    expect(screen.getByText(/could not identify which customer/i)).toBeInTheDocument();
  });

  it("shows an understandable message, not a raw error, when the request is rate limited", async () => {
    vi.mocked(evaluateRefund).mockRejectedValue(new RateLimitedError("Rate limit exceeded.", 30));

    renderCard(refundScenario);
    fireEvent.click(screen.getByRole("button", { name: "Run scenario" }));

    await waitFor(() => expect(screen.getByText(/try again in 30 seconds/i)).toBeInTheDocument());
  });

  it("shows the request's error message when the call fails for a non-rate-limit reason", async () => {
    vi.mocked(analyzeQuestion).mockRejectedValue(new Error("/query/analyze failed (500): boom"));

    renderCard(analyzeScenario);
    fireEvent.click(screen.getByRole("button", { name: "Run scenario" }));

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
    fireEvent.click(screen.getByRole("button", { name: "Run scenario" }));

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
