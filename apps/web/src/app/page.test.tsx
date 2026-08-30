import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { getEvalResults } from "@/lib/evals";
import HomePage from "./page";

describe("Landing page", () => {
  it("renders the hero heading and value prop", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", { name: /an ops agent that shows its work/i, level: 1 })
    ).toBeInTheDocument();
  });

  it("shows the real overall pass rate from the committed results.json, not a typed-in number", () => {
    const results = getEvalResults();
    render(<HomePage />);

    expect(
      screen.getByText(new RegExp(`${results.overall.passed}/${results.overall.total}`))
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        new RegExp(`eval cases pass \\(${results.overall.pass_rate.toFixed(1).replace(".", "\\.")}%\\)`)
      )
    ).toBeInTheDocument();
  });

  it("renders the tabbed snapshot, defaulting to the injection-attempt scenario", () => {
    render(<HomePage />);

    expect(screen.getByText(/captured from a real run/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Injection attempt", pressed: true })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /run this scenario live/i })).toHaveAttribute(
      "href",
      "/scenarios#injection-attempt"
    );
  });

  it("switches the snapshot and its live link when another tab is clicked", () => {
    render(<HomePage />);

    fireEvent.click(screen.getByRole("button", { name: "Data analysis" }));

    expect(screen.getByRole("button", { name: "Data analysis", pressed: true })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /run this scenario live/i })).toHaveAttribute(
      "href",
      "/scenarios#data-analysis"
    );
  });

  it("renders both finding cards linking into the Evaluation Lab's findings report", () => {
    render(<HomePage />);

    const findingLinks = screen
      .getAllByRole("link")
      .filter((link) => link.getAttribute("href") === "/evaluation-lab#findings");
    expect(findingLinks).toHaveLength(2);
  });

  it("renders a highlight stat card for each curated category with real numbers from results.json", () => {
    const results = getEvalResults();
    render(<HomePage />);

    for (const name of ["sql_semantic", "rag", "refund_evaluator", "permission"]) {
      const category = results.categories.find((c) => c.category === name)!;
      expect(screen.getByText(name)).toBeInTheDocument();
      expect(screen.getAllByText(`${category.passed}/${category.n}`).length).toBeGreaterThan(0);
    }
  });

  it("links into every other page in the site", () => {
    render(<HomePage />);

    for (const href of ["/scenarios", "/ask", "/activity", "/evaluation-lab", "/architecture"]) {
      expect(screen.getAllByRole("link").some((link) => link.getAttribute("href") === href)).toBe(
        true
      );
    }
  });

  it("renders an explore card for every destination page", () => {
    render(<HomePage />);

    for (const name of ["Scenarios", "Ask", "Activity", "Evaluation Lab", "Architecture"]) {
      expect(screen.getByRole("heading", { name, level: 3 })).toBeInTheDocument();
    }
  });
});
