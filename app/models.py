"""Pydantic v2 request/response schemas."""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
from enum import Enum


class StrictSchema(BaseModel):
    """Base schema that rejects misspelled or unexpected request/response fields."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(StrictSchema):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(..., min_length=8, max_length=128)


class UserCreated(StrictSchema):
    id: str
    username: str
    message: str


class Token(StrictSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class LoginRequest(StrictSchema):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class TokenData(StrictSchema):
    username: Optional[str] = None


# ─── Chat ────────────────────────────────────────────────────────────────────

class BackendEnum(str, Enum):
    ollama = "ollama"
    groq = "groq"


class Message(StrictSchema):
    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1, max_length=32000)


class ChatRequest(StrictSchema):
    model: Optional[str] = Field(default=None, min_length=1, max_length=120)  # overrides default model
    messages: List[Message] = Field(..., min_length=1, max_length=100)
    backend: BackendEnum = BackendEnum.ollama
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192)

    @field_validator("messages")
    @classmethod
    def must_have_user_message(cls, v: List[Message]) -> List[Message]:
        if not any(m.role == "user" for m in v):
            raise ValueError("At least one user message is required.")
        return v


class PerformanceMetrics(StrictSchema):
    ttft_ms: Optional[float] = Field(None, description="Time to first token (ms)")
    total_latency_ms: float = Field(..., description="Total request latency (ms)")
    input_tokens: int
    output_tokens: int
    tokens_per_second: Optional[float] = None
    backend: str
    model: str


class ChatResponse(StrictSchema):
    id: str
    content: str
    role: str = "assistant"
    finish_reason: str = "stop"
    metrics: PerformanceMetrics
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Usage ───────────────────────────────────────────────────────────────────

class UsagePeriod(StrictSchema):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    request_count: int


class UsageResponse(StrictSchema):
    username: str
    today: UsagePeriod
    this_month: UsagePeriod
    daily_quota: int
    daily_remaining: int
    quota_reset_at: str  # ISO datetime of next reset


# ─── Metrics endpoint ────────────────────────────────────────────────────────

class AggregatedMetrics(StrictSchema):
    total_requests: int
    avg_ttft_ms: Optional[float]
    avg_tokens_per_second: Optional[float]
    avg_latency_ms: Optional[float]
    by_backend: Dict[str, Dict[str, Any]]
    by_model: Dict[str, Dict[str, Any]]


# ─── Error ───────────────────────────────────────────────────────────────────

class ErrorResponse(StrictSchema):
    error: str
    detail: Optional[Any] = None
    code: Optional[str] = None


class ModelsResponse(StrictSchema):
    ollama: List[str]
    groq: List[str]


class HealthResponse(StrictSchema):
    status: str
    app: str
    version: str
    ollama_url: str
    groq_configured: bool


class RootResponse(StrictSchema):
    message: str
    docs: str
    health: str
