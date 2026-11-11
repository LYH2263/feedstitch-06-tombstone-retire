from __future__ import annotations

import sqlite3
from typing import Any


def get_all(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_value(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def as_list(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [{"key": k, "value": v} for k, v in get_all(conn).items()]
