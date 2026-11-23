import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EvaluationLabPage from "./page";

describe("Combined results and evidence page", () => {
  it("introduces the project and a concrete request before results and failure details", () => {
    render(<EvaluationLabPage />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText(/I built this assistant to answer questions/)).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "One request, from question to result" })).getByText("What is the refund rate for Home category products?")).toBeInTheDocument();
    expect(screen.getByText("2 approved refunded units / 24 units sold = 8.33%")).toBeInTheDocument();
    const example = screen.getByRole("heading", { name: "One request, from question to result" });
    const coverage = screen.getByRole("heading", { name: "What passed, what failed, and what didn’t run" });
    const failure = screen.getByRole("heading", { name: "The query ran successfully. The refund rate was wrong." });
    expect(example.compareDocumentPosition(coverage) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(coverage.compareDocumentPosition(failure) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText(/not a live Ask response/)).toBeInTheDocument();
  });

  it("provides a directly linked investigation with the recorded SQL and its measurement limits", () => {
    render(<EvaluationLabPage />);
    const investigation = document.getElementById("sql-investigation")!;
    expect(investigation).toHaveTextContent("Before: 50.00%");
    expect(investigation).toHaveTextContent("After: 43.48%");
    expect(investigation).toHaveTextContent("10 refund records / 20 order lines");
    expect(investigation).toHaveTextContent("10 approved refunded units / 23 units sold");
    expect(investigation).toHaveTextContent("Several settings changed");
    const queries = within(investigation).getByText("See the actual queries, returned rows, and independent checks");
    expect(queries.closest("details")).not.toHaveAttribute("open");
    fireEvent.click(queries);
    expect(queries.closest("details")).toHaveAttribute("open");
    expect(within(investigation).getAllByText(/COUNT\(DISTINCT r.id\)/).length).toBeGreaterThan(0);
    expect(within(investigation).getAllByRole("link", { name: "Open the saved query and result" })).toHaveLength(4);
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
