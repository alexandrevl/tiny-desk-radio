"""SQLite record of every episode the tool has looked at."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

OK, REVIEW, SKIPPED = "ok", "review", "skipped"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    video_id TEXT PRIMARY KEY,
    artist TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT,
    setlist_count INTEGER,
    detected_count INTEGER,
    files TEXT NOT NULL DEFAULT '[]',
    delivered INTEGER NOT NULL DEFAULT 0
)
"""


@dataclass(frozen=True)
class Row:
    video_id: str
    artist: str | None
    title: str
    status: str
    reason: str | None
    setlist_count: int | None
    detected_count: int | None
    files: list[str]
    delivered: bool


class State:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.execute(_SCHEMA)

    def get(self, video_id: str) -> Row | None:
        row = self._db.execute("SELECT * FROM episodes WHERE video_id = ?", (video_id,)).fetchone()
        return _row(row) if row else None

    def all(self) -> list[Row]:
        return [_row(r) for r in self._db.execute("SELECT * FROM episodes ORDER BY artist, video_id")]

    def save(
        self,
        video_id: str,
        title: str,
        status: str,
        *,
        artist: str | None = None,
        reason: str | None = None,
        setlist_count: int | None = None,
        detected_count: int | None = None,
        files: list[str] = (),
    ) -> None:
        """Insert or replace the episode's result; a fresh result is never delivered yet."""
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO episodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
                (video_id, artist, title, status, reason, setlist_count, detected_count, json.dumps(list(files))),
            )

    def mark_delivered(self, video_id: str) -> None:
        with self._db:
            self._db.execute("UPDATE episodes SET delivered = 1 WHERE video_id = ?", (video_id,))


def _row(row: sqlite3.Row) -> Row:
    return Row(
        video_id=row["video_id"],
        artist=row["artist"],
        title=row["title"],
        status=row["status"],
        reason=row["reason"],
        setlist_count=row["setlist_count"],
        detected_count=row["detected_count"],
        files=json.loads(row["files"]),
        delivered=bool(row["delivered"]),
    )
