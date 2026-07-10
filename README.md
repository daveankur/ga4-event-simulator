# GA4 Signup Funnel Simulator

A small Python CLI that sends fake but realistic signup-funnel events to a
GA4 property via the Measurement Protocol — so you can practice DebugView,
Realtime, Explorations, funnel reports, and BigQuery exports without a real
app, GTM container, or live users.

This is a personal-practice tool. It does not touch any production
analytics setup and generates zero PII — all identifiers and property
values are fake and produced locally.

## What it simulates

A 5-event signup funnel (`signup_page_viewed` → `signup_step1_submitted` →
`signup_step2_submitted` → `signup_verification` → `signup_completed`),
tied together by one `signup_id` per simulated user. It supports:

- **Batch generation** with configurable, realistic drop-off between steps.
- **Two scenario tests**: a device-switch journey (same `signup_id`, a
  different `client_id` partway through) and a verification-email
  re-request (confirms the funnel resolves as one journey, not two).
- **Backdating** (`--days-ago` / `--completion-gap-hours`), to simulate a
  signup today and a confirmation a day later, within Measurement
  Protocol's ~72-hour limit.
- **`--dry-run`** and **`--validate`** modes for safely inspecting payloads
  before anything real gets sent.

See [signup-funnel-simulator-PRD.md](signup-funnel-simulator-PRD.md) for
the original spec this was built against.

## Quick start

```bash
cd ga4-signup-simulator
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in your GA4 credentials, see below
```

```bash
source .venv/bin/activate

# Check the payload shape, no network call
python main.py --dry-run

# Confirm GA4 accepts it (needs real credentials, doesn't record data)
python main.py --validate --delay 0

# Send one real funnel
python main.py
```

Full flag reference, scenario walkthroughs, and how to verify data landed
in GA4: [USER_GUIDE.md](USER_GUIDE.md).

## Getting GA4 credentials

Use a **personal/practice GA4 property — never a production one.**

1. GA4 → **Admin** → **Data Streams** → pick or create a web data stream.
2. Copy the **Measurement ID** (`G-XXXXXXX`) shown at the top of that
   stream.
3. On the same page, **Measurement Protocol API secrets** → **Create**.
   Copy the secret immediately — GA4 only shows it once.
4. Put both in `.env` (copied from `.env.example`):
   ```
   GA4_MEASUREMENT_ID=G-XXXXXXX
   GA4_API_SECRET=your_api_secret_here
   ```

`.env` is git-ignored — never commit real credentials.

## Project docs

- [USER_GUIDE.md](USER_GUIDE.md) — full usage guide, every CLI flag, scenario details, verification steps.
- [RELEASE_NOTES.md](RELEASE_NOTES.md) — release diary (`x.y` versioning).
- [ROADMAP.md](ROADMAP.md) — ideas for future work, not yet built.
- [signup-funnel-simulator-PRD.md](signup-funnel-simulator-PRD.md) — the original product spec.

## Safety notes

- No-PII guard rejects any event param (other than the fake `email_domain`
  pool) that looks like it contains a real email address, before sending.
- All identifiers (`signup_id`, `account_id`, etc.) are randomly generated
  locally — nothing here is a real user.
- Intended for a personal/practice GA4 property only. Don't point
  `GA4_MEASUREMENT_ID`/`GA4_API_SECRET` at a production property.

## License

[MIT](LICENSE)
