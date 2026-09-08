# Experiment History

Some experiments changed the application. Others corrected how I measured it. Rows marked **MEASUREMENT CHANGE** altered the evaluation process, so a score change in those rows alone does not establish an improvement in application behavior.

## Table

| change | measured effect | decision | type |
|---|---|---|---|
| Remove `sql-05` (flawed test case) | Corrected a false failure. The case tested two things at once and couldn't say which broke. | fix eval | **MEASUREMENT CHANGE** |
| Add semantic SQL assertions (check the returned value against a known-correct number) | Exposed 14/21 (67%): legal SQL computing the wrong number, invisible to shape-only checks | fix eval, then investigate | **MEASUREMENT CHANGE** |
| SQL prompt v2 | Semantic SQL 14/21 → 21/21 (100%) | keep | |
| Expand `mixed` from 3 to 8 cases | Exposed `mixed-08`: a refund-approval request answered without ever declining it | fix eval, then investigate | **MEASUREMENT CHANGE** |
| Mixed-08 system prompt fix (state the write boundary explicitly) | `mixed-08` 0/3 → 3/3. 19/19 regression check across every case sharing the prompt. | keep | |
| Split `JUDGE_MODEL` from `ANTHROPIC_MODEL` | A model comparison would have graded a cheap model with a cheap judge. No score moved. A real contamination risk closed. | fix eval | **MEASUREMENT CHANGE** |
| Fix `/query/rag`'s missing cache bypass in the ablation harness | Off-topic refusal read 0/15 for every variant, including the one with the threshold on. Baseline's cached answer was being reused everywhere. | fix eval and fix the same bug in production | **MEASUREMENT CHANGE** |
| Add RAG relevance threshold | Off-topic refusal 0/15 → 12/15 (80%) | keep | |
| Widen RAG retrieval depth (`k`) | A real off-topic case (`rag-13`) already leaks all 3 of its top candidates at the current `k`. Widening `k` to 5 would let all 5 leak. No on-topic case gained anything. | rejected | |
| Bounded failure handling (retry wrapper around the Anthropic call) | Resilience 0/6, all crashed, → 6/6 | keep, reliability invariant | |
| Cheaper application model (Haiku) | Matched RAG (100% both). Semantic SQL 21/21 → 16/21. Mixed quality 88% → 84%. Cost and latency roughly a third. | retain Sonnet; defer routing selected requests to Haiku | |
| Per-provider RAG threshold (0.46 local, 0.48 voyage) | A real production question got a false "I don't know" under voyage that local eval runs never caught | keep | |
| Groundedness matches rule titles as well as numbers | `ground-01` flips from a false ungrounded flag to correctly grounded | keep | |
| Refund extraction: strip quantity from the product name | `refund-11` live: `could_not_process` → `requires_manager_approval`, the correct outcome | keep | |
| Local rerun of `mixed`, August 22 | `mixed-08` still passes. `mixed-07` fails now, on a real judge finding no prior run caught. | open, not yet fixed | |

## Decisions from the experiments

Widening retrieval depth added irrelevant candidates without improving the on-topic cases. I rejected that change.

Haiku reduced cost but lost accuracy on SQL and some combined workflows. I retained Sonnet and deferred routing selected requests to Haiku.

## mixed-07: an open finding

In the August 22 run, `mixed-08` passed after its prompt fix. `mixed-07` failed when the answer disputed a fact supported by the database. That failure remains open in this report.
