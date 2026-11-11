from __future__ import annotations

import sqlite3
from typing import Any


def list_sources(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, name, format, fixture_path, watermark_ts, lookback_seconds, enabled, note
        FROM sources ORDER BY id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_source(conn: sqlite3.Connection, source_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, name, format, fixture_path, watermark_ts, lookback_seconds, enabled, note
        FROM sources WHERE id = ?
        """,
        (source_id,),
    ).fetchone()
    return dict(row) if row else None


def set_watermark(conn: sqlite3.Connection, source_id: int, watermark_ts: str | None) -> None:
    conn.execute("UPDATE sources SET watermark_ts = ? WHERE id = ?", (watermark_ts, source_id))


def update_lookback(conn: sqlite3.Connection, source_id: int, lookback_seconds: int) -> None:
    conn.execute(
        "UPDATE sources SET lookback_seconds = ? WHERE id = ?",
        (lookback_seconds, source_id),
    )
