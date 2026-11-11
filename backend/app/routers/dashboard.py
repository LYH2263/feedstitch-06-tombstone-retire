from fastapi import APIRouter

from app.services.ingest_service import dashboard_stats

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard():
    return dashboard_stats()
