from fastapi import APIRouter

from app.db import connect
from app.repositories import settings as settings_repo
from app.schemas.entities import SettingUpdate

router = APIRouter(tags=["settings"])


@router.get("/settings")
def list_settings():
    conn = connect()
    try:
        return settings_repo.as_list(conn)
    finally:
        conn.close()


@router.put("/settings/{key}")
def put_setting(key: str, body: SettingUpdate):
    conn = connect()
    try:
        settings_repo.set_value(conn, key, body.value)
        conn.commit()
        return {"key": key, "value": body.value}
    finally:
        conn.close()


@router.get("/watermarks")
def list_watermarks():
    from app.repositories import sources as sources_repo

    conn = connect()
    try:
        return [
            {
                "source_id": s["id"],
                "name": s["name"],
                "watermark_ts": s["watermark_ts"],
                "lookback_seconds": s["lookback_seconds"],
            }
            for s in sources_repo.list_sources(conn)
        ]
    finally:
        conn.close()
