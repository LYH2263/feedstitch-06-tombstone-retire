from __future__ import annotations

import json
import sqlite3
from typing import Any


def list_items(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, business_key, title, price, category, source_id,
               event_ts, source_revision, payload_json, updated_at
        FROM canonical_items ORDER BY business_key
        """
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d.pop("payload_json"))
        out.append(d)
    return out


def get_by_key(conn: sqlite3.Connection, business_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, business_key, title, price, category, source_id,
               event_ts, source_revision, payload_json, updated_at
        FROM canonical_items WHERE business_key = ?
        """,
        (business_key,),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["payload"] = json.loads(d.pop("payload_json"))
    return d


def upsert_item(conn: sqlite3.Connection, item: dict[str, Any], source_id: int) -> None:
    conn.execute(
        """
        INSERT INTO canonical_items(
            business_key, title, price, category, source_id,
            event_ts, source_revision, payload_json, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,datetime('now'))
        ON CONFLICT(business_key) DO UPDATE SET
            title=excluded.title,
            price=excluded.price,
            category=excluded.category,
            source_id=excluded.source_id,
            event_ts=excluded.event_ts,
            source_revision=excluded.source_revision,
            payload_json=excluded.payload_json,
            updated_at=datetime('now')
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
        ),
    )


def count_items(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) c FROM canonical_items").fetchone()["c"])
