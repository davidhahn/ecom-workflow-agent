import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RoleProvider } from "@/lib/role-context";
import { getPublicEvalReport } from "@/lib/public-eval-report";
import GuidedDemoPage from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, analyzeQuestion: vi.fn(), evaluateRefund: vi.fn() };
});
import { analyzeQuestion, evaluateRefund } from "@/lib/api";

beforeEach(() => {
  window.history.replaceState(null, "", "/guided-demo");
  vi.clearAllMocks();
});

function renderGuide() {
  return render(<RoleProvider><GuidedDemoPage /></RoleProvider>);
}

function goTo(id: string) {
  act(() => {
    window.history.pushState(null, "", `/guided-demo#${id}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

describe("Guided demo", () => {
  it("switches steps without the link's native scroll navigation", () => {
    renderGuide();
    for (const name of ["2. Policy lookup", "Next: Refund decision →", "← Back: Policy lookup"]) {
      const event = new MouseEvent("click", { bubbles: true, cancelable: true });
      fireEvent(screen.getByRole("link", { name }), event);
      expect(event.defaultPrevented).toBe(true);
    }
    expect(window.location.hash).toBe("#policy");
    expect(screen.getByRole("heading", { name: "Find the rule before making a decision" })).toBeVisible();
  });

  it("starts with a sourced data result and does not require live API calls", () => {
    renderGuide();
    const report = getPublicEvalReport();
    expect(screen.getByRole("heading", { name: "Start with a question about the orders" })).toBeVisible();
    expect(screen.getByText(report.example.request)).toBeVisible();
    expect(screen.getByText(/2 approved refunded units \/ 24 units sold = 8.33%/)).toBeVisible();
    expect(screen.getByText(/not a live Ask result/)).toBeVisible();
    expect(analyzeQuestion).not.toHaveBeenCalled();
    expect(evaluateRefund).not.toHaveBeenCalled();
    expect(screen.getByRole("link", { name: "Next: Policy lookup →" })).toHaveAttribute("href", "#policy");
  });

  it("supports every step, direct links, and finishing with the evaluation scope", () => {
    renderGuide();
    for (const [id, title] of [
      ["policy", "Find the rule before making a decision"],
      ["refund", "Apply the policy to a customer’s request"],
      ["boundary", "Don’t guess which customer is asking"],
      ["evidence", "Check the demo against more than one example"],
    ]) {
      goTo(id);
      expect(screen.getByRole("heading", { name: title })).toBeVisible();
      expect(screen.queryByRole("heading", { name: "Start with a question about the orders" })).not.toBeInTheDocument();
      expect(document.getElementById(id)).toHaveFocus();
    }
    expect(screen.getByText("60/62 tests passed")).toBeVisible();
    expect(screen.getByText(/79 dataset cases · 13 categories · 17 not run · 2 failures/)).toBeVisible();
    expect(screen.getByRole("link", { name: "Try your own question →" })).toHaveAttribute("href", "/ask");
    expect(screen.queryByRole("link", { name: /Next:/ })).not.toBeInTheDocument();
  });

  it("keeps an optional fresh result and trace link when moving back to its step", async () => {
    vi.mocked(evaluateRefund).mockResolvedValue({
      data: { request_log_id: "guide-live", status: "approved", rule_applied: 4,
        reasoning: "Fresh eligibility result.", extracted_fields: { reason: "damaged_shipping" } },
      rateLimit: { limit: 10, remaining: 9 },
    });
    renderGuide();
    goTo("refund");
    fireEvent.click(screen.getByRole("button", { name: "Run it fresh" }));
    await waitFor(() => expect(screen.getByText("Fresh eligibility result.")).toBeVisible());
    const traceLink = screen.getByRole("link", { name: "View execution trace (new tab)" });
    expect(traceLink).toHaveAttribute("href", "/activity/guide-live");
    expect(traceLink).toHaveAttribute("target", "_blank");
    goTo("boundary");
    goTo("refund");
    expect(screen.getByText("Fresh eligibility result.")).toBeVisible();
    expect(evaluateRefund).toHaveBeenCalledTimes(1);
  });

  it("uses the first step for an unknown fragment", () => {
    renderGuide();
    goTo("unknown");
    expect(screen.getByRole("heading", { name: "Start with a question about the orders" })).toBeVisible();
  });
});
