import fs from "node:fs";
import path from "node:path";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ArchitecturePage from "./page";

describe("Architecture page", () => {
  it("renders the expandable diagram", () => {
    render(<ArchitecturePage />);
    expect(screen.getByRole("img")).toHaveAttribute("src", "/architecture-diagram.svg");
  });

  it("distinguishes post-generation warnings from execution controls", () => {
    render(<ArchitecturePage />);
    const controls = screen.getByRole("table", { name: "Controls by request stage" });
    expect(within(controls).getByText("SQL execution")).toBeInTheDocument();
    const citations = within(controls).getByText("After answer generation").closest("tr")!;
    expect(citations).toHaveTextContent("do not establish that it applied a policy correctly");
    const failures = screen.getByRole("table", { name: "Failure conditions and responses" });
    expect(failures).toHaveTextContent("The generated answer remains visible");
    expect(failures).toHaveTextContent("Other model-call sites remain outside this wrapper");
  });

  it("keeps current limits available as expandable details", () => {
    render(<ArchitecturePage />);
    for (const title of ["Identity and data access", "Retrieval and answer checks", "Investigation workflow"]) {
      expect(screen.getByText(title).closest("details")).toBeInTheDocument();
    }
  });

  it("links decisions to distinct headings that exist in the decision log", () => {
    render(<ArchitecturePage />);
    const section = screen.getByRole("heading", { name: "Implementation and decisions" }).closest("section")!;
    const decisions = fs.readFileSync(path.resolve(process.cwd(), "../../DECISIONS.md"), "utf8");
    const anchors = [...decisions.matchAll(/^### (.+)$/gm)].map(([, title]) =>
      title.toLowerCase().replace(/[^\w\s-]/g, "").replace(/ /g, "-")
    );
    const links = within(section).getAllByRole("link").filter(link => link.getAttribute("href")?.includes("DECISIONS.md#"));
    expect(links).toHaveLength(4);
    for (const link of links) expect(anchors).toContain(link.getAttribute("href")!.split("#")[1]);
  });
});
