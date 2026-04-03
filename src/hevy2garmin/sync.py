"""Sync orchestrator — pulls Hevy workouts, generates FIT files, uploads to Garmin."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from hevy2garmin import db
from hevy2garmin.fit import generate_fit
from hevy2garmin.garmin import (
    generate_description,
    get_client,
    rename_activity,
    set_description,
    upload_fit,
)
from hevy2garmin.hevy import HevyClient

logger = logging.getLogger("hevy2garmin")


def sync(
    hevy_api_key: str | None = None,
    garmin_email: str | None = None,
    garmin_password: str | None = None,
    garmin_token_dir: str = "~/.garminconnect",
    limit: int | None = None,
    dry_run: bool = False,
    skip_existing: bool = True,
) -> dict:
    """Sync Hevy workouts to Garmin Connect.

    Args:
        hevy_api_key: Hevy API key (or HEVY_API_KEY env var).
        garmin_email: Garmin email (or GARMIN_EMAIL env var).
        garmin_password: Garmin password (or GARMIN_PASSWORD env var).
        garmin_token_dir: Directory for Garmin token storage.
        limit: Max workouts to sync (None = all new).
        dry_run: Generate FIT files but don't upload.
        skip_existing: Skip workouts already synced.

    Returns:
        Dict with sync stats: synced, skipped, failed, total.
    """
    hevy = HevyClient(api_key=hevy_api_key)
    total = hevy.get_workout_count()
    logger.info("Hevy reports %d total workouts", total)

    # Fetch recent workouts (page 1 has newest)
    page_size = limit or 10
    data = hevy.get_workouts(page=1, page_size=min(page_size, 50))
    workouts = data.get("workouts", [])

    if limit:
        workouts = workouts[:limit]

    garmin_client = None
    if not dry_run:
        logger.info("Authenticating with Garmin Connect...")
        garmin_client = get_client(garmin_email, garmin_password, garmin_token_dir)
        logger.info("Authenticated successfully")

    stats = {"synced": 0, "skipped": 0, "failed": 0, "total": len(workouts)}

    for workout in workouts:
        wid = workout.get("id", "unknown")
        title = workout.get("title", "Workout")

        if skip_existing and db.is_synced(wid):
            logger.debug("Skipping %s (%s) — already synced", wid, title)
            stats["skipped"] += 1
            continue

        logger.info("Syncing: %s (%s)", title, wid)

        try:
            # Generate FIT file
            with tempfile.TemporaryDirectory() as tmp:
                fit_path = str(Path(tmp) / f"{wid}.fit")
                result = generate_fit(workout, hr_samples=None, output_path=fit_path)
                logger.info(
                    "  FIT: %d exercises, %d sets, %d cal",
                    result["exercises"], result["total_sets"], result["calories"],
                )

                if dry_run:
                    logger.info("  [DRY RUN] Would upload %s", fit_path)
                    stats["synced"] += 1
                    continue

                # Upload to Garmin
                upload_result = upload_fit(garmin_client, fit_path)
                activity_id = upload_result.get("activity_id")

                if activity_id:
                    rename_activity(garmin_client, activity_id, title)
                    desc = generate_description(
                        workout,
                        calories=result.get("calories"),
                        avg_hr=result.get("avg_hr"),
                    )
                    set_description(garmin_client, activity_id, desc)

                db.mark_synced(
                    hevy_id=wid,
                    garmin_activity_id=str(activity_id) if activity_id else None,
                    title=title,
                    calories=result.get("calories"),
                    avg_hr=result.get("avg_hr"),
                )
                stats["synced"] += 1
                logger.info("  ✓ Synced → Garmin activity %s", activity_id)

        except Exception as e:
            logger.error("  ✗ Failed to sync %s: %s", wid, e)
            stats["failed"] += 1

    return stats
