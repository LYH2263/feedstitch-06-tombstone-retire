from __future__ import annotations

from typing import Any

from app.config import FIXTURES_DIR
from app.db import connect
from app.engines.merge_rules import decide_merge, eligible_for_incremental
from app.engines.parse_feed import parse_fixture
from app.modules.tombstone_retire import (
    REJECT_STALE_REVIVED,
    REVIVE_UPSERT,
    TOMBSTONE_DUPLICATE,
    TOMBSTONE_RETIRE,
    TOMBSTONE_UNKNOWN,
    decide_revive,
    decide_tombstone,
    is_retired,
)
from app.repositories import canonical as canon_repo
from app.repositories import runs as runs_repo
from app.repositories import sources as sources_repo


def preview_source(source_id: int) -> dict[str, Any]:
    conn = connect()
    try:
        source = sources_repo.get_source(conn, source_id)
        if not source:
            raise ValueError("source not found")
        path = FIXTURES_DIR / source["fixture_path"]
        items = parse_fixture(path, source["format"], bool(source.get("tombstone_source")))
        return {
            "source": source,
            "count": len(items),
            "items": items[:50],
        }
    finally:
        conn.close()


def _existing_view(existing: dict[str, Any] | None) -> dict[str, Any] | None:
    if not existing:
        return None
    return {
        "business_key": existing["business_key"],
        "title": existing["title"],
        "price": existing["price"],
        "category": existing["category"],
        "event_ts": existing["event_ts"],
        "source_revision": existing["source_revision"],
        "status": existing["status"],
        "payload": existing["payload"],
    }


