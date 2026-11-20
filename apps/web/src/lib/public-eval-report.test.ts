import { describe, expect, it } from "vitest";
import { getPublicEvalReport, summarizeMeasurements } from "./public-eval-report";

describe("Public report measurements", () => {
  it("reconciles defined, scored, skipped, and passed outcomes", () => {
    const report = getPublicEvalReport();
    expect(report.datasetCount).toBe(79);
    expect(report.example).toEqual({ id: "sql-semantic-01-home-refund-rate-denominator", request: "What is the refund rate for Home category products?", sold: 24, refunded: 2, rate: 8.33 });
    expect(report.categoryCount).toBe(13);
    expect(report.categories.reduce((sum, row) => sum + row.scored, 0)).toBe(62);
    expect(report.categories.reduce((sum, row) => sum + row.passed, 0)).toBe(60);
    expect(report.categories.reduce((sum, row) => sum + row.skipped, 0)).toBe(17);
    expect(report.categories.filter((row) => !row.scored).map((row) => row.category).sort()).toEqual(["invoice_evaluator", "ticket_evaluator"]);
    expect(report.categories.find((row) => row.category === "prompt_injection")?.skipped).toBe(3);
  });

  it("preserves missing cost observations instead of treating them as free tasks", () => {
    expect(summarizeMeasurements([
      { latency_ms: 100, cost_usd: null },
      { latency_ms: 200, cost_usd: 0.02 },
      { latency_ms: 500, cost_usd: 0 },
      { latency_ms: 300, cost_usd: null },
    ])).toEqual({ n: 4, medianMs: 250, p95Ms: 500, costN: 2, meanCost: 0.01 });
    expect(summarizeMeasurements([])).toEqual({ n: 0, medianMs: null, p95Ms: null, costN: 0, meanCost: null });
  });

  it("derives judge agreement and SQL before/after from their own source samples", () => {
    const report = getPublicEvalReport();
    expect(report.audits.map(({ n, agreed, distinct }) => ({ n, agreed, distinct }))).toEqual([
      { n: 15, agreed: 15, distinct: 15 }, { n: 18, agreed: 18, distinct: 6 },
    ]);
    expect(report.regression.map(({ n, passed, distinct, runs }) => ({ n, passed, distinct, runs }))).toEqual([
      { n: 21, passed: 14, distinct: 7, runs: 3 }, { n: 21, passed: 21, distinct: 7, runs: 3 },
    ]);
    expect(report.categories.find((row) => row.category === "rag")?.meanCost).toBeNull();
  });
});
