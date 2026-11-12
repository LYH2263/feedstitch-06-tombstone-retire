"""Tombstone / retire end-to-end tests on a throwaway SQLite database."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from app.config import FIXTURES_DIR
from app.engines.parse_feed import detect_tombstone, parse_fixture
from app.modules.tombstone_retire import (
    ALIVE,
    REJECT_STALE_REVIVED,
    RETIRED,
    REVIVE_UPSERT,
    TOMBSTONE_DUPLICATE,
    TOMBSTONE_RETIRE,
    TOMBSTONE_UNKNOWN,
    decide_revive,
    decide_tombstone,
)


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point DATA_DIR at a temp folder and reload seed/db so each test gets a
    fresh database with the demo sources."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import app.config as config
    importlib.reload(config)
    import app.db as db
    importlib.reload(db)
    import app.seed as seed
    importlib.reload(seed)
    seed.init_db()

    from app.db import connect
    from app.repositories import sources as sources_repo
    from app.services import ingest_service

    # Reload service so it binds the reloaded db.connect.
    importlib.reload(ingest_service)
    conn = connect()
    try:
        sources = {s["name"]: s["id"] for s in sources_repo.list_sources(conn)}
    finally:
        conn.close()
    return sources, ingest_service


def _run(ingest_service, source_id: int, mode: str = "incremental"):
    return ingest_service.run_ingest(source_id, mode)


def test_detect_tombstone_markers():
    assert detect_tombstone({"tombstone": True}) is True
    assert detect_tombstone({"status": "RETIRED"}) is True
    assert detect_tombstone({"event_type": "delete"}) is True
    assert detect_tombstone({"is_deleted": "true"}) is True
    assert detect_tombstone({"status": "active"}) is False
    assert detect_tombstone({"title": "x"}) is False


def test_decide_tombstone_policy():
    alive_row = {"status": ALIVE}
    retired_row = {"status": RETIRED}
    assert decide_tombstone(None) == TOMBSTONE_UNKNOWN
    assert decide_tombstone(alive_row) == TOMBSTONE_RETIRE
    assert decide_tombstone(retired_row) == TOMBSTONE_DUPLICATE


def test_decide_revive_revision_order():
    retired_row = {"status": RETIRED, "source_revision": 2}
    newer = {"source_revision": 3}
    older = {"source_revision": 1}
    same = {"source_revision": 2}
    assert decide_revive(retired_row, newer) == REVIVE_UPSERT
    assert decide_revive(retired_row, older) == REJECT_STALE_REVIVED
    assert decide_revive(retired_row, same) == REJECT_STALE_REVIVED


def test_source_level_tombstone_force_flags_every_row():
    items = parse_fixture(FIXTURES_DIR / "delta_retirements.jsonl", "jsonl", True)
    assert len(items) == 3
    assert all(i["is_tombstone"] for i in items)
    # Tombstone rows do not require descriptive fields.
    assert items[0]["business_key"] == "SKU-1002"
    assert items[0]["title"] == ""


def test_in_band_tombstone_marker_parsing():
    items = parse_fixture(FIXTURES_DIR / "epsilon_revive.jsonl", "jsonl")
    assert len(items) == 5
    flags = {i["business_key"] + ":" + i["event_ts"]: i["is_tombstone"] for i in items}
    assert flags["SKU-1003:2026-11-04T08:00:00Z"] is True
    assert flags["SKU-2001:2026-11-04T10:30:00Z"] is True
    assert flags["SKU-1003:2026-11-04T10:00:00Z"] is False


def test_retirement_takes_effect_and_persists(isolated_db):
    sources, ingest = isolated_db

    # Seed alive canonical rows from Alpha (3 items).
    alpha_run = _run(ingest, sources["Alpha Catalog"])
    assert alpha_run["report"]["reconciled"] is True

    from app.db import connect
    from app.repositories import canonical as canon_repo

    conn = connect()
    try:
        assert canon_repo.count_alive(conn) == 3
        assert canon_repo.count_retired(conn) == 0
        # Alive view must not contain the soon-to-be-retired key differently.
        assert canon_repo.get_by_key(conn, "SKU-1002")["status"] == ALIVE
    finally:
        conn.close()

    # Delta source: retire SKU-1002, duplicate tombstone, unknown key.
    delta_run = _run(ingest, sources["Delta Retirements"])
    report = delta_run["report"]
    assert report["parsed_count"] == 3
    assert report["retired_count"] == 1
    assert report["skipped_count"] == 2  # duplicate + unknown
    assert report["revived_count"] == 0
    assert report["reconciled"] is True
    assert report["disposition_counts"] == {
        TOMBSTONE_RETIRE: 1,
        TOMBSTONE_DUPLICATE: 1,
        TOMBSTONE_UNKNOWN: 1,
    }

    conn = connect()
    try:
        # Soft delete: alive view shrinks, retired row stays queryable.
        assert canon_repo.count_alive(conn) == 2
        assert canon_repo.count_retired(conn) == 1
        alive_keys = {r["business_key"] for r in canon_repo.list_items(conn, ALIVE)}
        assert "SKU-1002" not in alive_keys
        retired = canon_repo.get_by_key(conn, "SKU-1002")
        assert retired["status"] == RETIRED
        assert retired["retired_at"] is not None
        assert retired["retired_by_run_id"] == delta_run["id"]
        # Last known payload is retained, not erased.
        assert retired["title"] == "Walnut Shelf"

        # Re-querying via a new connection proves the retirement was committed.
        conn2 = connect()
        try:
            again = canon_repo.get_by_key(conn2, "SKU-1002")
            assert again["status"] == RETIRED
            assert canon_repo.count_retired(conn2) == 1
        finally:
            conn2.close()
    finally:
        conn.close()


def test_duplicate_tombstone_does_not_move_watermark_or_counts(isolated_db):
    sources, ingest = isolated_db
    _run(ingest, sources["Alpha Catalog"])
    first = _run(ingest, sources["Delta Retirements"])
    watermark_after_first = first["report"]["watermark_ts"]
    assert first["report"]["retired_count"] == 1

    # Running the same tombstone source again: everything is now a duplicate /
    # unknown, counters stay at zero and the watermark must not regress.
    second = _run(ingest, sources["Delta Retirements"])
    assert second["report"]["retired_count"] == 0
    assert second["report"]["skipped_count"] == 3
    assert second["report"]["reconciled"] is True
    # Watermark already covered these event_ts -> all rows skip on watermark.
    assert second["report"]["disposition_counts"]["skipped_watermark"] == 3
    assert second["report"]["watermark_ts"] == watermark_after_first


def test_revive_accept_and_stale_reject_after_retirement(isolated_db):
    sources, ingest = isolated_db
    _run(ingest, sources["Alpha Catalog"])
    # Beta gives SKU-2001 alive (independent key).
    beta = _run(ingest, sources["Beta Offers"])
    assert beta["report"]["reconciled"] is True

    from app.db import connect
    from app.repositories import canonical as canon_repo
    from app.repositories import runs as runs_repo

    # Epsilon: retires SKU-1003 (in-band tombstone), rejects an older revision
    # while it is retired, then revives it with a newer revision; SKU-2001 is
    # retired via a status=retired marker; the last row re-retires the revived
    # SKU-1003 (a revived key is alive again, so this tombstone is a real retire).
    epsilon = _run(ingest, sources["Epsilon Revive Feed"])
    report = epsilon["report"]
    assert report["parsed_count"] == 5
    assert report["retired_count"] == 3          # SKU-1003, SKU-2001, re-retire of SKU-1003
    assert report["revived_count"] == 1          # newer revision revive
    assert report["skipped_count"] == 1          # stale reject only
    assert report["conflict_count"] == 0
    assert report["reconciled"] is True
    assert report["disposition_counts"][REVIVE_UPSERT] == 1
    assert report["disposition_counts"][REJECT_STALE_REVIVED] == 1
    assert report["disposition_counts"][TOMBSTONE_RETIRE] == 3

    conn = connect()
    try:
        # SKU-1003 was revived mid-run (revive row recorded with the new
        # payload) then re-retired by the final tombstone, so it ends retired;
        # its stored payload still reflects the revived values.
        sku_1003 = canon_repo.get_by_key(conn, "SKU-1003")
        assert sku_1003["status"] == RETIRED
        assert sku_1003["source_revision"] == 9
        assert sku_1003["price"] == 39.0
        assert sku_1003["retired_at"] is not None

        # The revive write itself is auditable in staging with its own
        # disposition and the payload that briefly restored the key.
        revive_rows = [
            s for s in runs_repo.list_staging(conn, epsilon["id"])
            if s["disposition"] == REVIVE_UPSERT
        ]
        assert len(revive_rows) == 1
        assert revive_rows[0]["business_key"] == "SKU-1003"

        retired_2001 = canon_repo.get_by_key(conn, "SKU-2001")
        assert retired_2001["status"] == RETIRED

        # Staging rows for this run partition exactly into parsed_count.
        staging = runs_repo.list_staging(conn, epsilon["id"])
        assert len(staging) == report["parsed_count"]
        dispositions = {s["disposition"] for s in staging}
        assert REVIVE_UPSERT in dispositions
        assert REJECT_STALE_REVIVED in dispositions

        # Dashboard-style counts agree with the report's canonical snapshot.
        assert canon_repo.count_alive(conn) == report["canonical_alive_count"]
        assert canon_repo.count_retired(conn) == report["canonical_retired_count"]
    finally:
        conn.close()


def test_run_counter_identity_holds_across_mixed_run(isolated_db):
    """parsed == upserted + retired + revived + conflicts + skipped, and it
    matches the staging_rows actually written."""
    sources, ingest = isolated_db
    alpha = _run(ingest, sources["Alpha Catalog"])
    assert alpha["report"]["parsed_count"] == 3
    assert alpha["report"]["upserted_count"] == 3

    beta = _run(ingest, sources["Beta Offers"])
    r = beta["report"]
    assert r["parsed_count"] == (
        r["upserted_count"]
        + r["retired_count"]
        + r["revived_count"]
        + r["conflict_count"]
        + r["skipped_count"]
    )
    assert r["reconciled"] is True
