"""CLI for hevy2garmin."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from hevy2garmin import db
from hevy2garmin.sync import sync


def cmd_sync(args: argparse.Namespace) -> None:
    """Sync Hevy workouts to Garmin."""
    result = sync(
        hevy_api_key=args.hevy_api_key,
        garmin_email=args.garmin_email,
        garmin_password=args.garmin_password,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    print(f"\n✓ Sync complete: {result['synced']} synced, {result['skipped']} skipped, {result['failed']} failed")
    if result["failed"] > 0:
        sys.exit(1)


def cmd_status(args: argparse.Namespace) -> None:
    """Show sync status."""
    count = db.get_synced_count()
    recent = db.get_recent_synced(5)
    print(f"Total synced: {count}")
    if recent:
        print("\nRecent:")
        for r in recent:
            print(f"  {r['synced_at']} | {r['title']} → garmin:{r['garmin_activity_id'] or '?'}")
    else:
        print("No workouts synced yet. Run: hevy2garmin sync")


def cmd_list(args: argparse.Namespace) -> None:
    """List recent Hevy workouts."""
    from hevy2garmin.hevy import HevyClient
    hevy = HevyClient(api_key=args.hevy_api_key)
    data = hevy.get_workouts(page=1, page_size=args.limit or 10)
    for w in data.get("workouts", []):
        synced = "✓" if db.is_synced(w["id"]) else " "
        exercises = len(w.get("exercises", []))
        start = w.get("start_time", "")[:16]
        print(f"  [{synced}] {start} | {w['title']} ({exercises} exercises)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hevy2garmin",
        description="Sync Hevy gym workouts to Garmin Connect",
    )
    parser.add_argument("--hevy-api-key", help="Hevy API key (or HEVY_API_KEY env var)")
    parser.add_argument("--garmin-email", help="Garmin email (or GARMIN_EMAIL env var)")
    parser.add_argument("--garmin-password", help="Garmin password (or GARMIN_PASSWORD env var)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress logging")

    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", help="Sync workouts to Garmin")
    sync_parser.add_argument("-n", "--limit", type=int, help="Max workouts to sync")
    sync_parser.add_argument("--dry-run", action="store_true", help="Generate FIT files without uploading")

    subparsers.add_parser("status", help="Show sync status")

    list_parser = subparsers.add_parser("list", help="List recent Hevy workouts")
    list_parser.add_argument("-n", "--limit", type=int, default=10, help="Number of workouts to show")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    level = logging.DEBUG if args.verbose else (logging.CRITICAL if args.quiet else logging.INFO)
    logging.basicConfig(format="%(message)s", level=level)

    try:
        commands = {"sync": cmd_sync, "status": cmd_status, "list": cmd_list}
        commands[args.command](args)
    except RuntimeError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
