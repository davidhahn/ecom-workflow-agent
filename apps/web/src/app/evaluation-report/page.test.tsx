import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EvaluationReportPage from "./page";

describe("Public evaluation report", () => {
  it("shows historical scope, unrun categories, and the next missing measurement", () => {
    render(<EvaluationReportPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("How I check whether the agent gives the right answer");
    expect(screen.getByText("60/62 tests passed (96.8%)")).toBeInTheDocument();
    expect(screen.getAllByText("Not run")).toHaveLength(3);
    expect(screen.getByText(/These results come from the August 22 local run/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What I need to measure next" })).toBeInTheDocument();
    const investigation = screen.getByRole("heading", { name: "A query can run successfully and still give the wrong number" });
    const coverage = screen.getByRole("heading", { name: "What passed, what failed, and what didn’t run" });
    expect(investigation.compareDocumentPosition(coverage) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole("link", { name: "Per-case timing and cost records" })).toHaveAttribute("href", expect.stringContaining("20260822-201944/results.json"));
    expect(screen.getByText(/These times include the test runner/)).toHaveTextContent("excludes grading calls");
  });
});
