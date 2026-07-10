import random
import time

import config
from events import EVENT_SEQUENCE, build_event
from identity import generate_account_id, generate_profile, new_id
from timing import event_timestamp_micros

# Events considered part of the "confirmation" side of the funnel, which
# --completion-gap-hours pushes forward in time relative to --days-ago.
POST_GAP_EVENTS = {"signup_verification", "signup_completed"}


def _timestamp_for(name, days_ago, completion_gap_hours):
    gap = completion_gap_hours if name in POST_GAP_EVENTS else 0
    return event_timestamp_micros(days_ago, gap)


def compute_conditional_rates(dropoff_cfg):
    """Converts cumulative reach percentages into per-step continue
    probabilities, each conditional on having reached the prior step."""
    rates = {}
    prev = 100
    for name in EVENT_SEQUENCE:
        cum = dropoff_cfg[name]
        rates[name] = 0 if prev == 0 else cum / prev
        prev = cum
    return rates


def run_normal(count, delay, dropoff_cfg, client, debug_client_id=None, days_ago=0, completion_gap_hours=0):
    pools = config.DATA_POOLS
    # A single default run always completes the full funnel (PRD success
    # criteria: "running the tool once produces all 5 events"). Drop-off
    # only applies once actually batching multiple users.
    if count > 1:
        rates = compute_conditional_rates(dropoff_cfg)
    else:
        rates = {name: 1.0 for name in EVENT_SEQUENCE}
    completed = 0

    for _ in range(count):
        signup_id = new_id()
        client_id = debug_client_id or signup_id
        profile = generate_profile(pools)
        reached_completed = False

        for name in EVENT_SEQUENCE:
            if random.random() > rates[name]:
                print(f"    user {signup_id} dropped off before {name}")
                break

            account_id = None
            if name == "signup_completed":
                account_id = generate_account_id()
                reached_completed = True

            event = build_event(name, signup_id, profile, account_id)
            ts = _timestamp_for(name, days_ago, completion_gap_hours)
            client.send(client_id, event, timestamp_micros=ts)
            time.sleep(delay)

        if reached_completed:
            completed += 1

    print(f"Batch complete: {completed}/{count} reached signup_completed")


def run_device_switch(count, delay, client, debug_client_id=None, days_ago=0, completion_gap_hours=0):
    pools = config.DATA_POOLS

    for _ in range(count):
        signup_id = new_id()
        profile = generate_profile(pools)
        client_id_a = debug_client_id or new_id()
        client_id_b = debug_client_id or new_id()

        print(f"--- device-switch user {signup_id}: session A, client_id={client_id_a} ---")
        for name in EVENT_SEQUENCE[:3]:
            event = build_event(name, signup_id, profile)
            ts = _timestamp_for(name, days_ago, completion_gap_hours)
            client.send(client_id_a, event, timestamp_micros=ts)
            time.sleep(delay)

        print(
            f"--- device-switch user {signup_id}: switching device, "
            f"new session client_id={client_id_b} (extra delay simulates the gap) ---"
        )
        time.sleep(delay * 2)

        for name in EVENT_SEQUENCE[3:]:
            account_id = generate_account_id() if name == "signup_completed" else None
            event = build_event(name, signup_id, profile, account_id)
            ts = _timestamp_for(name, days_ago, completion_gap_hours)
            client.send(client_id_b, event, timestamp_micros=ts)
            time.sleep(delay)


def run_re_request(count, delay, client, debug_client_id=None, days_ago=0, completion_gap_hours=0):
    pools = config.DATA_POOLS

    for _ in range(count):
        signup_id = new_id()
        client_id = debug_client_id or signup_id
        profile = generate_profile(pools)

        for name in ["signup_page_viewed", "signup_step1_submitted", "signup_step2_submitted"]:
            event = build_event(name, signup_id, profile)
            ts = _timestamp_for(name, days_ago, completion_gap_hours)
            client.send(client_id, event, timestamp_micros=ts)
            time.sleep(delay)

        print(f"    [re-request] user {signup_id} re-requested the verification email (no event fired)")
        time.sleep(delay)

        event = build_event("signup_verification", signup_id, profile)
        ts = _timestamp_for("signup_verification", days_ago, completion_gap_hours)
        client.send(client_id, event, timestamp_micros=ts)
        time.sleep(delay)

        account_id = generate_account_id()
        event = build_event("signup_completed", signup_id, profile, account_id)
        ts = _timestamp_for("signup_completed", days_ago, completion_gap_hours)
        client.send(client_id, event, timestamp_micros=ts)
