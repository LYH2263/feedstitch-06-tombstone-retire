import json
from pathlib import Path

import pytest

from app.config import FIXTURES_DIR
from app.engines.merge_rules import decide_merge, eligible_for_incremental, fields_conflict
from app.engines.parse_feed import parse_fixture


def test_parse_json_alpha():
    items = parse_fixture(FIXTURES_DIR / "alpha_catalog.json", "json")
    assert len(items) == 3
    assert items[0]["business_key"] == "SKU-1001"
    assert items[0]["price"] == 129.0


def test_parse_jsonl_beta():
    items = parse_fixture(FIXTURES_DIR / "beta_offers.jsonl", "jsonl")
    assert len(items) == 3
    assert items[0]["business_key"] == "SKU-1001"
    assert items[0]["price"] == 99.0


def test_parse_xml_gamma():
    items = parse_fixture(FIXTURES_DIR / "gamma_shelf.xml", "xml")
    assert len(items) == 2
    assert items[1]["business_key"] == "SKU-3002"


def test_conflict_on_price():
    a = {"title": "Oak Desk Lamp", "price": 129.0, "category": "lighting", "source_revision": 3}
    b = {"title": "Oak Desk Lamp", "price": 99.0, "category": "lighting", "source_revision": 4}
    assert fields_conflict(a, b) is True
    assert decide_merge(a, {**b, "business_key": "SKU-1001", "event_ts": "t", "payload": {}}) == "conflict"


def test_upsert_higher_revision_same_fields():
    a = {
        "business_key": "SKU-1",
        "title": "X",
        "price": 10.0,
        "category": "c",
        "source_revision": 1,
        "event_ts": "t1",
        "payload": {},
    }
    b = {
        "business_key": "SKU-1",
        "title": "X",
        "price": 10.0,
        "category": "c",
        "source_revision": 2,
        "event_ts": "t2",
        "payload": {},
    }
    assert decide_merge(a, b) == "upsert"


def test_insert_when_missing():
    incoming = {
        "business_key": "SKU-9",
        "title": "Y",
        "price": 1.0,
        "category": "c",
        "source_revision": 1,
        "event_ts": "t",
        "payload": {},
    }
    assert decide_merge(None, incoming) == "insert"


def test_watermark_gate():
    assert eligible_for_incremental("2026-11-02T00:00:00Z", None) is True
    assert eligible_for_incremental("2026-11-02T00:00:00Z", "2026-11-01T00:00:00Z") is True
    assert eligible_for_incremental("2026-11-01T00:00:00Z", "2026-11-01T00:00:00Z") is False
    assert eligible_for_incremental("2026-10-01T00:00:00Z", "2026-11-01T00:00:00Z") is False


def test_parse_missing_field_raises(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([{"business_key": "x"}]), encoding="utf-8")
    with pytest.raises(ValueError):
        parse_fixture(p, "json")
