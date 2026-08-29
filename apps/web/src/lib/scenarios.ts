// Static, curated scenario config for the landing-page demo. Deliberately
// not an authoring system: adding a scenario means editing scenarios.json
// and nothing else. Each `input` is real text sent verbatim to the named
// endpoint; several are drawn from apps/api/evals/cases.json (see
// scenarios.json's own comments in git history) so the "expected" copy is
// checked against seeded DB rows, not invented for the UI.
//
// The data lives in scenarios.json, not here, so evals/capture_scenario_
// snapshots.py can read the exact same inputs without a Python port of this
// file drifting out of sync.

import scenariosData from "./scenarios.json";

export type ScenarioEndpoint = "analyze" | "refund";

export type Scenario = {
  id: string;
  name: string;
  businessContext: string;
  expectedBehavior: string;
  endpoint: ScenarioEndpoint;
  input: string;
};

export const SCENARIOS: Scenario[] = scenariosData as Scenario[];
