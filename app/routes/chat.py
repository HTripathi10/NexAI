"""Chat completion route with quota enforcement and metrics logging."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db, log_request, get_daily_token_usage
from app.models import ChatRequest, ChatResponse, PerformanceMetrics, ModelsResponse
from app.llm import ollama_client, groq_client

settings = get_settings()
router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completions(
    request: ChatRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # ── Quota check ──────────────────────────────────────────────────────────
    daily_used = await get_daily_token_usage(db, current_user.username)
    if daily_used >= settings.daily_token_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "daily_quota_exceeded",
                "daily_quota": settings.daily_token_quota,
                "tokens_used_today": daily_used,
                "daily_quota": settings.daily_token_quota,
                "message": "Daily token quota exceeded. Resets at midnight UTC.",
            },
        )

    # ── Build messages list ───────────────────────────────────────────────────
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    # ── Dispatch to backend ───────────────────────────────────────────────────
    try:
        if request.backend.value == "ollama":
            if request.stream:
                result = await ollama_client.chat_completion_stream(
                    messages, request.model, request.temperature, request.max_tokens
                )
            else:
                result = await ollama_client.chat_completion(
                    messages, request.model, request.temperature, request.max_tokens
                )
        else:  # groq
            if not settings.groq_api_key:
                raise HTTPException(status_code=400, detail="Groq API key not configured.")
            if request.stream:
                result = await groq_client.chat_completion_stream(
                    messages, request.model, request.temperature, request.max_tokens
                )
            else:
                result = await groq_client.chat_completion(
                    messages, request.model, request.temperature, request.max_tokens
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")

    # ── Log request ───────────────────────────────────────────────────────────
    await log_request(
        db=db,
        username=current_user.username,
        backend=request.backend.value,
        model=result["model"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        ttft_ms=result.get("ttft_ms"),
        total_latency_ms=result["total_latency_ms"],
        tokens_per_second=result.get("tokens_per_second"),
        finish_reason=result.get("finish_reason", "stop"),
    )

    # ── Build response ────────────────────────────────────────────────────────
    metrics = PerformanceMetrics(
        ttft_ms=result.get("ttft_ms"),
        total_latency_ms=round(result["total_latency_ms"], 2),
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        tokens_per_second=round(result["tokens_per_second"], 2) if result.get("tokens_per_second") else None,
        backend=request.backend.value,
        model=result["model"],
    )

    return ChatResponse(
        id=str(uuid.uuid4()),
        content=result["content"],
        finish_reason=result.get("finish_reason", "stop"),
        metrics=metrics,
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models(current_user=Depends(get_current_user)):
    """List available models from both backends."""
    ollama_models = await ollama_client.list_models()
    groq_models = await groq_client.list_models() if settings.groq_api_key else []
    return {
        "ollama": ollama_models,
        "groq": groq_models,
    }
