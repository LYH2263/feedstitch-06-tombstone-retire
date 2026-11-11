from fastapi import APIRouter, Query

from app.db import connect
from app.repositories import runs as runs_repo

router = APIRouter(tags=["staging"])


@router.get("/staging")
def list_staging(run_id: int | None = Query(default=None)):
    conn = connect()
    try:
        return runs_repo.list_staging(conn, run_id)
    finally:
        conn.close()
