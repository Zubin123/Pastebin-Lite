"""
Health check route.
"""
from fastapi import APIRouter
from app.models import HealthCheck
from app.database import db

router = APIRouter()


@router.get("/api/healthz", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """
    Health check endpoint.
    Returns 200 with ok=true if application and database are healthy.
    """
    is_healthy = db.is_healthy()
    return HealthCheck(ok=is_healthy)
