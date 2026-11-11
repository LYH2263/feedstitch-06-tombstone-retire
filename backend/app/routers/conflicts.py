from fastapi import APIRouter

from app.db import connect
from app.repositories import runs as runs_repo

router = APIRouter(tags=["conflicts"])


@router.get("/conflicts")
def list_conflicts():
    conn = connect()
    try:
        return runs_repo.list_conflicts(conn)
    finally:
        conn.close()
