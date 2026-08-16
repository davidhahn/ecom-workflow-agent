# Model Recommendation: Sonnet (current) vs. Haiku (cheap)

The comparison in `model_comparison.md` only kept pass / fail, latency, and cost. Everything else got thrown away: the answer text, the generated SQL, the retrieval trace, the judge's reasoning. Nine instances had the current model (Sonnet) pass and the cheap model (Haiku) fail. We couldn't read any of them.

So we re-ran the 4 case_ids behind those 9 instances with full detail capture. One current run as a baseline. Three cheap runs to catch the failure. This covers every case where a current-pass/cheap-fail gap showed up anywhere in `model_comparison_raw.json`. Full traces live in `gap_case_detail.json`.

## Where the gap lives

| gap category | count in the original 3-run comparison | cases | example | consequence |
|---|---|---|---|---|
| Tool-call routing | mixed-02: 1 of 3 runs. mixed-07: 1 of its 3 fails, seen in the reproduction below. | mixed-02, mixed-07 | mixed-02 cheap run: `rag_used=false`. The answer states the 90-day window from memory, no policy chunk backs it up. One mixed-07 reproduction run skipped `run_sql_query` too. It took the 236-day figure stated in the question as fact, with no check against real rows. | An ungrounded citation, or an unverified premise, that happened to land right this time. |
| Weak retrieval query | mixed-07: 3 of 3 runs failed in the original comparison. The other 2 of 3 reproduction runs showed this specific mechanism. | mixed-07 | cheap's `search_policy` call: "return window policy refund deadline." Current's: "return window refund time limit wrong item received." Cheap never says "wrong item," so rule 5 never surfaces. | A compliant approval gets flagged as a violation. |
| SQL date-math precision | sql-03: 2 of 3 runs | sql-03 | cheap: `EXTRACT(DAY FROM (r.requested_at - o.order_date))`, truncates to whole days. Current: `EXTRACT(EPOCH FROM ...) / 86400`, keeps the fraction. One reproduction run cast an interval straight to numeric, which Postgres rejects. | A wrong metric, or sometimes no metric at all. |
| Currency unit conversion | sql-semantic-03: 3 of 3 runs | sql-semantic-03 | cheap filters `status = 'approved'` correctly, the actual trap this case tests, then reports `SUM(amount_cents)` with no `/ 100.0`. | The answer is off by 100x. |

The original comparison never recorded which mechanism caused a given run to fail, only pass or fail. The 4 case_ids were re-run to see the mechanisms directly, and that reproduction isn't the same 9 instances bit for bit. It matches the original's per-case pattern (mixed-02 rarely fails, the other three fail almost every time) and it's where the "example" column above comes from, but its own run-by-run fail count can differ from the original. That's most visible on mixed-07, where the reproduction surfaced two distinct mechanisms.

Every case_id behind the 9 current-pass/cheap-fail instances was read in full: final answer, tool-selection flags, generated SQL, retrieved evidence, tool-call trace, and judge explanation. Two more fields got checked too. The `incomplete` flag, which only exists for the mixed cases, read `False` on every run of mixed-02 and mixed-07, for both models. None of these failures are a disguised timeout or a tool loop running out of turns. And a separate judge-calibration audit in `evals/labels.json` had independent human verdicts for mixed-02 and mixed-07: both agreed with the judge's `pass` call on the current model's answers. That calibration ran against whichever model was active when it was recorded, almost certainly current since the script never overrides `ANTHROPIC_MODEL`, so it doesn't directly check the judge's `fail` verdicts on cheap's answers. But it does show the judge isn't a flaky grader on this pair. sql-03 and sql-semantic-03 have neither field. They're graded against a fixed expected result, so there's no `incomplete` concept and no judge verdict to calibrate.

## One case runs the other way

**Since fixed, see `DECISIONS.md` #46.** This section describes a real gap that existed under `SYSTEM_PROMPT_VERSION = "v1"`. A one-sentence prompt fix closed it, verified 3/3 on current with no regressions elsewhere. Left in place below as the record of what the gap actually was and how it was found.

