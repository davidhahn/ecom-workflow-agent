import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RoleProvider } from "@/lib/role-context";
import type { RequestLogRow } from "@/lib/api";
import ActivityPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, listRequestLogs: vi.fn() };
});

import { listRequestLogs } from "@/lib/api";

function baseRow(overrides: Partial<RequestLogRow>): RequestLogRow {
  return {
    id: "row-1",
    request_type: "sql",
    latency_ms: 120,
    input_tokens: null,
    output_tokens: null,
    estimated_cost_usd: null,
    grounded: null,
    cached: false,
    created_at: "2026-08-22T20:19:00Z",
    ...overrides,
  };
}

function renderActivityPage() {
  return render(
    <RoleProvider>
      <ActivityPage />
    </RoleProvider>
  );
}

describe("Activity page", () => {
  it("links every row to that request's execution trace", async () => {
    vi.mocked(listRequestLogs).mockResolvedValue([
      baseRow({ id: "abc-123", request_type: "sql" }),
      baseRow({ id: "def-456", request_type: "analyze" }),
      baseRow({ id: "ghi-789", request_type: "refund_evaluate" }),
    ]);

    renderActivityPage();

    const table = await screen.findByRole("table");
    const links = within(table).getAllByRole("link");
    expect(links.map((l) => l.getAttribute("href"))).toEqual([
      "/activity/abc-123",
      "/activity/def-456",
      "/activity/ghi-789",
    ]);
  });

  it("shows the empty state when nothing is logged", async () => {
    vi.mocked(listRequestLogs).mockResolvedValue([]);

    renderActivityPage();

    expect(await screen.findByText("No requests logged yet.")).toBeInTheDocument();
  });
});
