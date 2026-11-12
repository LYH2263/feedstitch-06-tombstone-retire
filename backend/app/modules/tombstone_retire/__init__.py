"""Tombstone / retire policy for canonical business keys.

Auditable policy implemented here:

* A tombstone event soft-retires an **alive** canonical row
  (``tombstone_retire``). The row is never physically deleted: it keeps its
  last known payload plus retirement metadata, stays queryable by key, and is
  hidden from the alive canonical view.
* A repeated tombstone for an already retired key is a no-op
  (``tombstone_duplicate``): it must not inflate retirement counters or
  re-write retirement metadata.
* A tombstone for a key that was never canonicalized cannot retire anything
  (``tombstone_unknown``) — nothing is invented.
* An alive event arriving for a **retired** key follows an explicit
  revive-or-reject rule based on revision ordering, so each outcome is
  distinguishable in staging and run reports:

    - newer revision -> revive write (``revive_upsert``)
    - same/older revision -> reject write (``reject_stale_revived``),
      the retired row is left untouched.

This is a soft-delete state flag on the canonical row, not a Type-2 history
chain and not a conflict dead-letter workflow.
"""

from __future__ import annotations

from typing import Any

# Staging dispositions emitted by this module.
TOMBSTONE_RETIRE = "tombstone_retire"
TOMBSTONE_DUPLICATE = "tombstone_duplicate"
TOMBSTONE_UNKNOWN = "tombstone_unknown"
REVIVE_UPSERT = "revive_upsert"
REJECT_STALE_REVIVED = "reject_stale_revived"

ALIVE = "alive"
RETIRED = "retired"


def is_retired(existing: dict[str, Any] | None) -> bool:
    return existing is not None and existing.get("status") == RETIRED


def decide_tombstone(existing: dict[str, Any] | None) -> str:
    """Classify a tombstone event against the current canonical row."""
    if existing is None:
        return TOMBSTONE_UNKNOWN
    if existing.get("status") == RETIRED:
        return TOMBSTONE_DUPLICATE
    return TOMBSTONE_RETIRE


def decide_revive(existing: dict[str, Any], incoming: dict[str, Any]) -> str:
    """Classify an alive event arriving on a retired key.

    Newer source revision revives the key; an equal or older revision is
    rejected as stale so an out-of-order event cannot silently un-retire it.
    """
    if int(incoming["source_revision"]) > int(existing["source_revision"]):
        return REVIVE_UPSERT
    return REJECT_STALE_REVIVED
