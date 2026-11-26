import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { getSqlInvestigation } from "@/lib/sql-investigation";
import { getPublicEvalReport } from "@/lib/public-eval-report";
import HomePage from "./page";

describe("Landing page", () => {
  it("identifies the users and introduces a sourced failure before technical details", () => {
    render(<HomePage />);
    const intro = screen.getByRole("region", { name: "An AI assistant for e-commerce operations" });
    const example = getSqlInvestigation().examples[0];
    expect(within(intro).getByText(/For support and operations teams/)).toBeInTheDocument();
    expect(within(intro).getByText(`“${example.request}”`)).toBeInTheDocument();
    expect(within(intro).getByText(`${example.beforeRate.toFixed(2)}%`)).toBeInTheDocument();
    expect(within(intro).getByText(`${example.afterRate.toFixed(2)}%`)).toBeInTheDocument();
    expect(within(intro).getByText("10 refund records / 20 order lines")).toBeInTheDocument();
    expect(within(intro).getByText("10 approved refunded units / 23 units sold")).toBeInTheDocument();
    expect(within(intro).getByText(/it doesn’t issue refunds/)).toBeInTheDocument();
    expect(within(intro).getByText(/not a live Ask result/)).toBeInTheDocument();
    expect(within(intro).getByRole("link", { name: /start the guided demo/i })).toHaveAttribute("href", "/guided-demo");
    expect(within(intro).getByRole("link", { name: "Read the SQL investigation →" })).toHaveAttribute("href", "/evaluation-lab#sql-investigation");
  });

  it("connects ownership and diagnosis to evidence with explicit scope limits", () => {
    render(<HomePage />);
    const { regression } = getPublicEvalReport();
    expect(screen.getByText(`${regression[0].passed}/${regression[0].n} → ${regression[1].passed}/${regression[1].n} correct SQL outcomes`)).toBeInTheDocument();
    expect(screen.getByText(/Several settings changed/)).toHaveTextContent("not proof of the current deployed Ask workflow");
    expect(screen.getByText(/I scoped the web app and API/)).toBeInTheDocument();
    expect(screen.getByText(/Ask used a separate prompt/)).toBeInTheDocument();
    expect(screen.getByText(/policy query remained unresolved/)).toBeInTheDocument();
    expect(screen.getByText(/I haven’t measured customer adoption or business savings/)).toBeInTheDocument();
    const sections = screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent);
    expect(sections).toEqual([
      "One question exposed a wrong calculation", "What I built and where I drew the boundary",
      "How I traced the wrong answer", "What the evidence supports", "Inspect the work",
    ]);
  });

  it("keeps the demo, complete investigation, evaluation report, and implementation accessible", () => {
    render(<HomePage />);
    const hrefs = screen.getAllByRole("link").map((link) => link.getAttribute("href"));
    for (const href of [
      "/guided-demo", "/scenarios#injection-attempt", "/evaluation-lab",
      "/evaluation-lab#sql-investigation", "/evaluation-lab#findings-finding-5-differences-in-the-deployed-environment",
      "/ask", "/activity", "/architecture", "https://github.com/davidhahn/ecom-workflow-agent",
    ]) expect(hrefs).toContain(href);
  });
});
