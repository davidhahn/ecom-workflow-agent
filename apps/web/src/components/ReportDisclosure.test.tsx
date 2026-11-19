import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ReportDisclosure } from "./ReportDisclosure";
import { Markdown } from "./Markdown";

afterEach(() => window.history.replaceState(null, "", "/"));

describe("Report deep links", () => {
  it("opens the containing report on a direct link to a finding", () => {
    window.history.replaceState(null, "", "#findings-finding-2-sql-calculation-errors");
    render(
      <ReportDisclosure id="findings">
        <summary>Findings</summary>
        <Markdown headingPrefix="findings" content={"## Finding 2: SQL calculation errors\n\nEvidence"} />
      </ReportDisclosure>
    );
    expect(document.getElementById("findings")).toHaveAttribute("open");
    expect(screen.getByRole("heading", { name: "Finding 2: SQL calculation errors" })).toHaveAttribute(
      "id", "findings-finding-2-sql-calculation-errors"
    );
  });

  it("opens a report when the hash changes after the page has loaded", () => {
    render(<ReportDisclosure id="primary_results"><summary>Comparison</summary>Evidence</ReportDisclosure>);
    expect(document.getElementById("primary_results")).not.toHaveAttribute("open");
    act(() => {
      window.history.replaceState(null, "", "#primary_results");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(document.getElementById("primary_results")).toHaveAttribute("open");
  });
});
