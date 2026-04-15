"""SQLite persistence for residency observations."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS residency_observations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id     TEXT    NOT NULL,
    observed_at   TEXT    NOT NULL,  -- ISO 8601 UTC
    jurisdiction  TEXT    NOT NULL,  -- US state name or country name
    in_us         INTEGER NOT NULL,  -- 1 = US, 0 = international
    latitude      REAL,
    longitude     REAL,
    gps_accuracy  REAL
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_person_observed
ON residency_observations (person_id, observed_at);
"""


class ResidencyDB:
    def __init__(self, config_dir: str) -> None:
        self._path = Path(config_dir) / "residency_tracker.db"
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(CREATE_TABLE)
        self._conn.execute(CREATE_INDEX)
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def insert_observation(
        self,
        person_id: str,
        observed_at: datetime,
        jurisdiction: str,
        in_us: bool,
        latitude: float | None,
        longitude: float | None,
        gps_accuracy: float | None,
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO residency_observations
                (person_id, observed_at, jurisdiction, in_us, latitude, longitude, gps_accuracy)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                person_id,
                observed_at.isoformat(),
                jurisdiction,
                1 if in_us else 0,
                latitude,
                longitude,
                gps_accuracy,
            ),
        )
        self._conn.commit()

    def get_latest_observation(self, person_id: str) -> "sqlite3.Row | None":
        assert self._conn is not None
        return self._conn.execute(
            """
            SELECT * FROM residency_observations
            WHERE person_id = ?
            ORDER BY observed_at DESC
            LIMIT 1
            """,
            (person_id,),
        ).fetchone()

    def get_days_by_jurisdiction(self, person_id: str, year: int) -> dict:
        """Return {jurisdiction: distinct_days} for the given person and calendar year."""
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT jurisdiction, COUNT(DISTINCT date(observed_at)) AS days
            FROM residency_observations
            WHERE person_id = ?
              AND observed_at >= ? AND observed_at < ?
            GROUP BY jurisdiction
            ORDER BY days DESC
            """,
            (person_id, f"{year}-01-01", f"{year + 1}-01-01"),
        ).fetchall()
        return {row["jurisdiction"]: row["days"] for row in rows}

    def get_observations(
        self,
        person_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[sqlite3.Row]:
        assert self._conn is not None
        query = "SELECT * FROM residency_observations WHERE 1=1"
        params: list = []
        if person_id:
            query += " AND person_id = ?"
            params.append(person_id)
        if start:
            query += " AND observed_at >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND observed_at <= ?"
            params.append(end.isoformat())
        query += " ORDER BY observed_at ASC"
        return self._conn.execute(query, params).fetchall()
