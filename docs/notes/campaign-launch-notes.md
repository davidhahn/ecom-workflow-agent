# Campaign Launch Notes

This document records the business context behind marketing campaigns tracked in the `campaigns` table — why a campaign ran, what it was expected to do, and what risk was known in advance if it ended. Session, page-view, and conversion data referenced here lives in `web_analytics`; revenue itself is never stored alongside it and must be computed from `orders`.

## Paid Social Growth Push: Overview

The Paid Social Growth Push was a `paid_social`-channel campaign, matching the `channel` value recorded for it in the `campaigns` table. The Paid Social Growth Push ran for roughly 30 days, tracked by `campaigns.start_date` and `campaigns.end_date`. The Paid Social Growth Push had a budget in the five-figure range, recorded in `campaigns.budget_cents` — large enough to be a primary driver of paid traffic during its flight window, not a token spend. Once its `end_date` passed, the Paid Social Growth Push's `status` moved to `ended`, matching the `campaigns.status` CHECK constraint's terminal value.

## Why the Paid Social Growth Push Ran

The Paid Social Growth Push was launched to grow top-of-funnel awareness and pull incremental sessions from audiences the organic and email channels were not reaching. Paid social was chosen over paid search for this push because the target audience skewed toward discovery-driven browsing rather than active search intent — the kind of buyer who finds a product by scrolling, not by searching for it directly.

## What the Paid Social Growth Push Was Expected to Do

The Paid Social Growth Push was expected to lift daily sessions meaningfully above their pre-campaign baseline for the full duration of its flight window, with a proportional lift to conversions from the added traffic volume. The Paid Social Growth Push was not expected to change the underlying conversion *rate* on its own — the goal was more sessions converting at a normal rate, not a higher-converting mix of sessions.

## Known Risk of the Paid Social Growth Push Ending

Paid social has historically driven roughly a quarter of total site sessions during an active flight window for a campaign of this size. The known risk, flagged before launch, was that ending the Paid Social Growth Push would remove that inflow abruptly rather than tapering it off — sessions sourced through the campaign do not carry over into organic or email channels on their own once paid spend stops. A sessions and conversion-rate drop in `web_analytics` beginning shortly after the Paid Social Growth Push's `end_date` is the expected signature of this risk materializing, not evidence of an unrelated problem elsewhere (e.g. refund volume, which this campaign's audience and channel have no structural connection to).
