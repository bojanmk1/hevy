"""PostgreSQL implementation of the Database interface."""

from __future__ import annotations

import json

from hevy2garmin.db_interface import Database


class PostgresDatabase(Database):
    """Postgres-backed storage for tracking synced workouts."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._ensure_tables()

    def _get_conn(self):
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
        return conn

    def _ensure_tables(self) -> None:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS synced_workouts (
                hevy_id TEXT PRIMARY KEY,
                garmin_activity_id TEXT,
                title TEXT,
                synced_at TIMESTAMPTZ DEFAULT NOW(),
                calories INTEGER,
                avg_hr INTEGER,
                status VARCHAR(20) DEFAULT 'success'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id BIGSERIAL PRIMARY KEY,
                time TIMESTAMPTZ DEFAULT NOW(),
                synced INTEGER DEFAULT 0,
                skipped INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                trigger VARCHAR(50) DEFAULT 'manual'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hr_cache (
                hevy_id TEXT PRIMARY KEY,
                data JSONB NOT NULL,
                cached_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_credentials (
                platform VARCHAR(50) PRIMARY KEY,
                auth_type VARCHAR(20) NOT NULL DEFAULT 'oauth',
                credentials JSONB NOT NULL DEFAULT '{}',
                connected_at TIMESTAMPTZ,
                expires_at TIMESTAMPTZ,
                status VARCHAR(20) DEFAULT 'disconnected'
            )
        """)
        conn.commit()
        cur.close()
        conn.close()

    def is_synced(self, hevy_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM synced_workouts WHERE hevy_id = %s", (hevy_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row is not None

    def get_garmin_id(self, hevy_id: str) -> str | None:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT garmin_activity_id FROM synced_workouts WHERE hevy_id = %s",
            (hevy_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row["garmin_activity_id"] if row else None

    def mark_synced(
        self,
        hevy_id: str,
        garmin_activity_id: str | None = None,
        title: str = "",
        calories: int | None = None,
        avg_hr: int | None = None,
    ) -> None:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO synced_workouts (hevy_id, garmin_activity_id, title, calories, avg_hr)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (hevy_id) DO UPDATE SET
                garmin_activity_id = EXCLUDED.garmin_activity_id,
                title = EXCLUDED.title,
                calories = EXCLUDED.calories,
                avg_hr = EXCLUDED.avg_hr,
                synced_at = NOW()
            """,
            (hevy_id, garmin_activity_id, title, calories, avg_hr),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_synced_count(self) -> int:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM synced_workouts")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row["cnt"]

    def get_recent_synced(self, limit: int = 10) -> list[dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM synced_workouts ORDER BY synced_at DESC LIMIT %s", (limit,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]

    def record_sync_log(
        self,
        synced: int = 0,
        skipped: int = 0,
        failed: int = 0,
        trigger: str = "manual",
    ) -> None:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sync_log (synced, skipped, failed, trigger) VALUES (%s, %s, %s, %s)",
            (synced, skipped, failed, trigger),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_sync_log(self, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]

    def get_cached_hr(self, hevy_id: str) -> dict | None:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT data FROM hr_cache WHERE hevy_id = %s", (hevy_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            data = row["data"]
            # JSONB is auto-deserialized by psycopg2, but handle string fallback
            if isinstance(data, str):
                return json.loads(data)
            return data
        return None

    def cache_hr(self, hevy_id: str, data: dict) -> None:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO hr_cache (hevy_id, data) VALUES (%s, %s)
            ON CONFLICT (hevy_id) DO UPDATE SET
                data = EXCLUDED.data,
                cached_at = NOW()
            """,
            (hevy_id, json.dumps(data)),
        )
        conn.commit()
        cur.close()
        conn.close()
