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
    input: "Which category has the highest refund rate?",
    output: {},
    latency_ms: 120,
    input_tokens: null,
    output_tokens: null,
    estimated_cost_usd: null,
    grounded: null,
    cached: false,
    sql_query_audit_id: null,
    rag_chunks_retrieved: null,
    retry_count: null,
    llm_latency_ms: null,
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
      baseRow({ id: "abc-123", request_type: "sql", input: "Which category has the highest refund rate?" }),
      baseRow({ id: "def-456", request_type: "analyze", input: "What is the return policy?" }),
      baseRow({ id: "ghi-789", request_type: "refund_evaluate", input: "Can I return my headphones?" }),
    ]);

    renderActivityPage();

    const table = await screen.findByRole("table");
    const links = within(table).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "Which category has the highest refund rate?",
      "What is the return policy?",
      "Can I return my headphones?",
    ]);
    const firstCell = links[0].closest("td")!;
    expect(firstCell.querySelector("time")).toHaveAttribute("datetime", "2026-08-22T20:19:00Z");
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
