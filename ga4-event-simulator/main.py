import argparse

import config
from ga4_client import GA4Client
from scenarios import run_device_switch, run_normal, run_re_request
from timing import validate_backdate


def parse_args():
    parser = argparse.ArgumentParser(description="GA4 signup funnel simulator")
    parser.add_argument("--count", type=int, default=1, help="number of simulated funnels")
    parser.add_argument(
        "--scenario",
        choices=["normal", "device-switch", "re-request"],
        default="normal",
    )
    parser.add_argument("--delay", type=float, default=3, help="seconds between events within one funnel")
    parser.add_argument("--dry-run", action="store_true", help="print payloads, do not send")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="send to GA4's debug endpoint for payload validation instead of the real endpoint",
    )
    parser.add_argument(
        "--drop-off",
        default=None,
        help="inline JSON or path to a JSON file overriding default drop-off rates (normal scenario only)",
    )
    parser.add_argument(
        "--debug-client-id",
        default=None,
        help=(
            "reuse this fixed client_id for every event in this run instead of a fresh one per user. "
            "GA4 DebugView only surfaces a client_id once it has prior data, so a brand-new random "
            "client_id often shows nothing in DebugView even though the event was recorded fine "
            "(visible in Realtime/reports). Send a few runs with the same --debug-client-id to get "
            "DebugView working. Debugging aid only — do not use for realistic batch generation."
        ),
    )
    parser.add_argument(
        "--days-ago",
        type=int,
        default=0,
        help="backdate signup_page_viewed/step1/step2 to N days ago instead of now (GA4 allows up to ~3 days total).",
    )
    parser.add_argument(
        "--completion-gap-hours",
        type=float,
        default=0,
        help="additionally push signup_verification/signup_completed forward by N hours from --days-ago, "
        "to simulate confirmation happening some time after signup (e.g. 24 for 'confirms next day').",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    validate_backdate(args.days_ago, args.completion_gap_hours)

    # validate always hits the debug endpoint (even under --dry-run), so it
    # needs credentials too; a pure --dry-run with no --validate needs none.
    if not (args.dry_run and not args.validate):
        config.require_credentials()

    client = GA4Client(
        measurement_id=config.GA4_MEASUREMENT_ID,
        api_secret=config.GA4_API_SECRET,
        dry_run=args.dry_run,
        validate=args.validate,
    )

    if args.debug_client_id:
        print(f"Note: --debug-client-id set, all events in this run will use client_id={args.debug_client_id}.")

    if args.days_ago or args.completion_gap_hours:
        print(
            f"Note: backdating enabled — page_viewed/step1/step2 at {args.days_ago} day(s) ago, "
            f"verification/completed {args.completion_gap_hours}h after that."
        )

    if args.scenario == "normal":
        dropoff_cfg = config.parse_dropoff_override(args.drop_off)
        run_normal(
            args.count, args.delay, dropoff_cfg, client, args.debug_client_id, args.days_ago, args.completion_gap_hours
        )
    elif args.scenario == "device-switch":
        if args.drop_off:
            print("Note: --drop-off is ignored for the device-switch scenario (always completes).")
        if args.debug_client_id:
            print(
                "Note: --debug-client-id also collapses session A and session B onto the same "
                "client_id, which defeats the point of this scenario's normal client_id-switch check. "
                "Use it only to troubleshoot DebugView visibility, not to validate TC1 behavior."
            )
        run_device_switch(
            args.count, args.delay, client, args.debug_client_id, args.days_ago, args.completion_gap_hours
        )
    elif args.scenario == "re-request":
        if args.drop_off:
            print("Note: --drop-off is ignored for the re-request scenario (always completes).")
        run_re_request(
            args.count, args.delay, client, args.debug_client_id, args.days_ago, args.completion_gap_hours
        )


if __name__ == "__main__":
    main()
