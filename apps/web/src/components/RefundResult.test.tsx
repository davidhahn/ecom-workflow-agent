import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RefundEvaluateResponse } from "@/lib/api";
import { RefundResult } from "@/components/RefundResult";

function baseResult(overrides: Partial<RefundEvaluateResponse>): RefundEvaluateResponse {
  return {
    request_log_id: "22222222-2222-2222-2222-222222222222",
    status: "approved",
    rule_applied: 4,
    reasoning: "Damaged in shipping, within window, evidence attached.",
    extracted_fields: { product_identifier: "Ceramic Coffee Mug", customer_identifier: "James O'Brien" },
    ...overrides,
  };
}

describe("RefundResult", () => {
  it("shows a trace link after a completed request, pointing at that request's own trace", () => {
    render(<RefundResult result={baseResult({ request_log_id: "xyz-789" })} />);

    const link = screen.getByRole("link", { name: "View execution trace" });
    expect(link).toHaveAttribute("href", "/activity/xyz-789");
  });

  it("renders an approval with its rule and extracted fields", () => {
    render(<RefundResult result={baseResult({})} />);

    expect(screen.getByText("approved")).toBeInTheDocument();
    expect(screen.getByText("rule 4")).toBeInTheDocument();
    expect(screen.getByText(/damaged in shipping/i)).toBeInTheDocument();
    expect(screen.getByText("Ceramic Coffee Mug")).toBeInTheDocument();
  });

  it("hides the trace link when traceHref is explicitly null, for a captured snapshot", () => {
    render(<RefundResult result={baseResult({})} traceHref={null} />);

    expect(screen.queryByRole("link", { name: "View execution trace" })).not.toBeInTheDocument();
  });

  it("displays a refusal (could_not_process) result correctly", () => {
    render(
      <RefundResult
        result={baseResult({
          status: "could_not_process",
          rule_applied: null,
          reasoning: "Could not identify which customer is making this request.",
          extracted_fields: { product_identifier: "wireless headphones", customer_identifier: null },
        })}
      />
    );

    expect(screen.getByText("could_not_process")).toBeInTheDocument();
    // No rule number applies to a refusal. Nothing gets invented in its place.
    expect(screen.queryByText(/^rule /)).not.toBeInTheDocument();
    expect(screen.getByText(/could not identify which customer/i)).toBeInTheDocument();
    // A null extracted field renders as an explicit placeholder, not "null"
    // or a blank cell that reads as missing data.
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("omits the extracted-fields section entirely when there are no fields", () => {
    render(<RefundResult result={baseResult({ extracted_fields: {} })} />);

    expect(screen.queryByText("Extracted fields")).not.toBeInTheDocument();
  });
});
