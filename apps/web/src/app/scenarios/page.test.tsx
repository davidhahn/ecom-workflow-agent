import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

describe("Scenarios page", () => {
  it("renders the page heading", () => {
    renderScenariosPage();

    expect(screen.getByRole("heading", { name: "Scenarios" })).toBeInTheDocument();
  });

  it("renders a card for each curated scenario with its name and expected behavior", () => {
    renderScenariosPage();

    for (const scenario of SCENARIOS) {
      expect(screen.getByRole("heading", { name: scenario.name })).toBeInTheDocument();
      expect(screen.getByText(scenario.expectedBehavior)).toBeInTheDocument();
    }
  });

  it("running an analyze-type scenario calls analyzeQuestion with that scenario's exact input", () => {
    renderScenariosPage();
    const scenario = SCENARIOS.find((s) => s.endpoint === "analyze")!;

    const card = screen.getByRole("heading", { name: scenario.name }).closest("div")!.parentElement!;
    fireEvent.click(within(card).getByRole("button", { name: "Run scenario" }));

    expect(analyzeQuestion).toHaveBeenCalledWith(scenario.input, "read_only_viewer");
  });

  it("running a refund-type scenario calls evaluateRefund with that scenario's exact input", () => {
    renderScenariosPage();
    const scenario = SCENARIOS.find((s) => s.endpoint === "refund")!;

    const card = screen.getByRole("heading", { name: scenario.name }).closest("div")!.parentElement!;
    fireEvent.click(within(card).getByRole("button", { name: "Run scenario" }));

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
