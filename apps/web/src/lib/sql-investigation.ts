import fs from "node:fs";
import path from "node:path";

export const SQL_CALIBRATION_SOURCE = "sql_semantic_calibration_v1_raw.json";
export const SQL_FIXED_SOURCE = "results/20260822-201944/results.json";
const ROOT = path.resolve(process.cwd(), "..", "..", "evals");
type Calibration = {
  case_id: string; run_index: number; generated_sql: string; rows: Record<string, unknown>[];
  structural_pass: boolean; semantic_pass: boolean | null; status: string;
};
type Saved = {
  id: string; expected: { expected_result: { derivation: string } };
  actual: { sql_executed: string; rows: Record<string, unknown>[]; prompt_version: string };
};

export function getSqlInvestigation() {
  const calibration: Calibration[] = JSON.parse(fs.readFileSync(path.join(ROOT, SQL_CALIBRATION_SOURCE), "utf8"));
  const saved: { cases: Saved[] } = JSON.parse(fs.readFileSync(path.join(ROOT, SQL_FIXED_SOURCE), "utf8"));
  const cases: { id: string; input: string }[] = JSON.parse(fs.readFileSync(path.join(ROOT, "cases.json"), "utf8"));
  const examples = ["sql-01-refund-rate-by-category", "sql-semantic-01-home-refund-rate-denominator"].map((id) => {
    const before = calibration.find((item) => item.case_id === id && item.run_index === 1);
    const after = saved.cases.find((item) => item.id === id);
    const request = cases.find((item) => item.id === id)?.input;
    if (!request || !before?.generated_sql || !before.rows?.length || !after?.actual.sql_executed || !after.actual.rows?.length) {
      throw new Error(`Missing saved SQL investigation evidence: ${id}`);
    }
    const beforeRate = Number(before.rows[0].refund_rate_pct ?? before.rows[0].refund_rate_percent);
    const afterRate = Number(after.actual.rows[0].refund_rate_pct);
    if (!Number.isFinite(beforeRate) || !Number.isFinite(afterRate)) throw new Error(`Missing recorded rate: ${id}`);
    return { id, request, before, after: after.actual, derivation: after.expected.expected_result.derivation, beforeRate, afterRate };
  });
  return {
    examples,
    calibrationCount: calibration.length,
    structuralPassed: calibration.filter((row) => row.structural_pass === true).length,
    correct: calibration.filter((row) => row.semantic_pass === true).length,
    wrong: calibration.filter((row) => row.semantic_pass === false).length,
    unscored: calibration.filter((row) => row.semantic_pass === null).length,
  };
}
