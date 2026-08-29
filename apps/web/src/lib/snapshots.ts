import type { AnalyzeResponse, RefundEvaluateResponse } from "@/lib/api";
import type { Scenario } from "@/lib/scenarios";
import snapshotsFile from "./scenario-snapshots.json";

type Snapshot = AnalyzeResponse | RefundEvaluateResponse;

const SNAPSHOTS = snapshotsFile as { captured_at: string; results: Record<string, Snapshot> };

export const SNAPSHOT_CAPTURED_AT = SNAPSHOTS.captured_at;

// Fails loudly on a missing capture rather than rendering an empty or
// misleading card. Run evals/capture_scenario_snapshots.py to add one.
export function getScenarioSnapshot(scenario: Scenario): Snapshot {
  const snapshot = SNAPSHOTS.results[scenario.id];
  if (!snapshot) {
    throw new Error(
      `No captured snapshot for scenario "${scenario.id}". Run evals/capture_scenario_snapshots.py.`
    );
  }
  return snapshot;
}
