import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RoleProvider } from "@/lib/role-context";
import AskPage from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    analyzeQuestion: vi.fn(),
  };
});

import { analyzeQuestion } from "@/lib/api";

const EXAMPLE_QUESTIONS = [
  "Which products have the highest refund rate?",
  "What's our policy on damaged shipments?",
  "We've had a lot of refund requests for the Bluetooth Headphones Pro, what's driving that, and does it violate our policy?",
  "Are any shipments delayed right now?",
];

function renderAskPage() {
  return render(
    <RoleProvider>
      <AskPage />
    </RoleProvider>
  );
}

describe("Ask page example questions", () => {
  it.each(EXAMPLE_QUESTIONS)("clicking %s populates the textarea with that exact text", (example) => {
    renderAskPage();

    fireEvent.click(screen.getByRole("button", { name: example }));

    expect(screen.getByPlaceholderText(/refund rate for Electronics/i)).toHaveValue(example);
  });

  it("does not submit the form (analyzeQuestion is never called) when an example is clicked", () => {
    renderAskPage();

    fireEvent.click(screen.getByRole("button", { name: EXAMPLE_QUESTIONS[0] }));

    expect(analyzeQuestion).not.toHaveBeenCalled();
  });

  it("renders all four example chips", () => {
    renderAskPage();

    for (const example of EXAMPLE_QUESTIONS) {
      expect(screen.getByRole("button", { name: example })).toBeInTheDocument();
    }
  });
});
