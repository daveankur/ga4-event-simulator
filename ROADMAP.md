# Roadmap / Backlog

Ideas raised while building and using this tool, captured so they aren't
lost — not commitments, just a place to pull from later. Append as new
ideas come up; don't overwrite what's here.

## 1. Config-driven multi-flow simulator (the big one)

Generalize away from the hardcoded signup-only `events.py` into a
`--flow <name>` selector that reads a flow definition file (YAML/JSON),
so adding a new event set is a config change, not new code.

Two flow types, since they need different mechanics:
- **Funnel**: ordered steps, drop-off between them, one identity persists
  across the whole journey, supports scenario variants (device-switch,
  re-request style session/time gaps) — today's signup funnel becomes the
  first example of this type.
- **Independent**: unordered, frequency-weighted events (e.g.
  `dashboard_viewed`, `report_exported`, `settings_changed`) fired against
  a simulated pool of persistent fake users, so it looks like real ongoing
  engagement rather than a fresh first-time visitor on every event.

Schema sketch (discussed 2026-07-10):

```yaml
name: signup_funnel
type: funnel
identity_field: signup_id
steps:
  - event: signup_page_viewed
    fields: []
  - event: signup_step1_submitted
    fields: [signup_method, email_domain]
drop_off: {signup_page_viewed: 100, signup_step1_submitted: 80}
pools: {signup_method: [...], email_domain: [...]}
scenarios:
  device-switch: {split_after_step: 3}
  re-request: {gap_before_step: signup_verification}
```

```yaml
name: feature_usage
type: independent
user_pool_size: 50
events:
  - {name: dashboard_viewed, weight: 0.6, fields: [plan_tier]}
  - {name: report_exported, weight: 0.2, fields: [export_format]}
pools: {plan_tier: [...], export_format: [...]}
```

`ga4_client.py`, `timing.py`, `validation.py`, and most of `identity.py`
are already generic and would carry over unchanged. `events.py` and the
scenario-splitting logic in `scenarios.py` are what's currently
signup-specific and would need to become config-driven. Once the engine
generalizes, a second example flow (e.g. a purchase/checkout funnel) would
be a good way to prove the schema actually holds up beyond signup.

## 2. Multi-day history convenience

A flag (e.g. `--seed-history`) that auto-loops `--days-ago 0, 1, 2` in one
command instead of three separate invocations, to quickly populate a full
3-day window of realistic-looking Explorations data in one shot.

## 3. Closing the verification loop

- A post-run local summary (e.g. `--summary`) that prints a funnel table
  from what was actually sent, as an immediate sanity check — no need to
  wait on GA4's processing lag before Explorations shows anything.
- Optional GA4 Data API integration: after a run (plus a wait), auto-pull
  the real funnel numbers from GA4 and print them next to what was sent,
  so mismatches are obvious without manually poking around the GA4 UI.

## 4. Persistence / replay

Log every sent (or dry-run) payload to a local JSONL file, not just
stdout. Enables offline review, diffing between runs, or replaying a
previously-generated batch later without regenerating random profiles.

## 5. Config hygiene

Basic linting/validation of flow definition files before running (catch a
typo'd event name or missing pool value up front, rather than failing
mid-run or silently sending malformed data).

## Explicitly out of scope — revisit only if truly needed

- **True historical backfill beyond ~72 hours.** Measurement Protocol
  cannot do this (hard platform ceiling, see `timing.py`); would require
  GA4's BigQuery Data Import, a fundamentally different and much heavier
  mechanism than this CLI.
- **Geo/device-category variation per simulated user.** Measurement
  Protocol supports some override params for this, but it's only worth
  building if segmentation-report practice becomes an actual need.
