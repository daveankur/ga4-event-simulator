# Release Diary

Version format: `x.y` — `x` = major, `y` = minor. All dates below are when the
change was made in this project.

## 1.3 — 2026-07-10

**Added**

- **`--days-ago <n>` and `--completion-gap-hours <n>` flags**, to backdate
  simulated funnels instead of always sending in real time. `--days-ago`
  shifts `signup_page_viewed`/`step1`/`step2` back N days; on top of that,
  `--completion-gap-hours` pushes `signup_verification`/`signup_completed`
  forward N hours, to simulate confirmation happening some time after
  signup (e.g. `--days-ago 1 --completion-gap-hours 24` for "confirms the
  next day"). Implemented via the Measurement Protocol's `timestamp_micros`
  field, verified against Google's docs and confirmed via test dry-runs
  (see `timing.py`).
- **Hard 72-hour ceiling enforced up front.** Measurement Protocol only
  accepts backdated timestamps up to ~72 hours old — older values are
  silently clamped or rejected by Google, not actually recorded on the
  requested date. `--days-ago` + `--completion-gap-hours` combined is
  validated against a 71-hour ceiling before any events are sent, with a
  clear error if exceeded, rather than silently sending wrong data. Real
  multi-week historical backfill isn't possible through this tool (would
  require GA4's BigQuery Data Import instead) — documented as an explicit
  limitation.
- Timestamps are computed at send time (not pre-computed per batch), so
  within a batch, later users/events naturally land at slightly later
  times too, same as they would without backdating.
- The `--delay` flag's meaning is unchanged — it still controls real
  wall-clock pacing between requests, independent of the backdated
  timestamp attached to each event. Use `--delay 0` for fast backdated
  batch generation, since day-scale gaps no longer require real waiting.

**Files added:** `timing.py`
**Files touched:** `main.py`, `scenarios.py`, `ga4_client.py`

## 1.2 — 2026-07-10

**Added**

- **`--debug-client-id <id>` flag.** GA4 DebugView, as documented by Simo
  Ahava and confirmed against Google's own docs, only surfaces a
  `client_id` once that ID already has prior data recorded — a brand-new
  random `client_id` (which is what every simulated user gets by design)
  can be recorded successfully into Realtime/standard reports while never
  appearing in DebugView at all. This flag lets you pin every event in a
  run to one fixed, reusable `client_id` purely for DebugView
  troubleshooting, independent of the per-user `signup_id` (which keeps
  varying normally). Not intended for realistic batch generation — using it
  with `--scenario device-switch` prints a warning, since it collapses the
  scenario's two-client_id mechanic that TC1 is meant to test.
- **`engagement_time_msec` added to every event's params**, alongside
  `debug_mode`. Google's Measurement Protocol docs pair these two
  parameters together for debug-mode events; only `debug_mode` was being
  sent before.

**Files touched:** `main.py`, `scenarios.py`, `events.py`

## 1.1 — 2026-07-10

**Fixes**

- **Single run now always completes all 5 events.** Previously, drop-off
  modeling was applied even when running the tool with no `--count` flag
  (i.e. `count=1`), so a plain `python main.py` could randomly stop short of
  `signup_completed`. This contradicted the PRD's success criterion that
  running the tool once must produce all 5 events for one `signup_id`.
  Drop-off now only applies once actually batching (`--count` > 1).
- **Events now include `debug_mode: true`.** GA4 Measurement Protocol events
  are invisible in DebugView unless this flag is set on each event's params.
  Without it, real sends were landing in standard reporting but never
  appearing in DebugView, making the tool hard to verify visually. This
  affects `main.py`/`events.py` output for every event, in every scenario.

**Files touched:** `scenarios.py`, `events.py`

## 1.0 — 2026-07-10

**Initial release.** Full implementation of the PRD
([signup-funnel-simulator-PRD.md](signup-funnel-simulator-PRD.md)):

- 5-event signup funnel (`signup_page_viewed` → `signup_step1_submitted` →
  `signup_step2_submitted` → `signup_verification` → `signup_completed`)
  sent via the GA4 Measurement Protocol, sharing one `signup_id` per
  simulated user.
- `--count N` batch mode, each simulated user with its own `signup_id` and
  fake profile (signup method, email domain, setup option, data center)
  drawn from `data_pools.json`.
- Configurable drop-off modeling per funnel step (default 100/80/65/55/45%
  cumulative reach), overridable via `--drop-off`.
- `--scenario device-switch` (TC1): steps 1–3 sent under one `client_id`,
  verification + completion sent under a second `client_id`, with
  `signup_id` held constant throughout to prove the funnel resolves as one
  journey despite the client_id change.
- `--scenario re-request` (TC2): simulates an expired-link re-request as an
  extra delay with no GA4 event fired for the re-request itself — exactly
  one `signup_verification` and one `signup_completed` per user.
- `--dry-run` (print payloads, no network calls) and `--validate` (send to
  GA4's debug endpoint for schema validation instead of the real endpoint),
  combinable per the agreed semantics.
- No-PII guard: rejects any event param (other than `email_domain`)
  containing an `@` character before sending.
- Structured stdout logging: timestamp, `signup_id`, event name, params,
  and response status/mode for every event.

**Files added:** `main.py`, `config.py`, `identity.py`, `events.py`,
`validation.py`, `ga4_client.py`, `scenarios.py`, `data_pools.json`,
`.env.example`, `.gitignore`, `requirements.txt`
