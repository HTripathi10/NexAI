"""Usage tracking routes — GET /v1/usage."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db, get_usage_stats
from app.models import UsageResponse, UsagePeriod

settings = get_settings()
router = APIRouter(prefix="/v1", tags=["usage"])


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stats = await get_usage_stats(db, current_user.username)
    daily_used = stats["today"]["total_tokens"]
    daily_remaining = max(0, settings.daily_token_quota - daily_used)

    # Next reset: midnight UTC tomorrow
    from datetime import timedelta
    tomorrow = date.today() + timedelta(days=1)
    reset_at = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc).isoformat()

    return UsageResponse(
        username=current_user.username,
        today=UsagePeriod(**stats["today"]),
        this_month=UsagePeriod(**stats["this_month"]),
        daily_quota=settings.daily_token_quota,
        daily_remaining=daily_remaining,
        quota_reset_at=reset_at,
    )
