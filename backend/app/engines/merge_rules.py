"""Business-key merge / conflict decisions for Feedstitch."""

from __future__ import annotations

from typing import Any


NON_KEY_FIELDS = ("title", "price", "category")


def non_key_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    return {k: item[k] for k in NON_KEY_FIELDS}


def fields_conflict(existing: dict[str, Any], incoming: dict[str, Any]) -> bool:
    return non_key_snapshot(existing) != non_key_snapshot(incoming)


def decide_merge(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
) -> str:
    """Return one of: insert | upsert | conflict | skip_stale.

    Base rules (lookback not implemented):
    - no existing → insert
    - non-key diverge → conflict
    - same non-key, incoming revision > existing → upsert
    - else → skip_stale
    """
    if existing is None:
        return "insert"
    if fields_conflict(existing, incoming):
        return "conflict"
    if int(incoming["source_revision"]) > int(existing["source_revision"]):
        return "upsert"
    return "skip_stale"


def eligible_for_incremental(
    event_ts: str,
    watermark_ts: str | None,
    lookback_seconds: int = 0,
) -> bool:
    """Base: event_ts must be strictly after watermark. lookback reserved for 0-1."""
    del lookback_seconds  # reserved; base ignores lookback window
    if not watermark_ts:
        return True
    return event_ts > watermark_ts
