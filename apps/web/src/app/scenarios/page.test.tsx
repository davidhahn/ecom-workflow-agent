import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RoleProvider } from "@/lib/role-context";
import { SCENARIOS } from "@/lib/scenarios";
import ScenariosPage from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    analyzeQuestion: vi.fn(),
    evaluateRefund: vi.fn(),
  };
});

import { analyzeQuestion, evaluateRefund } from "@/lib/api";

function renderScenariosPage() {
  return render(
    <RoleProvider>
      <ScenariosPage />
    </RoleProvider>
  );
}

function selectScenario(id: string) {
  act(() => {
    window.history.replaceState(null, "", `#${id}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("Scenarios page", () => {
  it("opens the linked scenario and responds to browser hash navigation", () => {
    window.history.replaceState(null, "", "#injection-attempt");
    renderScenariosPage();
    expect(screen.getByRole("heading", { name: "Injection attempt" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Data analysis" })).not.toBeInTheDocument();
    selectScenario("data-analysis");
    expect(screen.getByRole("heading", { name: "Data analysis" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Injection attempt" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "How I checked the calculations →" })).toHaveAttribute(
      "href", "/evaluation-lab#sql-investigation"
    );
  });

  it("renders the page heading", () => {
    renderScenariosPage();

    expect(screen.getByRole("heading", { name: "Scenarios" })).toBeInTheDocument();
  });

  it("renders a card for each curated scenario with its name and expected behavior", () => {
    renderScenariosPage();

    for (const scenario of SCENARIOS) {
      selectScenario(scenario.id);
      expect(screen.getByRole("heading", { name: scenario.name })).toBeInTheDocument();
      expect(screen.getByText(scenario.expectedBehavior)).toBeInTheDocument();
    }
  });

  it("renders each card's captured snapshot up front, with no trace link", () => {
    renderScenariosPage();

    expect(screen.getAllByText(/captured from a real run/i)).toHaveLength(SCENARIOS.length);
    expect(screen.queryByRole("link", { name: "View execution trace" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Run it fresh" })).toHaveLength(1);
  });

  it("running an analyze-type scenario calls analyzeQuestion with that scenario's exact input", () => {
    renderScenariosPage();
    const scenario = SCENARIOS.find((s) => s.endpoint === "analyze")!;

    selectScenario(scenario.id);
    const card = screen.getByRole("heading", { name: scenario.name }).closest(`#${scenario.id}`)!;
    fireEvent.click(within(card as HTMLElement).getByRole("button", { name: "Run it fresh" }));

    expect(analyzeQuestion).toHaveBeenCalledWith(scenario.input, "read_only_viewer");
  });

  it("running a refund-type scenario calls evaluateRefund with that scenario's exact input", () => {
    renderScenariosPage();
    const scenario = SCENARIOS.find((s) => s.endpoint === "refund")!;

    selectScenario(scenario.id);
    const card = screen.getByRole("heading", { name: scenario.name }).closest(`#${scenario.id}`)!;
    fireEvent.click(within(card as HTMLElement).getByRole("button", { name: "Run it fresh" }));

    expect(evaluateRefund).toHaveBeenCalledWith(scenario.input, "read_only_viewer");
  });

  it("renders the free-form refund box beneath the curated scenarios", () => {
    renderScenariosPage();

    expect(screen.getByRole("heading", { name: "Try your own refund request" })).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/wireless headphones/i)
    ).toBeInTheDocument();
  });
});
