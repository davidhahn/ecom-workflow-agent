import { describe, expect, it } from "vitest";
import { getSqlInvestigation } from "./sql-investigation";

describe("SQL investigation evidence", () => {
  it("reads the real query captures and distinguishes the two calculation errors", () => {
    const evidence = getSqlInvestigation();
    const [electronics, home] = evidence.examples;
    expect(electronics.beforeRate).toBe(50);
    expect(electronics.afterRate).toBe(43.48);
    expect(electronics.before.generated_sql).toContain("COUNT(DISTINCT oi.id)");
    expect(electronics.before.structural_pass).toBe(true);
    expect(electronics.before.semantic_pass).toBe(false);
    expect(electronics.after.sql_executed).toContain("SUM(oi.quantity)");
    expect(electronics.after.sql_executed).toContain("r.status = 'approved'");
    expect(electronics.derivation).toContain("none are denied or pending");
    expect(home.beforeRate).toBe(13.04);
    expect(home.afterRate).toBe(8.33);
    expect(evidence).toMatchObject({ calibrationCount: 21, structuralPassed: 21, correct: 14, wrong: 6, unscored: 1 });
  });
});
