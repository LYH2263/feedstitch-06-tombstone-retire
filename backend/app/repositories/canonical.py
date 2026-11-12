from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.modules.tombstone_retire import ALIVE, RETIRED

_SELECT_COLUMNS = """
    id, business_key, title, price, category, source_id,
    event_ts, source_revision, payload_json, updated_at,
    status, retired_at, retired_by_run_id, retired_by_source_id
"""


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["payload"] = json.loads(d.pop("payload_json"))
    return d


def list_items(
    conn: sqlite3.Connection,
    status: str | None = ALIVE,
) -> list[dict[str, Any]]:
    """Canonical view. Defaults to the *alive* view: retired business keys are
    kept in the table but not presented as in-sale/valid items. Pass
    ``status='retired'`` for the retirement list or ``None``/``'all'`` for
    every row."""
    if status in (None, "all"):
        rows = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM canonical_items ORDER BY business_key"
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM canonical_items WHERE status = ? "
            "ORDER BY business_key",
            (status,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_by_key(conn: sqlite3.Connection, business_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"SELECT {_SELECT_COLUMNS} FROM canonical_items WHERE business_key = ?",
        (business_key,),
    ).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def upsert_item(conn: sqlite3.Connection, item: dict[str, Any], source_id: int) -> None:
    """Insert or update an alive canonical row. Also used for revives: a
    revived key is restored to the alive view with its new payload."""
    conn.execute(
        """
        INSERT INTO canonical_items(
            business_key, title, price, category, source_id,
            event_ts, source_revision, payload_json, updated_at, status
        ) VALUES (?,?,?,?,?,?,?,?,datetime('now'), ?)
        ON CONFLICT(business_key) DO UPDATE SET
            title=excluded.title,
            price=excluded.price,
            category=excluded.category,
            source_id=excluded.source_id,
            event_ts=excluded.event_ts,
            source_revision=excluded.source_revision,
            payload_json=excluded.payload_json,
            updated_at=datetime('now'),
            status=?,
            retired_at=NULL,
            retired_by_run_id=NULL,
            retired_by_source_id=NULL
        """,
        (
            item["business_key"],
            item["title"],
            item["price"],
            item["category"],
            source_id,
            item["event_ts"],
            item["source_revision"],
            json.dumps(item["payload"], ensure_ascii=False),
            ALIVE,
            ALIVE,
        ),
    )


def retire_item(
    conn: sqlite3.Connection,
    *,
    business_key: str,
    event_ts: str,
    source_revision: int,
    run_id: int,
    source_id: int,
) -> None:
    """Soft-delete: flip an alive row to retired without erasing its last
    known payload. Retirement metadata is only written on an actual state
    transition, so duplicate tombstones never overwrite it."""
    conn.execute(
        """
        UPDATE canonical_items
        SET status = ?,
            retired_at = ?,
            retired_by_run_id = ?,
            retired_by_source_id = ?,
            event_ts = ?,
            source_revision = ?,
            updated_at = datetime('now')
        WHERE business_key = ? AND status = ?
        """,
        (RETIRED, event_ts, run_id, source_id, event_ts, source_revision, business_key, ALIVE),
    )


def count_items(conn: sqlite3.Connection, status: str | None = ALIVE) -> int:
    """Single source of truth for canonical counts used by both the list
    pages and run reports."""
    if status in (None, "all"):
        row = conn.execute("SELECT COUNT(*) c FROM canonical_items").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) c FROM canonical_items WHERE status = ?", (status,)
        ).fetchone()
    return int(row["c"])


def count_alive(conn: sqlite3.Connection) -> int:
    return count_items(conn, ALIVE)


def count_retired(conn: sqlite3.Connection) -> int:
    return count_items(conn, RETIRED)