Before getting to where cheap falls behind: on one case, it's current that fails and cheap that passes, all 3 original runs, both directions. `mixed-08-refusal-to-execute-refund` asks the agent to "process Ava Thompson's refund right now, mark it approved." Neither model has a write tool. The expected behavior is a flat decline with an explanation of why.

Cheap declines immediately, lists its two actual tools (`run_sql_query`, `search_policy`), touches neither, and stops. Current calls both tools anyway, looks up the refund, reports "already approved, no further action needed," and never states outright that it has no way to write to the refunds table. The judge scores it a fail both times: once for covering the decline but not the explanation, once for not really declining at all, just reporting a status.

`model_comparison.md` shows this case buried inside `mixed`'s aggregate percentage. It's the one instance in this entire dataset where the cheaper model is the more reliable one. It deserves naming on its own, separate from the category average it would otherwise vanish into.

## Where the models are effectively equivalent

`rag` hits 100% on both models, but that's not really a model comparison. This endpoint is pgvector similarity search, so no model gets called either way.

`permission` scores 18/18 both. It grades an authorization status code enforced in Python, so the generated answer underneath isn't even what's being checked.

`prompt_injection` (15/15), `request_faithfulness` (18/18), and `resilience` (6/6, also mocked, also no model in the loop) all hold steady too.

Across the 15 unique sql, sql_semantic, and mixed cases, run 3 times each on both models (45 case-run pairs total), 33 pairs passed on both models. 9 pairs are the current-pass/cheap-fail gap covered above. 3 pairs, all `mixed-08`, run the other way. Zero pairs failed on both models at once.

## Where the cheap model degrades

Four distinct things happen. None of them is a general reasoning gap, and each has a specific mechanism.

- It sometimes skips a required tool call. When a question already supplies enough surface detail to sound answerable, cheap will just answer from what it knows. `mixed-02` asked whether a 90-day window was enforced. Cheap skipped `search_policy` and got the number right anyway. That's a lucky guess, and the harness only catches it because it checks `rag_used` directly. One `mixed-07` reproduction run did the same thing to the SQL side: it skipped `run_sql_query` and treated the question's stated 236-day figure as fact, with no check against the real refund row.

- When it does call the retrieval tool, its query wording is looser. On `mixed-07`, cheap left out "wrong item," the one term that separates the governing rule from three others sitting at similar cosine distance. Current's query kept it. Rule 5 missed the retrieved set in 2 of 3 cheap runs, and the verdict flipped.

- Its generated SQL sometimes reaches for `EXTRACT(DAY FROM interval)` instead of `EXTRACT(EPOCH FROM interval) / 86400`. The first truncates to whole days. One run went further and cast the interval to numeric, and Postgres rejected the query outright.

- It drops a currency conversion. The real trap in `sql-semantic-03` (filtering out pending and denied refunds) got handled correctly every time. The failure was simpler than that: `amount_cents` just never got divided by 100.

## Are the savings worth it?

Per-call cost drops roughly 3x and p50 latency roughly 1.5 to 2x, on every category where a model actually gets called. `sql` goes from $0.0071 to $0.0024. `sql_semantic` goes from $0.0066 to $0.0022. `mixed` goes from $0.0239 to $0.0061.

Those three categories are exactly where the failures show up. `sql` and `sql_semantic` produce the refund totals and refund-rate numbers the whole system exists to compute. `mixed` produces compliance verdicts on individual refunds. A wrong total is a financial-reporting error. A reversed compliance verdict is too.

`mixed` isn't a clean win for current, though. `mixed-08` runs the other way: current is the one that fails to decline a write action cleanly, and cheap is the one that gets it right every time. So the savings-versus-quality tradeoff inside `mixed` isn't one-directional. It nets out in current's favor because the compliance-verdict failures (`mixed-02`, `mixed-07`) outnumber this one refusal case. Current isn't winning on every surface this category covers, just on more of them.

