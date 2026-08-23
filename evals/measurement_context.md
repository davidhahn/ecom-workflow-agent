# Measurement Context

A metric depends partly on how the system was set up when it ran. Change the embedding provider, and the same query can rank a different chunk first. This project already lived through that. The strips below name the setup behind every result in `primary_results.md` and `experiment_history.md`, so nobody has to guess which environment a number came from.

## The gap this project already hit

Almost every "current" number so far ran locally: today's live rerun, the ablation study, the model comparison. Local embeddings, threshold 0.46. Production runs Voyage, threshold 0.48.

One real case shows these aren't interchangeable. The query `"damaged shipments policy"` ranks the correct policy chunk 2nd locally, distance 0.4191, well inside the 0.46 cutoff. Under Voyage, the same query and corpus rank that chunk 4th, distance 0.6101, outside any threshold that would still make sense. Nothing about the question changed. The embedding space did.

## Result sets

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

Read a "current" number next to its strip. A 100% measured locally is a claim about the local configuration. It says nothing about Voyage until someone checks. `primary_results.md`'s `rag` row is exactly that kind of claim, real and still unverified against what production runs today.
