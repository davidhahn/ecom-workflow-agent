# Measurement Context

A single number, like "92% pass rate," doesn't mean much on its own. It depends on which model answered the questions, which embedding provider searched the policy documents, and which version of the case file was used. Change any of those and the same query can behave differently, which is exactly what happened once in this project. Each block below records that exact setup for one specific result, so nobody reading `primary_results.md` or `experiment_history.md` has to guess which environment a number came from.

## The gap this project already hit

Almost every "current" number in this project's reports ran locally: today's live rerun, the ablation study, the model comparison. All of them used the local embedding model, at a 0.46 relevance threshold. Production runs a different, hosted provider instead, called Voyage, at a 0.48 threshold.

One real case shows these aren't interchangeable. The query `"damaged shipments policy"` ranks the correct policy chunk 2nd locally, distance 0.4191, well inside the 0.46 cutoff. Under Voyage, the same query and corpus rank that chunk 4th, distance 0.6101, outside any threshold that would still make sense. The query and the corpus stayed exactly the same. Only the embedding provider was different, and that alone moved the correct chunk from a safe 2nd place to an unusable 4th.

## Result sets

Each block below is one experiment's full configuration, everything that could affect its numbers, recorded together so a reader can check whether two results are comparable before treating them as such.

**Today's live rerun** (`refund_evaluator`, `groundedness`, `topic_coverage`, `resilience` current, `mixed` current)

```
Environment: local dev, not production-equivalent
Application model: claude-sonnet-4-6
Judge model: claude-sonnet-4-6
Embedding provider: local
Relevance threshold: 0.46
Suite: frozen suite, n=79 (62 runnable live)
Dataset version: 78fcd15b208e
Commit: 67509ca
```

**Ablation study** (`SQL / SQL semantic` and `rag` baseline and current, `resilience` baseline)

```
Environment: local dev, not production-equivalent
Application model: claude-sonnet-4-6 (Haiku only on the model-swap row)
Judge model: n/a, deterministic scoring only
Embedding provider: local, not recorded directly in ablation_raw.json
Relevance threshold: 0.46, a single value, before the local/Voyage split existed
Suite: frozen 27-case ablation subset
Dataset version: 78fcd15b208e
Commit: not recorded in the artifact. Closest by timestamp: d671e8e
```

**Model comparison** (Sonnet vs. Haiku)

```
Environment: local dev, not production-equivalent
Application model: claude-sonnet-4-6 vs. claude-haiku-4-5-20251001
Judge model: claude-sonnet-4-6, fixed for both arms
Embedding provider: local
Relevance threshold: 0.46
Suite: 46-case subset, 8 of 13 categories
Dataset version: 78fcd15b208e
Commit: generated 20:51 UTC on 2026-08-17, 16 minutes before the local/Voyage split landed (4be52c1, 21:07 UTC)
```

**RAG retrieval calibration**, run twice on purpose, once per provider:

```
Local embeddings
Relevance threshold: 0.46
Sample: 18 questions, 13 relevant labels, 34 irrelevant labels
```

```
Production / Voyage
Relevance threshold: 0.48
Sample: the same 18 questions, rerun under the provider production uses
```

**Production, live** (the deployed app itself)

```
Environment: production (Vercel + Render)
Application model: claude-sonnet-4-6
Embedding provider: Voyage (voyage-3.5-lite)
Relevance threshold: 0.48
```

## What to do with this

Always read a "current" number next to its configuration strip. A 100% pass rate measured locally is a claim about the local setup only. Whether it holds under Voyage is a separate question until someone checks. The `rag` row in `primary_results.md` is exactly that kind of claim: real, and still unverified against what production runs today.
