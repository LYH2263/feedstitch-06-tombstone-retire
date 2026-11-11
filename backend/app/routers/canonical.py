from fastapi import APIRouter, HTTPException

from app.db import connect
from app.repositories import canonical as canon_repo

router = APIRouter(tags=["canonical"])


@router.get("/canonical")
def list_canonical():
    conn = connect()
    try:
        return canon_repo.list_items(conn)
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
