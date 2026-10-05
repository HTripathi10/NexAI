"""SQLite database with SQLAlchemy async — users, usage logs, metrics."""
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Date,
    select, func, text
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ─── ORM Models ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RequestLog(Base):
    """One row per LLM request — stores tokens, latency, metrics."""
    __tablename__ = "request_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), nullable=False, index=True)
    backend = Column(String(20), nullable=False)   # ollama | groq
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    ttft_ms = Column(Float, nullable=True)
    total_latency_ms = Column(Float, nullable=False)
    tokens_per_second = Column(Float, nullable=True)
    finish_reason = Column(String(50), default="stop")
    created_at = Column(DateTime, default=datetime.utcnow)
    request_date = Column(Date, default=date.today)


# ─── DB Lifecycle ─────────────────────────────────────────────────────────────

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# ─── User helpers ─────────────────────────────────────────────────────────────

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, hashed_password: str) -> User:
    user = User(username=username, hashed_password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ─── Usage helpers ────────────────────────────────────────────────────────────

async def log_request(
    db: AsyncSession,
    username: str,
    backend: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    ttft_ms: Optional[float],
    total_latency_ms: float,
    tokens_per_second: Optional[float],
    finish_reason: str = "stop",
) -> RequestLog:
    log = RequestLog(
        username=username,
        backend=backend,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        ttft_ms=ttft_ms,
        total_latency_ms=total_latency_ms,
        tokens_per_second=tokens_per_second,
        finish_reason=finish_reason,
        request_date=date.today(),
    )
    db.add(log)
    await db.commit()
    return log


async def get_daily_token_usage(db: AsyncSession, username: str) -> int:
    today = date.today()
    result = await db.execute(
        select(func.coalesce(func.sum(RequestLog.total_tokens), 0))
        .where(RequestLog.username == username)
        .where(RequestLog.request_date == today)
    )
    return result.scalar()


async def get_usage_stats(db: AsyncSession, username: str) -> dict:
    today = date.today()
    month_start = today.replace(day=1)

    def _period_query(start: date, end: Optional[date] = None):
        q = select(
            func.coalesce(func.sum(RequestLog.input_tokens), 0),
            func.coalesce(func.sum(RequestLog.output_tokens), 0),
            func.coalesce(func.sum(RequestLog.total_tokens), 0),
            func.count(RequestLog.id),
        ).where(RequestLog.username == username)
        if end:
            q = q.where(RequestLog.request_date.between(start, end))
        else:
            q = q.where(RequestLog.request_date == start)
        return q

    today_result = await db.execute(_period_query(today))
    month_result = await db.execute(_period_query(month_start, today))

    ti, to, tt, tc = today_result.one()
    mi, mo, mt, mc = month_result.one()

    return {
        "today": {"input_tokens": ti, "output_tokens": to, "total_tokens": tt, "request_count": tc},
        "this_month": {"input_tokens": mi, "output_tokens": mo, "total_tokens": mt, "request_count": mc},
    }


async def get_aggregated_metrics(db: AsyncSession) -> dict:
    result = await db.execute(
        select(
            func.count(RequestLog.id),
            func.avg(RequestLog.ttft_ms),
            func.avg(RequestLog.tokens_per_second),
            func.avg(RequestLog.total_latency_ms),
        )
    )
    total, avg_ttft, avg_tps, avg_lat = result.one()

    # by backend
    by_backend_result = await db.execute(
        select(RequestLog.backend, func.count(RequestLog.id), func.avg(RequestLog.total_latency_ms))
        .group_by(RequestLog.backend)
    )
    by_backend = {
        row[0]: {"requests": row[1], "avg_latency_ms": round(row[2] or 0, 2)}
        for row in by_backend_result.all()
    }

    # by model
    by_model_result = await db.execute(
        select(RequestLog.model, func.count(RequestLog.id), func.avg(RequestLog.total_latency_ms))
        .group_by(RequestLog.model)
    )
    by_model = {
        row[0]: {"requests": row[1], "avg_latency_ms": round(row[2] or 0, 2)}
        for row in by_model_result.all()
    }

    return {
        "total_requests": total or 0,
        "avg_ttft_ms": round(avg_ttft, 2) if avg_ttft else None,
        "avg_tokens_per_second": round(avg_tps, 2) if avg_tps else None,
        "avg_latency_ms": round(avg_lat, 2) if avg_lat else None,
        "by_backend": by_backend,
        "by_model": by_model,
    }
