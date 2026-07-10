# PRD: GA4 Signup Funnel Simulator

## 1. Purpose

Build a small CLI tool that sends fake but realistic signup funnel events to a GA4 property, using the 5-event spec below. This is a personal practice property, not the Conversive production property. The goal is to generate enough varied, realistic-looking event data to practice DebugView, Explorations, funnel reports, and BigQuery exports without depending on a live app or real users.

This is a standalone tool. It does not touch Conversive's codebase, GTM container, or production GA4 property.

## 2. Goals

- Simulate the 5-event signup funnel (`signup_page_viewed` through `signup_completed`) with one persistent `signup_id` across all events.
- Send events via the GA4 Measurement Protocol so the tool works standalone, without a browser or GTM.
- Generate a batch of simulated "users" per run, with realistic drop-off between steps (not every fake user completes the funnel).
- Support the two test-case scenarios explicitly: device switch (TC1) and expired-link re-request (TC2).
- Produce zero PII. All identifiers and property values are fake and generated locally.
- Be runnable with a single command and a small set of flags.

## 3. Non-Goals

- No real GTM, dataLayer, or browser involved. All "client-side" events are also sent via Measurement Protocol for simplicity; the tool should log clearly that this is a simulation shortcut, not a stand-in for real GTM validation.
- No UI. CLI only.
- No integration with Conversive's actual signup form or infrastructure.
- No attempt to replicate GA4's `_ga` cookie / `client_id` mechanics exactly. The tool generates its own `signup_id` per simulated user and reuses it as the GA4 `client_id` for consistency, matching the real design intent.

## 4. Event Spec (reference)

Same 5 events as the production spec, sent as GA4 Measurement Protocol payloads.

1. `signup_page_viewed`
2. `signup_step1_submitted`
3. `signup_step2_submitted`
4. `signup_verification`
5. `signup_completed`

Shared fields across all 5 events for one simulated signup:
- `signup_id`: UUID v4, generated once per simulated user, reused as `client_id` in every Measurement Protocol call for that user.
- `source_feature`: always `"signup"`.
- `page_url`: a fake hash route appropriate to the step (e.g. `#/signup/step1`).

Step-specific fields (all fake, generated from small fixed pools, not random strings):
- `signup_method`: one of `email`, `google`, `microsoft`.
- `email_domain`: sampled from a fixed list of realistic domains (e.g. `acme.com`, `globex.io`, `initech.co`, `umbrella.net`). Never a full email address.
- `setup_option`: one of `self_setup`, `guided_setup`.
- `data_center`: one of `us`, `eu`, `aus`.
- `account_id`: fake numeric string, generated only at `signup_completed`.

## 5. Functional Requirements

### 5.1 Single-run simulation
Running the tool with no batch flag simulates one signup funnel end to end, with a configurable delay between events (default a few seconds, so events land with realistic spacing in DebugView).

### 5.2 Batch simulation
Running with a `--count N` flag simulates N independent signups in one run. Each gets its own `signup_id` and its own fake profile (method, domain, setup option, data center).

### 5.3 Drop-off modeling
Batch mode should apply a configurable drop-off rate at each step, so not every simulated user reaches `signup_completed`. Suggested default funnel shape:
- 100% reach `signup_page_viewed`
- ~80% reach `signup_step1_submitted`
- ~65% reach `signup_step2_submitted`
- ~55% reach `signup_verification`
- ~45% reach `signup_completed`

These percentages should be flags or a config block, not hardcoded, so the funnel shape can be tuned between runs.

### 5.4 TC1: device switch scenario
A `--scenario device-switch` flag simulates the case where steps 1 to 3 happen in one session and verification and completion happen in a separate session (different `client_id` context on the GA4 side, but the same `signup_id` value carried through). Purpose is to confirm the funnel still resolves as one journey.

### 5.5 TC2: expired link, re-request scenario
A `--scenario re-request` flag simulates a user who submits signup, then re-requests the verification email, then completes. The key assertion: `signup_id` must stay the same across the re-request, only one `signup_verification` and one `signup_completed` fire, and they reference the original `signup_id`, not a new one.

### 5.6 No PII enforcement
Add a simple validation step before sending: reject any payload where a property value looks like a full email address or a name (basic regex check for `@` in a non-`email_domain` field is enough). This is a safety net, not a compliance feature.

### 5.7 Logging
Every event sent should be logged to stdout with timestamp, `signup_id`, event name, and key params, plus the Measurement Protocol response code. A `--dry-run` flag should print payloads without sending them.

## 6. Configuration

Environment variables (via `.env`, not committed):
- `GA4_MEASUREMENT_ID`: your personal practice property's Measurement ID (`G-XXXXXXX`).
- `GA4_API_SECRET`: Measurement Protocol API secret for that property.

CLI flags:
- `--count <n>`: number of simulated funnels (default 1).
- `--scenario <normal|device-switch|re-request>` (default `normal`).
- `--delay <seconds>`: delay between events within one funnel (default 3).
- `--dry-run`: print payloads, do not send.
- `--drop-off <config path or inline>`: override default drop-off rates.

## 7. Technical Notes for Implementation

- Use the GA4 Measurement Protocol endpoint (`https://www.google-analytics.com/mp/collect`) with `measurement_id` and `api_secret` as query params, and `client_id` plus `events` array in the POST body, per the same shape shown in the production spec's event 4 example.
- Use the `debug` endpoint (`https://www.google-analytics.com/debug/mp/collect`) as an option behind a `--validate` flag, to get Google's payload validation response instead of actually sending, useful when first setting the tool up.
- Fake data pools (domains, setup options, data centers) should live in a small config file so they are easy to extend later.
- Keep the whole thing to a single script or a small handful of files. This does not need a framework.

## 8. Success Criteria

- Running the tool once produces all 5 events in GA4 DebugView, all sharing one `signup_id`.
- Running in batch mode produces a funnel in GA4 Explorations that shows realistic drop-off across the 5 steps.
- The device-switch and re-request scenarios each produce exactly one complete, unbroken funnel per simulated user, not two partial ones.
- No event parameter ever contains a full email address or name.

## 9. Out of Scope

- Any connection to Conversive's real signup flow, GTM container, or production GA4 property.
- Realistic timing distributions beyond a simple fixed or randomized delay.
- A UI or dashboard. Terminal output and GA4 itself are the only interfaces.
