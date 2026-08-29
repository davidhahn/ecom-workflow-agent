import { describe, expect, it } from "vitest";
import { SCENARIOS } from "@/lib/scenarios";
import { getScenarioSnapshot, SNAPSHOT_CAPTURED_AT } from "@/lib/snapshots";

describe("scenario snapshots", () => {
  it("captured_at is a real date, not a placeholder", () => {
    expect(new Date(SNAPSHOT_CAPTURED_AT).toString()).not.toBe("Invalid Date");
  });

  it("has a captured snapshot for every curated scenario", () => {
    for (const scenario of SCENARIOS) {
      expect(() => getScenarioSnapshot(scenario)).not.toThrow();
    }
  });

  it("analyze snapshots reflect an uncached run", () => {
    for (const scenario of SCENARIOS.filter((s) => s.endpoint === "analyze")) {
      const snapshot = getScenarioSnapshot(scenario);
      expect("cached" in snapshot && snapshot.cached).toBe(false);
    }
  });

  it("refund snapshots carry a real status", () => {
    for (const scenario of SCENARIOS.filter((s) => s.endpoint === "refund")) {
      const snapshot = getScenarioSnapshot(scenario);
      expect("status" in snapshot && typeof snapshot.status).toBe("string");
    }
  });

  it("throws instead of returning nothing for an uncaptured id", () => {
    expect(() => getScenarioSnapshot({ ...SCENARIOS[0], id: "does-not-exist" })).toThrow(
      /no captured snapshot/i
    );
  });
});
