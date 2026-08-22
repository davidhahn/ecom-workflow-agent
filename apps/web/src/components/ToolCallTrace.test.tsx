import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ToolCallEntry } from "@/lib/api";
import { ToolCallTrace } from "@/components/ToolCallTrace";

const call: ToolCallEntry = { tool_name: "run_sql_query", input: {}, output: {}, latency_ms: 60, sequence: 0 };

describe("ToolCallTrace", () => {
  it("shows the three-way breakdown when llmLatencyMs is a real measurement", () => {
    render(<ToolCallTrace toolCalls={[call]} totalLatencyMs={1000} llmLatencyMs={800} />);

    expect(screen.getByText(/800 ms/)).toBeInTheDocument();
    expect(screen.getByText(/Claude API calls/)).toBeInTheDocument();
    expect(screen.getByText(/140 ms/)).toBeInTheDocument();
  });

  it("treats llmLatencyMs of 0 as a real measurement, not a missing one", () => {
    render(<ToolCallTrace toolCalls={[call]} totalLatencyMs={100} llmLatencyMs={0} />);

    expect(screen.getByText(/Claude API calls/)).toBeInTheDocument();
    expect(screen.queryByText(/Remaining \(LLM thinking/)).not.toBeInTheDocument();
  });

  it("falls back to the old two-way split when llmLatencyMs is missing", () => {
    render(<ToolCallTrace toolCalls={[call]} totalLatencyMs={1000} />);

    expect(screen.getByText(/Remaining \(LLM thinking \/ orchestration\)/)).toBeInTheDocument();
    expect(screen.queryByText(/Claude API calls/)).not.toBeInTheDocument();
  });

  it("shows nothing but the empty state when there are no tool calls", () => {
    render(<ToolCallTrace toolCalls={[]} totalLatencyMs={500} llmLatencyMs={480} />);

    expect(screen.getByText("No tool calls made for this request.")).toBeInTheDocument();
    expect(screen.queryByText(/Claude API calls/)).not.toBeInTheDocument();
  });
});
