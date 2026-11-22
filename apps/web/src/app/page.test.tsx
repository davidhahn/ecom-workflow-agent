import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { getEvalResults } from "@/lib/evals";
import { SCENARIOS } from "@/lib/scenarios";
import { getScenarioSnapshot } from "@/lib/snapshots";
import HomePage from "./page";

describe("Landing page", () => {
  it("introduces the use case and a recorded request before the engineering details", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { level: 1, name: "An AI assistant for e-commerce operations" })).toBeInTheDocument();
    const intro = screen.getByRole("region", { name: "An AI assistant for e-commerce operations" });
    const scenario = SCENARIOS.find((item) => item.id === "refund-approval")!;
    const snapshot = getScenarioSnapshot(scenario);
    expect(within(intro).getByText(`“${scenario.input}”`)).toBeInTheDocument();
    expect("status" in snapshot && within(intro).getByText(snapshot.status)).toBeInTheDocument();
    expect(within(intro).getByText(/it doesn’t issue refunds/)).toBeInTheDocument();
    expect(within(intro).getByText(/doesn’t inspect the photos/)).toBeInTheDocument();
    expect(within(intro).getByText(/sample data, not a live result/)).toBeInTheDocument();
    expect(within(intro).getByRole("link", { name: /start the guided demo/i })).toHaveAttribute("href", "/guided-demo");
    expect(within(intro).getByRole("link", { name: /see results & evidence/i })).toHaveAttribute("href", "/evaluation-lab");
  });

  it("uses the saved evaluation totals with the historical measurement scope", () => {
    render(<HomePage />);
    const results = getEvalResults();
    expect(screen.getByText(`Saved evaluation run: ${results.overall.passed}/${results.overall.total} tests passed (${results.overall.pass_rate.toFixed(1)}%)`)).toBeInTheDocument();
    expect(screen.getByText(/not the current deployment/)).toBeInTheDocument();
    expect(screen.getByText(/specific damaged-shipment query remained unresolved/)).toBeInTheDocument();
    expect(screen.getByText(/a later Ask check exposed a separate prompt/)).toBeInTheDocument();
  });

  it("keeps routes to the demo, investigations, traces, architecture, and source", () => {
    render(<HomePage />);
    const hrefs = screen.getAllByRole("link").map((link) => link.getAttribute("href"));
    for (const href of [
      "/guided-demo", "/scenarios#refund-approval", "/scenarios#injection-attempt", "/evaluation-lab",
      "/evaluation-lab#coverage", "/evaluation-lab#findings-finding-2-sql-calculation-errors",
      "/evaluation-lab#findings-finding-5-differences-in-the-deployed-environment",
      "/ask", "/activity", "/architecture", "https://github.com/davidhahn/ecom-workflow-agent",
    ]) expect(hrefs).toContain(href);
  });
});
