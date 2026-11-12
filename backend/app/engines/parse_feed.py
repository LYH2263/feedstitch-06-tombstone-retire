"""Parse local fixture feeds into normalized staging records.

Tombstone / retire events are recognized two ways:

1. in-band markers on a row: a truthy ``tombstone`` / ``retired`` /
   ``is_deleted`` / ``deleted`` field, or a ``status`` / ``event_type``
   field whose value denotes retirement (tombstone / retired / delete ...).
2. a source-level marker: when a source is flagged as a tombstone source,
   every row it emits is treated as a tombstone.

Tombstone rows only need to identify the business key and its event position
(business_key / event_ts / source_revision); descriptive fields are optional.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = ("business_key", "title", "price", "category", "event_ts", "source_revision")
TOMBSTONE_KEY_FIELDS = ("business_key", "event_ts", "source_revision")

TOMBSTONE_BOOL_FIELDS = ("tombstone", "retired", "is_deleted", "deleted")
TOMBSTONE_VALUE_FIELDS = ("status", "event_type", "op", "operation")
TOMBSTONE_VALUE_TOKENS = {
    "tombstone",
    "retire",
    "retired",
    "delete",
    "deleted",
    "soft_delete",
    "soft-delete",
    "remove",
}
TRUE_TOKENS = {"true", "1", "yes", "y"}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in TRUE_TOKENS


def detect_tombstone(raw: dict[str, Any]) -> bool:
    """Inspect a raw feed row for an in-band retirement marker."""
    for field in TOMBSTONE_BOOL_FIELDS:
        if field in raw and raw[field] is not None and _as_bool(raw[field]):
            return True
    for field in TOMBSTONE_VALUE_FIELDS:
        value = raw.get(field)
        if value is not None and str(value).strip().lower() in TOMBSTONE_VALUE_TOKENS:
            return True
    return False


def _normalize_item(raw: dict[str, Any], force_tombstone: bool = False) -> dict[str, Any]:
    is_tombstone = force_tombstone or detect_tombstone(raw)
    required = TOMBSTONE_KEY_FIELDS if is_tombstone else REQUIRED_FIELDS
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")

    business_key = str(raw["business_key"]).strip()
    event_ts = str(raw["event_ts"]).strip()
    source_revision = int(raw["source_revision"])

    if is_tombstone:
        # Descriptive columns are NOT NULL in canonical_items; a tombstone only
        # identifies the key, so keep whatever the feed offered (or blanks).
        title = str(raw.get("title") or "").strip()
        price = float(raw["price"]) if raw.get("price") is not None else 0.0
        category = str(raw.get("category") or "").strip()
    else:
        title = str(raw["title"]).strip()
        price = float(raw["price"])
        category = str(raw["category"]).strip()

    payload: dict[str, Any] = {
        "business_key": business_key,
        "title": title,
        "price": price,
        "category": category,
        "event_ts": event_ts,
        "source_revision": source_revision,
    }
    if is_tombstone:
        payload["tombstone"] = True

    return {
        "business_key": business_key,
        "title": title,
        "price": price,
        "category": category,
        "event_ts": event_ts,
        "source_revision": source_revision,
        "is_tombstone": is_tombstone,
        "payload": payload,
    }


def parse_json(path: Path, force_tombstone: bool = False) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("JSON feed must be a list or an object with items[]")
    return [_normalize_item(x, force_tombstone) for x in items]


def parse_jsonl(path: Path, force_tombstone: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            rows.append(_normalize_item(json.loads(text), force_tombstone))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"jsonl line {line_no}: {exc}") from exc
    return rows


def parse_xml(path: Path, force_tombstone: bool = False) -> list[dict[str, Any]]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for node in root.findall(".//item"):
        raw = {child.tag: child.text for child in list(node)}
        rows.append(_normalize_item(raw, force_tombstone))
    return rows


PARSERS = {
    "json": parse_json,
    "jsonl": parse_jsonl,
    "xml": parse_xml,
}


def parse_fixture(path: Path, fmt: str, tombstone_source: bool = False) -> list[dict[str, Any]]:
    parser = PARSERS.get(fmt)
    if parser is None:
        raise ValueError(f"unsupported format: {fmt}")
    if not path.exists():
        raise FileNotFoundError(str(path))
    return parser(path, force_tombstone=tombstone_source)
