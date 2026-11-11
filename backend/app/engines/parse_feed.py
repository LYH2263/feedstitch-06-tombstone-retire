"""Parse local fixture feeds into normalized staging records."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("business_key", "title", "price", "category", "event_ts", "source_revision")


def _normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in REQUIRED_FIELDS if k not in raw]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    return {
        "business_key": str(raw["business_key"]).strip(),
        "title": str(raw["title"]).strip(),
        "price": float(raw["price"]),
        "category": str(raw["category"]).strip(),
        "event_ts": str(raw["event_ts"]).strip(),
        "source_revision": int(raw["source_revision"]),
        "payload": {
            "business_key": str(raw["business_key"]).strip(),
            "title": str(raw["title"]).strip(),
            "price": float(raw["price"]),
            "category": str(raw["category"]).strip(),
            "event_ts": str(raw["event_ts"]).strip(),
            "source_revision": int(raw["source_revision"]),
        },
    }


def parse_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("JSON feed must be a list or an object with items[]")
    return [_normalize_item(x) for x in items]


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            rows.append(_normalize_item(json.loads(text)))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"jsonl line {line_no}: {exc}") from exc
    return rows


def parse_xml(path: Path) -> list[dict[str, Any]]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for node in root.findall(".//item"):
        raw = {child.tag: child.text for child in list(node)}
        rows.append(_normalize_item(raw))
    return rows


PARSERS = {
    "json": parse_json,
    "jsonl": parse_jsonl,
    "xml": parse_xml,
}


def parse_fixture(path: Path, fmt: str) -> list[dict[str, Any]]:
    parser = PARSERS.get(fmt)
    if parser is None:
        raise ValueError(f"unsupported format: {fmt}")
    if not path.exists():
        raise FileNotFoundError(str(path))
    return parser(path)
