import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { getEvalResults, getExperimentMetadata } from "./evals";

export const REPORT_RUN = "20260822-201944";
const ROOT = path.resolve(process.cwd(), "..", "..");
function read<T>(file: string): T {
  return JSON.parse(fs.readFileSync(path.join(ROOT, "evals", file), "utf8"));
}
type Case = { id: string; category: string; input: string };
type Observation = Pick<Case, "id" | "category"> & { passed: boolean; latency_ms: number; cost_usd: number | null; actual: { rows?: Record<string, unknown>[] } };
type Label = { case_id: string; judge_verdict?: string; human_verdict?: string; judge_response_relationship?: string; human_response_relationship?: string };

// Nearest-rank p95 keeps the convention explicit, especially for tiny samples.
export function summarizeMeasurements(rows: Pick<Observation, "latency_ms" | "cost_usd">[]) {
  const latencies = rows.map((row) => row.latency_ms).sort((a, b) => a - b);
  const costs = rows.flatMap((row) => row.cost_usd === null ? [] : [row.cost_usd]);
  const n = latencies.length;
  return {
    n,
    medianMs: n ? (latencies[Math.floor((n - 1) / 2)] + latencies[Math.floor(n / 2)]) / 2 : null,
    p95Ms: n ? latencies[Math.ceil(n * 0.95) - 1] : null,
    costN: costs.length,
    meanCost: costs.length ? costs.reduce((sum, cost) => sum + cost, 0) / costs.length : null,
  };
}

export function getPublicEvalReport() {
  const datasetBytes = fs.readFileSync(path.join(ROOT, "evals/cases.json"));
  const dataset: Case[] = JSON.parse(datasetBytes.toString());
  const saved = read<{ cases: Observation[] }>(`results/${REPORT_RUN}/results.json`);
  const results = getEvalResults();
  const experiment = getExperimentMetadata();
  const defined = new Map<string, number>();
  for (const item of dataset) defined.set(item.category, (defined.get(item.category) ?? 0) + 1);
  if (new Set(dataset.map((item) => item.id)).size !== dataset.length ||
      new Set(saved.cases.map((item) => item.id)).size !== saved.cases.length ||
      saved.cases.length !== results.overall.total ||
      saved.cases.filter((item) => item.passed).length !== results.overall.passed) {
    throw new Error("Evaluation dataset or saved totals do not reconcile");
  }
  const categories = [...defined].map(([category, count]) => {
    const rows = saved.cases.filter((item) => item.category === category);
    const passed = rows.filter((item) => item.passed).length;
    const summary = results.categories.find((item) => item.category === category);
    if (rows.length && (!summary || summary.n !== rows.length || summary.passed !== passed)) {
      throw new Error(`Saved category totals do not reconcile: ${category}`);
    }
    return { category, defined: count, scored: rows.length, passed, skipped: count - rows.length,
      ...summarizeMeasurements(rows) };
  });
  const audits = ["labels.json", "request_faithfulness_labels.json"].map((file) => {
    const labels = read<Label[]>(file);
    return { file, n: labels.length, distinct: new Set(labels.map((item) => item.case_id)).size,
      agreed: labels.filter((item) => {
        const human = item.human_verdict ?? item.human_response_relationship;
        const judge = item.judge_verdict ?? item.judge_response_relationship;
        return human !== undefined && judge !== undefined && human === judge;
      }).length };
  });
  const ablation = read<{ case_id: string; category: string; variant: string; run_index: number; semantic_pass?: boolean }[]>("ablation_raw.json");
  const regression = ["baseline", "+ bounded failure handling"].map((variant) => {
    const rows = ablation.filter((item) => item.variant === variant && ["sql", "sql_semantic"].includes(item.category));
    return { variant, n: rows.length, passed: rows.filter((item) => item.semantic_pass === true).length,
      distinct: new Set(rows.map((item) => item.case_id)).size,
      runs: new Set(rows.map((item) => item.run_index)).size };
  });
  const exampleId = "sql-semantic-01-home-refund-rate-denominator";
  const exampleCase = dataset.find((item) => item.id === exampleId);
  const exampleRows = saved.cases.find((item) => item.id === exampleId)?.actual.rows;
  const row = exampleRows?.[0];
  if (!exampleCase || !row || typeof row.total_units_sold !== "number" ||
      typeof row.approved_refund_units !== "number" || !Number.isFinite(Number(row.refund_rate_pct))) {
    throw new Error("Saved Home refund-rate example is missing its measured result");
  }
  const example = { id: exampleId, request: exampleCase.input, sold: row.total_units_sold,
    refunded: row.approved_refund_units, rate: Number(row.refund_rate_pct) };
  return { results, experiment, categories, audits, regression, example,
    datasetCount: dataset.length, categoryCount: defined.size,
    currentDatasetHash: createHash("sha256").update(datasetBytes).digest("hex").slice(0, 12),
    skipped: dataset.length - saved.cases.length };
}
