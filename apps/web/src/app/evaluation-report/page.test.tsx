import { expect, it, vi } from "vitest";
import { permanentRedirect } from "next/navigation";
import EvaluationReportPage from "./page";

vi.mock("next/navigation", () => ({ permanentRedirect: vi.fn(() => { throw new Error("redirect"); }) }));

it("keeps one canonical page for the former public report", () => {
  expect(() => EvaluationReportPage()).toThrow("redirect");
  expect(permanentRedirect).toHaveBeenCalledWith("/evaluation-lab");
});
