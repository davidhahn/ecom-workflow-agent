import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EvaluationLabPage from "./page";

describe("Combined results and evidence page", () => {
  it("introduces the project and a concrete request before results and failure details", () => {
    render(<EvaluationLabPage />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText(/I built this assistant to answer questions/)).toBeInTheDocument();
    expect(screen.getByText("What is the refund rate for Home category products?")).toBeInTheDocument();
    expect(screen.getByText("2 approved refunded units / 24 units sold = 8.33%")).toBeInTheDocument();
    const example = screen.getByRole("heading", { name: "One request, from question to result" });
    const coverage = screen.getByRole("heading", { name: "What passed, what failed, and what didn’t run" });
    const failure = screen.getByRole("heading", { name: "A query can run successfully and still give the wrong number" });
    expect(example.compareDocumentPosition(coverage) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(coverage.compareDocumentPosition(failure) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText(/not a live Ask response/)).toBeInTheDocument();
  });

  it("keeps one total, with sample size and historical limits beside it", () => {
    render(<EvaluationLabPage />);
    expect(screen.getAllByText("60/62 tests passed (96.8%)")).toHaveLength(1);
    expect(screen.getByText(/79 cases in the dataset/)).toHaveTextContent("13 categories · 17 not run · 2 failures");
    expect(screen.getByText(/These results come from the August 22 local run/)).toBeInTheDocument();
    expect(screen.getByText(/Twelve rule checks with known inputs/)).toHaveTextContent("bypass the model");
    expect(screen.getByText(/These times include the test runner/)).toHaveTextContent("excludes grading calls");
  });

  it("keeps detailed tables and source reports expandable, including existing deep links", () => {
    render(<EvaluationLabPage />);
    const categorySummary = screen.getByText("All 13 categories and skipped coverage");
    expect(categorySummary.closest("details")).not.toHaveAttribute("open");
    expect(screen.getByText("Timing and cost by category").closest("details")).not.toHaveAttribute("open");
    for (const id of ["primary_results", "findings", "methodology", "measurement_context", "frozen_suite", "experiment_history"]) {
      expect(document.getElementById(id)).toBeInTheDocument();
    }
    expect(document.getElementById("findings-finding-2-sql-calculation-errors")).toBeInTheDocument();
    expect(document.getElementById("findings-finding-5-differences-in-the-deployed-environment")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Try a live scenario →" })).toHaveAttribute("href", "/scenarios");
  });
});
