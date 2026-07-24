import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RoleProvider } from "@/lib/role-context";
import RefundsPage from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    evaluateRefund: vi.fn(),
  };
});

import { evaluateRefund } from "@/lib/api";

const EXAMPLE_REQUEST =
  "Hi, this is James O'Brien. The Ceramic Coffee Mug I ordered arrived cracked because of " +
  "rough handling during shipping. I've already attached photos showing the damage - can I " +
  "get a refund?";

function renderRefundsPage() {
  return render(
    <RoleProvider>
      <RefundsPage />
    </RoleProvider>
  );
}

describe("Refunds page example request", () => {
  it("clicking the example populates the textarea with the full example request text", () => {
    renderRefundsPage();

    fireEvent.click(screen.getByRole("button", { name: /try an example/i }));

    expect(screen.getByPlaceholderText(/wireless headphones/i)).toHaveValue(EXAMPLE_REQUEST);
  });

  it("does not submit the form (evaluateRefund is never called) when the example is clicked", () => {
    renderRefundsPage();

    fireEvent.click(screen.getByRole("button", { name: /try an example/i }));

    expect(evaluateRefund).not.toHaveBeenCalled();
  });
});
