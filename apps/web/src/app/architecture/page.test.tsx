import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ArchitecturePage from "./page";

describe("Architecture page", () => {
  it("renders the diagram", () => {
    render(<ArchitecturePage />);

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "/architecture-diagram.svg");
  });

  it("renders the responsibility split table", () => {
    render(<ArchitecturePage />);

    expect(screen.getByText("LLM proposes / interprets")).toBeInTheDocument();
    expect(screen.getByText("Deterministic systems enforce")).toBeInTheDocument();
    expect(screen.getByText("tool selection")).toBeInTheDocument();
  });

  it("renders all six deliberately-not-built entries", () => {
    render(<ArchitecturePage />);

    expect(screen.getByText("Multi-agent decomposition")).toBeInTheDocument();
    expect(screen.getByText("A workflow framework (LangGraph or similar)")).toBeInTheDocument();
    expect(screen.getByText("A vector database migration, or a reranker")).toBeInTheDocument();
    expect(screen.getByText("Production OAuth or a full identity system")).toBeInTheDocument();
    expect(screen.getByText("A second agentic investigation workflow")).toBeInTheDocument();
    expect(screen.getByText("More UI surface")).toBeInTheDocument();
  });

  it("links all five decisions to the real, public DECISIONS.md", () => {
    render(<ArchitecturePage />);

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(5);
    for (const link of links) {
      expect(link).toHaveAttribute(
        "href",
        "https://github.com/davidhahn/ecom-workflow-agent/blob/main/DECISIONS.md"
      );
    }
  });
});