def run_ingest(source_id: int, mode: str = "incremental") -> dict[str, Any]:
    if mode not in ("incremental", "full"):
        raise ValueError("mode must be incremental or full")

    conn = connect()
    try:
        source = sources_repo.get_source(conn, source_id)
        if not source:
            raise ValueError("source not found")
        if not source["enabled"]:
            raise ValueError("source disabled")

        tombstone_source = bool(source.get("tombstone_source"))
        if mode == "full":
            sources_repo.set_watermark(conn, source_id, None)
            source["watermark_ts"] = None

        run_id = runs_repo.create_run(conn, source_id, mode)
        path = FIXTURES_DIR / source["fixture_path"]

        try:
            items = parse_fixture(path, source["format"], tombstone_source)
        except Exception as exc:  # noqa: BLE001
            runs_repo.finish_run(
                conn,
                run_id,
                status="failed",
                parsed=0,
                upserted=0,
                conflicts=0,
                skipped=0,
                retired=0,
                revived=0,
                report={"error": str(exc)},
            )
            conn.commit()
            raise

        parsed = 0
        upserted = 0
        conflicts = 0
        skipped = 0
        retired = 0
        revived = 0
        max_event_ts: str | None = source.get("watermark_ts")

        for item in items:
            parsed += 1
            if mode == "incremental" and not eligible_for_incremental(
                item["event_ts"],
                source.get("watermark_ts"),
                int(source.get("lookback_seconds") or 0),
            ):
                runs_repo.insert_staging(
                    conn,
                    run_id=run_id,
                    source_id=source_id,
                    item=item,
                    disposition="skipped_watermark",
                )
                skipped += 1
                continue

            existing = canon_repo.get_by_key(conn, item["business_key"])

            # --- Branch 1: tombstone / retire event -------------------------
            if item["is_tombstone"]:
                decision = decide_tombstone(existing)
                if decision == TOMBSTONE_RETIRE:
                    canon_repo.retire_item(
                        conn,
                        business_key=item["business_key"],
                        event_ts=item["event_ts"],
                        source_revision=item["source_revision"],
                        run_id=run_id,
                        source_id=source_id,
                    )
                    retired += 1
                else:
                    # duplicate / unknown: no canonical write, no counter move
                    skipped += 1
                runs_repo.insert_staging(
                    conn,
                    run_id=run_id,
                    source_id=source_id,
                    item=item,
                    disposition=decision,
                )
                if max_event_ts is None or item["event_ts"] > max_event_ts:
                    max_event_ts = item["event_ts"]
                continue

            # --- Branch 2: alive event on a retired key (revive / reject) ---
            if is_retired(existing):
                decision = decide_revive(existing, item)
                if decision == REVIVE_UPSERT:
                    canon_repo.upsert_item(conn, item, source_id)
                    revived += 1
                else:
                    # stale revision cannot un-retire the key: reject write
                    skipped += 1
                runs_repo.insert_staging(
                    conn,
                    run_id=run_id,
                    source_id=source_id,
                    item=item,
                    disposition=decision,
                )
                if max_event_ts is None or item["event_ts"] > max_event_ts:
                    max_event_ts = item["event_ts"]
                continue

            # --- Branch 3: normal alive merge against alive / missing row ---
            existing_view = _existing_view(existing)
            decision = decide_merge(existing_view, item)
            if decision in ("insert", "upsert"):
                canon_repo.upsert_item(conn, item, source_id)
                runs_repo.insert_staging(
                    conn,
                    run_id=run_id,
                    source_id=source_id,
                    item=item,
                    disposition=decision,
                )
                upserted += 1
            elif decision == "conflict":
                runs_repo.insert_conflict(
                    conn,
                    run_id=run_id,
                    source_id=source_id,
                    business_key=item["business_key"],
                    existing_payload=existing_view["payload"] if existing_view else {},
                    incoming_payload=item["payload"],
                    reason="non_key_field_mismatch",
                )
                runs_repo.insert_staging(
                    conn,
                    run_id=run_id,
                    source_id=source_id,
                    item=item,
                    disposition="quarantine",
                )
                conflicts += 1
            else:
                runs_repo.insert_staging(
                    conn,
                    run_id=run_id,
                    source_id=source_id,
                    item=item,
                    disposition="skip_stale",
                )
                skipped += 1
            if max_event_ts is None or item["event_ts"] > max_event_ts:
                max_event_ts = item["event_ts"]

        if max_event_ts:
            sources_repo.set_watermark(conn, source_id, max_event_ts)

        # Reconciliation snapshot: every count below comes from the database,
        # the same tables that back the Staging / Canonical list pages.
        per_disposition = runs_repo.disposition_counts(conn, run_id)
        staging_total = sum(per_disposition.values())
        alive_count = canon_repo.count_alive(conn)
        retired_count = canon_repo.count_retired(conn)
        report = {
            "source_id": source_id,
            "mode": mode,
            "parsed_count": parsed,
            "upserted_count": upserted,
            "retired_count": retired,
            "revived_count": revived,
            "conflict_count": conflicts,
            "skipped_count": skipped,
            # Backward-compatible field: canonical total (alive + retired).
            "canonical_count": alive_count + retired_count,
            "canonical_alive_count": alive_count,
            "canonical_retired_count": retired_count,
            "watermark_ts": max_event_ts,
            "staging_row_count": staging_total,
            "disposition_counts": per_disposition,
            # Identity that must hold: every parsed row got exactly one
            # disposition, and the four state-changing/skip buckets partition it.
            "reconciled": (
                parsed == staging_total
                and parsed == upserted + retired + revived + conflicts + skipped
            ),
        }
        runs_repo.finish_run(
            conn,
            run_id,
            status="ok",
            parsed=parsed,
            upserted=upserted,
            conflicts=conflicts,
            skipped=skipped,
            retired=retired,
            revived=revived,
            report=report,
        )
        conn.commit()
        run = runs_repo.get_run(conn, run_id)
        return run or report
    finally:
        conn.close()


def dashboard_stats() -> dict[str, Any]:
    conn = connect()
    try:
        sources = sources_repo.list_sources(conn)
        return {
            "source_count": len(sources),
            "enabled_sources": sum(1 for s in sources if s["enabled"]),
            "canonical_count": canon_repo.count_alive(conn),
            "canonical_retired_count": canon_repo.count_retired(conn),
            "conflict_count": conn.execute("SELECT COUNT(*) c FROM conflicts").fetchone()["c"],
            "run_count": conn.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"],
            "staging_count": conn.execute("SELECT COUNT(*) c FROM staging_rows").fetchone()["c"],
        }
    finally:
        conn.close()
