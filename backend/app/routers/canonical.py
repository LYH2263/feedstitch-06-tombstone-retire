from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.db import connect
from app.repositories import canonical as canon_repo

router = APIRouter(tags=["canonical"])


@router.get("/canonical")
def list_canonical(
    status: Literal["alive", "retired", "all"] = Query(
        default="alive",
        description="alive=在售有效项（默认，退役键不展示）；retired=退役列表；all=全部",
    ),
):
    conn = connect()
    try:
        return canon_repo.list_items(conn, None if status == "all" else status)
    finally:
        conn.close()


@router.get("/canonical/{business_key}")
def get_canonical(business_key: str):
    conn = connect()
    try:
        row = canon_repo.get_by_key(conn, business_key)
        if not row:
            raise HTTPException(404, "not found")
        return row
    finally:
        conn.close()
