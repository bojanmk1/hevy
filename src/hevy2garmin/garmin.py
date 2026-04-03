"""Garmin Connect upload — FIT files, activity renaming, descriptions.

Uses garmin-auth for authentication.
"""

from __future__ import annotations

import io
import logging
import time
from pathlib import Path

from garminconnect import Garmin
from garmin_auth import GarminAuth, RateLimiter

logger = logging.getLogger("hevy2garmin")

_limiter = RateLimiter(delay=1.0, max_retries=3, base_wait=30)


def get_client(
    email: str | None = None,
    password: str | None = None,
    token_dir: str = "~/.garminconnect",
) -> Garmin:
    """Get an authenticated Garmin client via garmin-auth."""
    auth = GarminAuth(email=email, password=password, token_dir=token_dir)
    return auth.login()


def upload_fit(client: Garmin, fit_path: str | Path) -> dict:
    """Upload a FIT file to Garmin Connect.

    Returns dict with upload_id and activity_id (if found).
    """
    fit_path = Path(fit_path)
    if not fit_path.exists():
        raise FileNotFoundError(f"FIT file not found: {fit_path}")

    resp = _limiter.call(client.upload_activity, str(fit_path))
    upload_id = None
    activity_id = None

    if isinstance(resp, dict):
        upload_id = resp.get("detailedImportResult", {}).get("uploadId")

    # Wait for Garmin to process, then find the activity
    if upload_id:
        logger.info("  Upload accepted (uploadId=%s), waiting for processing...", upload_id)
        time.sleep(8)
        try:
            activities = _limiter.call(client.get_activities, 0, 5)
            if activities:
                activity_id = activities[0].get("activityId")
                logger.info("  Found activity %s", activity_id)
        except Exception as e:
            logger.warning("  Could not find uploaded activity: %s", e)

    return {"upload_id": upload_id, "activity_id": activity_id}


def rename_activity(client: Garmin, activity_id: int, name: str) -> None:
    """Rename a Garmin activity."""
    _limiter.call(client.set_activity_name, activity_id, name)
    logger.info("  Renamed activity %s to '%s'", activity_id, name)


def set_description(client: Garmin, activity_id: int, description: str) -> None:
    """Set description for a Garmin activity."""
    url = f"/activity-service/activity/{activity_id}"
    payload = {"activityId": activity_id, "description": description}
    client.garth.put("connectapi", url, json=payload, api=True)
    time.sleep(1.0)
    logger.info("  Description set (%d chars)", len(description))


def upload_image(client: Garmin, activity_id: int, image_bytes: bytes, filename: str = "image.png") -> None:
    """Upload an image to a Garmin activity."""
    files = {"file": (filename, io.BytesIO(image_bytes))}
    client.garth.post(
        "connectapi",
        f"activity-service/activity/{activity_id}/image",
        files=files,
        api=True,
    )
    time.sleep(1.0)
    logger.info("  Image uploaded (%dKB)", len(image_bytes) // 1024)


def generate_description(workout: dict, calories: int | None = None, avg_hr: int | None = None) -> str:
    """Generate a text description for a gym workout."""
    lines: list[str] = []
    title = workout.get("title", "Workout")
    duration_s = 0

    start = workout.get("start_time") or workout.get("startTime", "")
    end = workout.get("end_time") or workout.get("endTime", "")
    if start and end:
        from datetime import datetime
        try:
            fmt = "%Y-%m-%dT%H:%M:%S%z" if "T" in start else "%Y-%m-%d %H:%M:%S"
            t0 = datetime.fromisoformat(start.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(end.replace("Z", "+00:00"))
            duration_s = int((t1 - t0).total_seconds())
        except Exception:
            pass

    lines.append(f"🏋️ {title}")
    if duration_s > 0:
        m = duration_s // 60
        lines.append(f"⏱️ {m} min")
    if calories:
        lines.append(f"🔥 {calories} kcal")
    if avg_hr:
        lines.append(f"❤️ avg {avg_hr} bpm")

    exercises = workout.get("exercises", [])
    if exercises:
        lines.append("")
        for ex in exercises:
            name = ex.get("title") or ex.get("name", "Unknown")
            sets = [s for s in ex.get("sets", []) if s.get("type") == "normal"]
            if sets:
                weights = [s.get("weight_kg") or s.get("weight", 0) for s in sets]
                reps = [s.get("reps", 0) for s in sets]
                top_weight = max(weights) if weights else 0
                top_reps = max(reps) if reps else 0
                lines.append(f"• {name}: {len(sets)} sets · {top_weight:.1f}kg × {top_reps}")

    lines.append("\n— synced by hevy2garmin")
    return "\n".join(lines)
