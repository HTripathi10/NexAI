"""Performance metrics route — GET /metrics."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db, get_aggregated_metrics
from app.models import AggregatedMetrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=AggregatedMetrics)
async def get_metrics(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated performance metrics across all users."""
    data = await get_aggregated_metrics(db)
    return AggregatedMetrics(**data)
