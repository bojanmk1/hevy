"""SQLite storage for tracking synced workouts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("~/.hevy2garmin/sync.db").expanduser()


def _get_conn(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS synced_workouts (
            hevy_id TEXT PRIMARY KEY,
            garmin_activity_id TEXT,
            title TEXT,
            synced_at TEXT DEFAULT (datetime('now')),
            calories INTEGER,
            avg_hr INTEGER,
            status TEXT DEFAULT 'success'
        )
    """)
    conn.commit()
    return conn


def is_synced(hevy_id: str, db_path: Path = DEFAULT_DB_PATH) -> bool:
    """Check if a Hevy workout has already been synced."""
    conn = _get_conn(db_path)
    row = conn.execute("SELECT 1 FROM synced_workouts WHERE hevy_id = ?", (hevy_id,)).fetchone()
    conn.close()
    return row is not None


def mark_synced(
    hevy_id: str,
    garmin_activity_id: str | None = None,
    title: str = "",
    calories: int | None = None,
    avg_hr: int | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Record a successfully synced workout."""
    conn = _get_conn(db_path)
    conn.execute(
        """
        INSERT OR REPLACE INTO synced_workouts (hevy_id, garmin_activity_id, title, calories, avg_hr)
        VALUES (?, ?, ?, ?, ?)
        """,
        (hevy_id, garmin_activity_id, title, calories, avg_hr),
    )
    conn.commit()
    conn.close()


def get_synced_count(db_path: Path = DEFAULT_DB_PATH) -> int:
    """Get total number of synced workouts."""
    conn = _get_conn(db_path)
    count = conn.execute("SELECT COUNT(*) FROM synced_workouts").fetchone()[0]
    conn.close()
    return count


def get_recent_synced(limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Get recently synced workouts."""
    conn = _get_conn(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM synced_workouts ORDER BY synced_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
