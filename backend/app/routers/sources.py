from fastapi import APIRouter, HTTPException

from app.db import connect
from app.repositories import sources as sources_repo
from app.schemas.entities import LookbackUpdate
from app.services.ingest_service import preview_source

router = APIRouter(tags=["sources"])


@router.get("/sources")
def list_sources():
    conn = connect()
    try:
        return sources_repo.list_sources(conn)
    finally:
        conn.close()


@router.get("/sources/{source_id}")
def get_source(source_id: int):
    conn = connect()
    try:
        row = sources_repo.get_source(conn, source_id)
        if not row:
            raise HTTPException(404, "source not found")
        return row
    finally:
        conn.close()


@router.get("/sources/{source_id}/preview")
def preview(source_id: int):
    try:
        return preview_source(source_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


@router.patch("/sources/{source_id}/lookback")
def patch_lookback(source_id: int, body: LookbackUpdate):
    """Field exists for 0-1; base ingest currently ignores lookback_seconds."""
    conn = connect()
    try:
        if not sources_repo.get_source(conn, source_id):
            raise HTTPException(404, "source not found")
        sources_repo.update_lookback(conn, source_id, body.lookback_seconds)
        conn.commit()
        return sources_repo.get_source(conn, source_id)
    finally:
        conn.close()
