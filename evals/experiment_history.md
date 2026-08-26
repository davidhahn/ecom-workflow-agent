# Experiment History

This is a running log of every change that affected how this project gets measured, or what it measures. For each row: what changed, what the eval suite showed afterward, and what decision that led to. Rows marked **MEASUREMENT CHANGE** altered the eval suite itself: the ruler. A score moving on one of those rows is evidence about the ruler getting better. It says nothing on its own about whether the underlying system changed.

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
| Cheaper application model (Haiku) | Matched RAG (100% both). Semantic SQL 21/21 → 16/21. Mixed quality 88% → 84%. Cost and latency roughly a third. | recommended, not deployed | |
| Per-provider RAG threshold (0.46 local, 0.48 voyage) | A real production question got a false "I don't know" under voyage that local eval runs never caught | keep | |
| Groundedness matches rule titles as well as numbers | `ground-01` flips from a false ungrounded flag to correctly grounded | keep | |
| Refund extraction: strip quantity from the product name | `refund-11` live: `could_not_process` → `requires_manager_approval`, the correct outcome | keep | |
| Live rerun of `mixed` today | `mixed-08` still passes. `mixed-07` fails now, on a real judge finding no prior run caught. | open, not yet fixed | |

## Two rows worth a second look

**Widening RAG's `k`**, the number of chunks retrieval returns per question, looked like a plausible fix for a known retrieval gap. It made things worse somewhere else. Off-topic questions started leaking through the same door meant to let more of the right chunk in.

**The Haiku swap**, replacing the production model with a cheaper one, held its own on most categories. It lost ground on the two that carry financial and compliance weight. Sonnet stays the deployed model.

## mixed-07: a new, open finding

A live rerun of the suite caught something no earlier saved report had. `mixed-08` is fixed and stayed fixed. `mixed-07` failed on a problem nobody had written a case for. The judge caught the answer disputing a stated fact it should have confirmed against the real data. That row stays open, a candidate for the next round of this table.
