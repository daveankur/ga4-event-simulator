# GA4 Event Simulator — User Guide

A CLI tool that sends fake but realistic events to a GA4 property via the
Measurement Protocol, so you can practice DebugView, Realtime,
Explorations, funnel reports, and BigQuery exports without a real app.
This guide currently covers the signup funnel flow, its first
implementation. See [signup-funnel-simulator-PRD.md](signup-funnel-simulator-PRD.md)
for the original spec and [RELEASE_NOTES.md](RELEASE_NOTES.md) for what's
changed between versions.

## 1. Setup

### 1.1 Create a GA4 property and API secret

Use a **personal practice property**, not a production one.

1. In GA4: **Admin** → **Data Streams** → pick (or create) a web data
   stream.
2. Copy the **Measurement ID** shown at the top of that stream (`G-XXXXXXX`).
3. On the same page, click **Measurement Protocol API secrets** → **Create**.
   Give it a nickname and copy the secret value immediately — GA4 only
   shows it once.

### 1.2 Install dependencies

```bash
cd ga4-event-simulator
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Activate the venv so you can just type `python` instead of `.venv/bin/python`:

```bash
source .venv/bin/activate
```

### 1.3 Configure credentials

```bash
cp .env.example .env
```

Edit `.env`:

```
GA4_MEASUREMENT_ID=G-XXXXXXX
GA4_API_SECRET=your_api_secret_here
```

`.env` is git-ignored — never commit it.

## 2. Quick start

```bash
# Check the payload shape against GA4's validator, no data sent, no credentials required to skip network calls
python main.py --dry-run

# Confirm GA4 accepts the payload shape (does hit the network, needs real credentials)
python main.py --validate --delay 0

