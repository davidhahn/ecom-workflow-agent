# Running evaluations

Use the evaluation runner to check the assistant against known cases and compare behavior across changes. [EVALS.md](../EVALS.md) defines the categories and coverage limits. The [Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab) presents saved results.

## Prepare the environment

Follow the [API setup](../apps/api/README.md) first. The runner needs the configured database, migrations, seeded records, and ingested policy corpus. Use a development database: evaluations exercise application paths and write logs.

Run the commands below from `apps/api`. The runner invokes the FastAPI application through its test client, so a separate API server is unnecessary. It supplies the configured proxy-secret header itself.

## Run the deterministic subset

```bash
poetry run python ../../evals/run.py --subset deterministic
```

This runs 18 cases covering refund rules, answer checks, and simulated model failures. It makes no live model calls and skips the live cache check. The other application environment settings are still required.

This is the evaluation subset used in CI. The separate pytest step includes some tests that call Claude, so running all of pytest has different requirements.

## Run all supported cases

With a working Anthropic key configured:

```bash
EVAL_RATE_LIMIT_BYPASS=1 poetry run python ../../evals/run.py --bypass-cache
```

The runner currently scores 62 of the dataset's 79 cases. It reports unsupported categories and skipped cases separately. It also runs a cache check. Live model calls incur cost; retrieval uses the configured embedding provider.

`--bypass-cache` skips cached answers on supported case paths. The separate cache check intentionally exercises caching.

To compare a different application model:

```bash
EVAL_RATE_LIMIT_BYPASS=1 poetry run python ../../evals/run.py --model MODEL_ID
```

Replace `MODEL_ID` with the model to test. This option enables cache bypass automatically. The judge uses its separate `JUDGE_MODEL` setting and remains fixed when the application model changes.

## Read the output

Each run creates a timestamped directory under [results](results/):

| File | Contents |
|---|---|
| `report.md` | Category scores, case outcomes, and skipped coverage |
| `results.json` | Structured results for inspection and reporting |
| `experiment.json` | Model settings, prompt versions, dataset hash, commit, and cache setting |

Failure records provide additional details for failed cases. Start with the case ID and reason, then inspect generated SQL, returned rows, or judge reasoning as appropriate. A failed verdict can indicate an application defect, a scoring problem, or an environment issue.

The runner exits with status 1 if a scored case or the cache check fails. A successful exit does not mean every case in the dataset ran. Check skipped coverage before reporting a pass rate.

## Compare changes

Keep the dataset, seed data, judge, and embedding provider consistent when comparing an application change. Record intentional differences. Repeat model-dependent runs to see whether the result holds across attempts.

Report case counts alongside percentages. Seven cases over three runs produce 21 outcomes, with repeated observations of the same questions. Those observations do not establish performance on 21 independent questions.

Inspect failures before changing the prompt or code. Preserve the case expectations during a fix; a suspected scoring defect needs its own review and explanation. The [case study](../CASE_STUDY.md) shows how that distinction changed the SQL work.

For retrieval comparisons, use the provider you intend to deploy and its calibrated threshold. Local results do not validate production ranking behavior.

## Further reading

- [Methodology](methodology.md): scoring and review procedures.
- [Primary results](primary_results.md): selected before/after measurements.
- [Experiment history](experiment_history.md): changes tested and their outcomes.
- [Measurement context](measurement_context.md): configuration and interpretation limits.

Timestamped reports preserve what happened during those runs. Read their configuration before applying an older result to the current application.
