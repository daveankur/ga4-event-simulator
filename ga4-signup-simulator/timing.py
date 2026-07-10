import datetime

# GA4 Measurement Protocol silently clamps (or rejects, depending on
# validation_behavior) any timestamp older than 72 hours. Stay under that
# with a safety margin.
MAX_BACKDATE_HOURS = 71


def validate_backdate(days_ago, completion_gap_hours):
    total_hours = days_ago * 24 + completion_gap_hours
    if total_hours > MAX_BACKDATE_HOURS:
        raise SystemExit(
            f"--days-ago {days_ago} ({days_ago * 24}h) plus --completion-gap-hours "
            f"{completion_gap_hours}h totals {total_hours}h, which exceeds Measurement "
            f"Protocol's ~72-hour backdating limit. Keep the combined total under "
            f"{MAX_BACKDATE_HOURS}h."
        )


def event_timestamp_micros(days_ago, gap_hours=0):
    """Returns a GA4 timestamp_micros value, or None for real-time (unbackdated)
    sends. Computed at call time so within a batch, later users/events naturally
    land slightly later too, same as they would without backdating."""
    if days_ago == 0 and gap_hours == 0:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    event_time = now - datetime.timedelta(days=days_ago) + datetime.timedelta(hours=gap_hours)
    return int(event_time.timestamp() * 1_000_000)