# Send one real funnel (all 5 events) and check GA4 DebugView
python main.py
```

## 3. CLI parameters

| Flag | Type | Default | Description |
|---|---|---|---|
| `--count <n>` | int | `1` | Number of simulated signups to run. `1` (the default) always completes the full 5-event funnel. Values `>1` apply drop-off modeling (normal scenario only — see below). |
| `--scenario <normal\|device-switch\|re-request>` | string | `normal` | Which funnel pattern to simulate. See §4. |
| `--delay <seconds>` | float | `3` | Delay between events within one simulated funnel. Set to `0` for fast local testing; keep a few seconds for realistic DebugView pacing. |
| `--dry-run` | flag | off | Print payloads to stdout, make no network calls. Combinable with `--validate`. |
| `--validate` | flag | off | Send to GA4's `debug/mp/collect` endpoint instead of the real one — returns Google's schema validation response (`validationMessages`) without recording any data. Combinable with `--dry-run`. |
| `--drop-off <path or inline JSON>` | string | built-in defaults | Override the per-step drop-off rates. Only applies to the `normal` scenario with `--count > 1`; ignored (with a log note) for `device-switch` and `re-request`. |
| `--debug-client-id <id>` | string | none (fresh `client_id` per user) | Pin every event in this run to one fixed `client_id`, instead of a fresh random one per user. Debugging aid for GA4 DebugView visibility — see §5.1. `signup_id` still varies normally per user; only the transport-level `client_id` is overridden. Prints a warning if combined with `--scenario device-switch`, since it collapses that scenario's two-`client_id` mechanic. |
| `--days-ago <n>` | int | `0` (real time) | Backdate `signup_page_viewed`/`step1`/`step2` to N days before now instead of sending in real time. See §6. |
| `--completion-gap-hours <n>` | float | `0` | On top of `--days-ago`, push `signup_verification`/`signup_completed` forward N hours, to simulate confirmation happening some time after signup. See §6. |

### `--dry-run` vs `--validate`, combined

- `--dry-run` alone: no network call at all. Payload is printed, tagged
  `DRY-RUN`.
- `--validate` alone: hits GA4's debug endpoint (never records real data),
  prints the payload and Google's validation response. **Requires real
  credentials** since it does make a network call.
- Both together: same as `--validate` alone — the debug endpoint is safe to
  call under a "dry run" since it never records data. Useful for confirming
  payload shape when first setting the tool up (per PRD §7).

### `--drop-off` format

Default (cumulative % of simulated users reaching each step):

```json
{
  "signup_page_viewed": 100,
  "signup_step1_submitted": 80,
  "signup_step2_submitted": 65,
  "signup_verification": 55,
  "signup_completed": 45
}
```

Pass either an inline JSON string or a path to a JSON file with any subset
of these keys (missing keys fall back to the defaults):

```bash
python main.py --count 50 --drop-off '{"signup_step1_submitted": 90}'
python main.py --count 50 --drop-off my_dropoff.json
```

## 4. Scenarios

### `normal` (default)

Each of `--count` simulated users gets one `signup_id`, reused as the GA4
`client_id` for every event. With `--count 1` the funnel always completes
all 5 events. With `--count > 1`, each user independently rolls against the
drop-off rates at each step and may stop early — this is what produces a
realistic drop-off shape in GA4 Explorations.

```bash
python main.py --count 30
```

### `device-switch` (TC1)

Simulates a user who starts signup on one device/session and finishes
verification + completion on another. Steps 1–3 are sent under one
`client_id`; verification and completion are sent under a second,
different `client_id`. The `signup_id` stays identical across all 5
events — the point is to confirm GA4 still resolves this as one journey
via `signup_id` even though `client_id` changed. There's an extra pause
(`2× --delay`) between the two sessions to represent the device switch. This
scenario always completes; `--drop-off` is ignored.

```bash
python main.py --scenario device-switch --count 5
```

### `re-request` (TC2)

Simulates a user whose verification email expired, so they re-request it
before completing. The re-request itself does **not** fire a GA4 event —
it's represented only as an extra delay and an informational log line.
Exactly one `signup_verification` and one `signup_completed` fire, both
against the original `signup_id`. Always completes; `--drop-off` is
ignored.

```bash
python main.py --scenario re-request --count 5
```

## 5. Verifying events actually landed in GA4

- **DebugView** (`Admin` → `Data display` → `DebugView`): near-real-time,
  but has a real gotcha — see §5.1 below before assuming something's broken
  if it stays empty.
- **Realtime report** (`Reports` → `Realtime`): confirms events are hitting
  standard collection. This is the most reliable quick check and does
  **not** depend on `debug_mode` or the client_id quirk below — trust this
  over DebugView if the two disagree.
- **Explorations / funnel reports**: **not** real-time — GA4 typically
  takes a few hours (sometimes up to 24–48h) to fully process standard
  reporting data. Use this to evaluate batch-mode drop-off shape or the
  scenario journeys, but don't expect it immediately after a run.
- **BigQuery export** (if linked): daily export tables land once a day;
  the `events_intraday_YYYYMMDD` table (if streaming export is enabled)
  updates same-day.

### 5.1 Getting DebugView to actually show something

Every event this tool sends (outside of `--dry-run`/`--validate`) includes
`debug_mode: true` and `engagement_time_msec`, which are required for
Measurement Protocol events to be eligible for DebugView at all. That's
necessary but **not sufficient**: per Google's docs and independent
GA4 experts (e.g. Simo Ahava), DebugView only surfaces a `client_id` once
that ID already has *prior data* recorded against it in GA4. A brand-new
random `client_id` — which is what every simulated user gets by default —
can be recorded correctly (visible in Realtime, standard reports, BigQuery)
while never showing up in DebugView at all.

To work around this for troubleshooting, reuse a fixed `client_id` across
a few runs with `--debug-client-id`:

```bash
python main.py --debug-client-id local-debug-1
```

Run it a couple of times with the same `--debug-client-id` value; once GA4
has "seen" that ID before, subsequent runs under it should start appearing
in DebugView. Also keep DebugView open and watching *while* you run the
command — it's a live stream, not a stored log, so traffic sent before you
opened the page won't retroactively appear.

This flag is a debugging aid only — don't use it for real batch generation,
since it defeats the point of unique per-user identities, and it prints a
warning if combined with `--scenario device-switch` since it collapses that
scenario's two-`client_id` mechanic.

## 6. Backdating funnels (`--days-ago` / `--completion-gap-hours`)

By default every event is sent in real time — `signup_page_viewed` happens
"now," and the rest follow a few seconds apart per `--delay`. To simulate a
funnel where confirmation happens some time after signup (e.g. the user
verifies the next day), backdate it instead:

```bash
# Signup happened 1 day ago; confirmation followed 24h after that
python main.py --days-ago 1 --completion-gap-hours 24
```

- `--days-ago N`: shifts `signup_page_viewed`, `signup_step1_submitted`,
  and `signup_step2_submitted` to N days before now.
- `--completion-gap-hours N`: on top of that, pushes
  `signup_verification` and `signup_completed` forward N hours from where
  `--days-ago` landed — e.g. `24` means "confirmed the next day."
- Both flags work with `--count`, `--scenario`, and everything else. Use
  `--delay 0` for backdated batches — the day-scale gap is encoded in each
  event's timestamp, not real waiting, so there's no need to actually sleep.
- Each event's real send time is echoed in the log as `ga4_timestamp=...`
  alongside the timestamp GA4 will actually record it under, so you can
  confirm it landed where you expected.

**Hard limit: ~72 hours.** GA4 Measurement Protocol silently clamps (or
rejects, depending on its settings) any event timestamped further back
than about 3 days — it cannot be made to look like it happened weeks ago.
The tool validates `--days-ago` + `--completion-gap-hours` against a
71-hour ceiling up front and errors out clearly if you exceed it, rather
than silently sending data to the wrong date. If you need real multi-week
historical data, that requires GA4's BigQuery Data Import, which is outside
what this Measurement-Protocol-based tool can do — to build up a spread of
days within the 3-day window, just run the tool once per `--days-ago`
value (`0`, `1`, `2`).

Since backdated events don't represent "right now," don't expect them in
DebugView or Realtime (both are live/near-live views) — check Explorations
or the standard Events report instead (see §5).

## 7. Logging

Every event that is actually sent (or would be, under `--dry-run`/
`--validate`) is logged to stdout with a timestamp, `signup_id`, event
name, params, and a status field indicating what happened:

- An HTTP status code (e.g. `204`) for real sends.
- `DRY-RUN (not sent)` for `--dry-run`.
- `VALIDATE http=<code>` plus the payload and Google's validation response
  for `--validate`.
- `REJECTED (PII check failed)` if a param other than `email_domain`
  contains an `@` character — the event is not sent in this case.
- `ga4_timestamp=...` appended when `--days-ago`/`--completion-gap-hours`
  is in effect, showing the backdated time GA4 will record for that event.

## 8. Customizing fake data pools

`data_pools.json` holds the pools `signup_method`, `email_domain`,
`setup_option`, and `data_center` are drawn from. Edit it directly to add
or change values — no code changes needed.

## 9. File overview

| File | Purpose |
|---|---|
| `main.py` | CLI entry point, argument parsing, dispatch to scenarios |
| `config.py` | Loads `.env` credentials, data pools, drop-off defaults/overrides |
| `identity.py` | Generates `signup_id`/`client_id` UUIDs and fake user profiles |
| `events.py` | Builds the GA4 event payload for each of the 5 funnel steps |
| `validation.py` | No-PII guard (rejects payloads with a stray `@`) |
| `ga4_client.py` | Sends events to the real or debug MP endpoint, or prints them under `--dry-run`; handles stdout logging |
| `scenarios.py` | Orchestrates the `normal`, `device-switch`, and `re-request` flows |
| `timing.py` | Computes backdated `timestamp_micros` values and enforces the 72-hour ceiling |
| `data_pools.json` | Editable fake data pools |
| `.env.example` | Template for GA4 credentials |
