# Error Analysis — Week 1 Wrap-Up

## 1. Failure Distribution

| failure category | count | highest severity | example case | first failure point |
|---|---|---|---|---|
| *(none)* | 0 | — | — | — |

Zero confirmed application failures. 8 fresh full-suite runs this week all passed 37/37. The one case that ever failed (`sql-05`) turned out to be an eval bug, not a real one (see below).

## 2. Most Common Category

None. There's no failure data to group.

## 3. Highest-Severity Category

None confirmed. One known risk is still unmeasured: Claude sometimes answers a write request by quietly swapping in an unrelated read instead of declining it. If a future eval catches this for real, it would rank **High** (i.e. a confident, wrong response to what was actually asked). It's not counted here because no case currently measures it correctly.

This is exactly why frequency and severity get tracked separately: a risk can carry real severity and still show a frequency of zero, simply because nothing is watching for it yet.

## 4. Three Representative Failures

We don't have three. We have one historical case, and it didn't hold up as a real failure once investigated. Padding this section with invented examples would misrepresent what we actually found, so it's left at one:

- `sql-05-write-attempt-rejected`: asked for a write, expected it blocked, got back an unrelated successful read instead. Investigated and reclassified as an eval bug (see #5).

## 5. Evaluation or Scorer Bugs Discovered

Just one. `sql-05` combined two different questions into one check ("did Claude attempt a write" and "does the safety layer block a write"). A failure couldn't tell you which one broke. Fixed by removing the case and adding a direct test of the safety layer alone, which now passes every time.

## 6. Main Uncertainty

Most categories are still small. They're under the 8-case threshold we use before trusting a pass rate. A clean run on a small sample isn't proof the system is safe, just that we haven't found the gap yet. LLM-backed categories also vary run to run, so a clean week can still hide a low-frequency problem.

## 7. Recommended Order for Week 2

1. **Build a real eval for the write-substitution behavior.** "Did the response honestly tell the caller what happened" is a reading-comprehension question, not a substring match.
2. **Record the groundedness heuristic's content-blind gap in `DECISIONS.md`.** Already found a few, just not written down yet.
3. **Grow the small categories past the 8-case threshold** (`mixed`, `sql`, `rag`, `prompt_injection`, `permission`, `groundedness`, `topic_coverage`) so a passing run means something statistically, not just today.
4. **Move on to the model-swap comparison.** The eval quality prerequisites for it (judge calibration, stability check) are done this week. Running the suite on a cheap model vs. the current one is the next real step.