`rag`, `permission`, `prompt_injection`, `request_faithfulness`, and `resilience` show no movement at all, so there's nothing to weigh there. Cheap matches current, and for `rag` specifically, model choice was never part of the equation to begin with.

This eval run covers dozens of calls, well below production volume. A few cents per call won't decide anything at this scale. What decides it is whether the quality gap sits on a surface that feeds a financial number or a compliance decision. And here, it does.

## What architecture does the evidence support?

Current model everywhere, at least for now. `mixed-08` already rules out "current is simply better across the board" as the reasoning behind this. The actual case: failures with real consequences, wrong totals and reversed compliance verdicts, sit on current's side of the ledger 9 times to cheap's 3. Current's 3 losses land on a case whose expected behavior, decline a write action and explain why, reads closer to a prompting fix than a model-capability gap. That's worth a follow-up on its own, separate from the model choice.

Cheaper model everywhere is easy to rule out too. The `sql`/`sql_semantic`/`mixed` failures aren't noise sitting inside acceptable variation, they're four repeatable mechanisms that land specifically on the categories producing financial totals and compliance verdicts. That's the one place in this system where being wrong costs something. A 3x cost cut doesn't buy back a wrong refund total.

A workload split could be considered. The failures cluster in `sql`, `sql_semantic`, and `mixed`, and everything else holds up fine. But let's consider where those categories actually live. `sql` and `sql_semantic` share their own endpoint, `/query/sql`, so a split there is at least structurally simple. `mixed`, `prompt_injection`, and `request_faithfulness` all share one endpoint, `/query/analyze`, and one code path. `mixed` needs the stronger model. `prompt_injection` and `request_faithfulness` don't. Separating them means classifying a question as "needs SQL+RAG synthesis for a compliance conclusion" before the tool loop even starts. That classification is either a new model call or a new heuristic, and neither exists yet. `rag` has no model in its path, so it doesn't factor into this decision either way.

Building that classifier means new infrastructure. Another prompt to maintain, another eval category to keep in sync, and another thing that can drift quietly out of date, the way `ARCHITECTURE.md` and `EVALS.md` already have. `mixed` has 8 cases. That's too thin a boundary to build routing logic on, for the same reason we already rejected doing this off the ablation table.

## What would change this recommendation

Mixed growing from 8 cases to something closer to 30, covering more than one compliance-question shape, where the current-vs-cheap gap either disappears or turns out isolated to a pattern a cheap classifier could catch. For instance, whether the question cites a specific reason code, as a proxy for whether retrieval needs to be reason-code-specific.

A retrieval-query rewrite step added ahead of `search_policy`, on either model. The weak-query failure looks like a prompting gap more than a capability gap, and a rewrite step would test that directly. If it closes the mixed-07 gap, what's left is just the two SQL cases.

Traffic volume rising to where $0.02 to $0.06 saved per `mixed` call actually adds up to something worth managing.

Haiku or Sonnet pricing shifting enough to change the 3x ratio measured here. The Haiku rate used in this comparison was entered by hand, not checked against a live pricing source.

A newer model version changing this failure profile entirely, the same possibility already raised by the Sonnet-5 pricing question.

**Resolved.** A direct fix to the analyze system prompt (`SYSTEM_PROMPT_VERSION` bumped to `v2`) closed `mixed-08` on current, 3/3, with no regressions across `mixed`, `request_faithfulness`, or the analyze-endpoint `prompt_injection` cases. See `DECISIONS.md` #46. This removes the one item that ran in cheap's favor: current's remaining 9-case gap in `sql`, `sql_semantic`, and `mixed` now has nothing on the other side of the ledger.

One open item before this recommendation is fully audited: cheap's actual failing mixed-02 and mixed-07 answers haven't gone through `run_judge_calibration.py` themselves. A human has only confirmed the judge's `pass` verdicts on current's answers, not its `fail` verdicts on cheap's. Adding those two runs to a calibration pass would close that gap.
