from fastapi import APIRouter, HTTPException

from app.db import connect
from app.repositories import runs as runs_repo
from app.schemas.entities import RunRequest
from app.services.ingest_service import run_ingest

router = APIRouter(tags=["runs"])


@router.get("/runs")
def list_runs():
    conn = connect()
    try:
        return runs_repo.list_runs(conn)
    finally:
        conn.close()


@router.get("/runs/{run_id}")
def get_run(run_id: int):
    conn = connect()
    try:
        row = runs_repo.get_run(conn, run_id)
        if not row:
            raise HTTPException(404, "run not found")
        return row
    finally:
        conn.close()


@router.post("/sources/{source_id}/runs")
def create_run(source_id: int, body: RunRequest):
    try:
        return run_ingest(source_id, body.mode)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc
