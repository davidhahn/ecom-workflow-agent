import fs from "node:fs";
import path from "node:path";

// apps/web is two levels under the repo root (see next.config.ts's
// turbopack.root, which locates the same place the same way).
const REPO_ROOT = path.resolve(process.cwd(), "..", "..");
const RESULTS_DIR = path.join(REPO_ROOT, "evals", "results", "20260822-201944");

export type EvalCategoryResult = {
  category: string;
  n: number;
  passed: number;
  failed: number;
  pass_rate: number;
  comparison_ready: boolean;
  what_it_tests: string;
  consequence_of_failure: string;
};

export type EvalResults = {
  timestamp: string;
  commit: string;
  categories: EvalCategoryResult[];
  overall: {
    total: number;
    passed: number;
    failed: number;
    pass_rate: number;
  };
  comparison_readiness: { threshold_n: number; note: string };
  skipped_categories: string[];
  skipped_case_ids: Record<string, string>;
};

export type ExperimentMetadata = {
  application_model: string;
  judge_model: string;
  prompt_version: Record<string, string>;
  eval_dataset_version: string;
  git_commit: string;
  cache_bypassed: boolean;
};

function readJson<T>(filePath: string): T {
  return JSON.parse(fs.readFileSync(filePath, "utf-8")) as T;
}

export function getEvalResults(): EvalResults {
  return readJson<EvalResults>(path.join(RESULTS_DIR, "results.json"));
}

export function getExperimentMetadata(): ExperimentMetadata {
  return readJson<ExperimentMetadata>(path.join(RESULTS_DIR, "experiment.json"));
}

const REPORT_FILES = [
  "frozen_suite.md",
  "primary_results.md",
  "experiment_history.md",
  "measurement_context.md",
  "findings.md",
  "methodology.md",
] as const;

export type ReportName = (typeof REPORT_FILES)[number];

export function getEvalReport(name: ReportName): string {
  return fs.readFileSync(path.join(REPO_ROOT, "evals", name), "utf-8");
}

export function getAllEvalReports(): { name: ReportName; content: string }[] {
  return REPORT_FILES.map((name) => ({ name, content: getEvalReport(name) }));
}
