"""Health check endpoints.

  GET /api/health        — liveness (API is up, no DB check)
  GET /api/health/ready  — readiness (DB is reachable)
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

router = APIRouter()


@router.get("/health")
async def health():
    """Liveness check — API process is running.

    Does not touch the database. Used by load balancers
    to know the process is alive.
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness check — API can serve requests (DB is reachable).

    Used by deployment platforms to decide whether to route traffic.
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": str(e)}
