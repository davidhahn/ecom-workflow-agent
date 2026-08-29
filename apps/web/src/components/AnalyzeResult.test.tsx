import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AnalyzeResponse } from "@/lib/api";
import { AnalyzeResult } from "@/components/AnalyzeResult";

function baseResult(overrides: Partial<AnalyzeResponse>): AnalyzeResponse {
  return {
    request_log_id: "11111111-1111-1111-1111-111111111111",
    answer: "The Electronics category has the highest refund rate.",
    sql_used: true,
    rag_used: false,
    grounded: true,
    ungrounded_claims: [],
    sources: [],
    incomplete: false,
    cached: false,
    topic_coverage_warning: false,
    ...overrides,
  };
}

describe("AnalyzeResult", () => {
  it("shows a trace link after a completed request, pointing at that request's own trace", () => {
    render(<AnalyzeResult result={baseResult({ request_log_id: "abc-123" })} />);

    const link = screen.getByRole("link", { name: "View execution trace" });
    expect(link).toHaveAttribute("href", "/activity/abc-123");
  });

  it("renders the answer and reflects which tool paths ran", () => {
    render(<AnalyzeResult result={baseResult({ sql_used: true, rag_used: false })} />);

    expect(screen.getByText(/highest refund rate/i)).toBeInTheDocument();
    expect(screen.getByText("SQL used")).toBeInTheDocument();
    expect(screen.getByText("Policy lookup not used")).toBeInTheDocument();
  });

  it("flags an ungrounded answer instead of presenting it as trustworthy", () => {
    render(
      <AnalyzeResult
        result={baseResult({ grounded: false, ungrounded_claims: ["rule 15"] })}
      />
    );

    expect(screen.getByText("Ungrounded claims detected")).toBeInTheDocument();
    expect(screen.getByText(/unverified claim/i)).toBeInTheDocument();
    expect(screen.getByText("rule 15")).toBeInTheDocument();
  });

  it("hides the trace link when traceHref is explicitly null, for a captured snapshot", () => {
    render(<AnalyzeResult result={baseResult({})} traceHref={null} />);

    expect(screen.queryByRole("link", { name: "View execution trace" })).not.toBeInTheDocument();
  });

  it("uses a supplied traceHref instead of the result's own request_log_id", () => {
    render(<AnalyzeResult result={baseResult({ request_log_id: "abc-123" })} traceHref="/somewhere/else" />);

    expect(screen.getByRole("link", { name: "View execution trace" })).toHaveAttribute(
      "href",
      "/somewhere/else"
    );
  });

  it("renders an incomplete request as a distinct warning, not a normal answer with badges", () => {
    render(
      <AnalyzeResult
        result={baseResult({ incomplete: true, answer: "This request could not be completed: timed out." })}
      />
    );

    expect(screen.getByText(/unable to complete this request/i)).toBeInTheDocument();
    expect(screen.getByText(/timed out/)).toBeInTheDocument();
    // The badge row and trace link only belong to the normal-answer path.
    expect(screen.queryByRole("link", { name: "View execution trace" })).not.toBeInTheDocument();
    expect(screen.queryByText("SQL used")).not.toBeInTheDocument();
  });
});
