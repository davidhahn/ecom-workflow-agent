import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { getEvalResults, getExperimentMetadata } from "@/lib/evals";
import EvaluationLabPage from "./page";

describe("Evaluation Lab page", () => {
  it("shows the real overall pass rate from the committed results.json, not a typed-in number", () => {
    const results = getEvalResults();
    render(<EvaluationLabPage />);

    // The headline splits the fraction and its caption across two spans.
    expect(
      screen.getByText(new RegExp(`${results.overall.passed}/${results.overall.total}`))
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        new RegExp(`cases passed \\(${results.overall.pass_rate.toFixed(1).replace(".", "\\.")}%\\)`)
      )
    ).toBeInTheDocument();
  });

  it("shows the real environment metadata from the committed experiment.json", () => {
    const experiment = getExperimentMetadata();
    render(<EvaluationLabPage />);

    expect(screen.getAllByText(experiment.application_model).length).toBeGreaterThan(0);
    expect(screen.getAllByText(experiment.git_commit).length).toBeGreaterThan(0);
  });

  it("renders a row per category from results.json", () => {
    const results = getEvalResults();
    render(<EvaluationLabPage />);

    for (const category of results.categories) {
      // Short category names like "sql" or "rag" also appear inside the
      // rendered report prose below the table, so more than one match is
      // expected — this only confirms the table row exists, not uniqueness.
      expect(screen.getAllByText(category.category).length).toBeGreaterThan(0);
    }
  });

  it("renders all six committed eval reports", () => {
    render(<EvaluationLabPage />);

    // Each report's own H1, from the markdown itself. Titles like "Findings"
    // can also appear on the collapsed summary row, so match all and require
    // at least one.
    for (const heading of [
      "Frozen Final Evaluation Suite",
      "Primary Results",
      "Experiment History",
      "Measurement Context",
      "Findings",
      "Methodology Notes",
    ]) {
      expect(screen.getAllByText(heading).length).toBeGreaterThan(0);
    }
  });
});
