"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import init_db
from app.routes import auth, chat, usage, metrics
from app.api.v1 import screen
from app.models import ErrorResponse, HealthResponse, RootResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables on startup."""
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## NexAI — AI Workspace

A FastAPI service that routes LLM requests to **Ollama** (local)
or **Groq** (free-tier cloud), with:

- 🔐 **JWT Authentication** — register/login, bearer tokens
- 📊 **Token-based Usage Tracking** — per-user daily/monthly quotas stored in SQLite
- 🚦 **Quota Enforcement** — 429 when daily token limit exceeded
- ⚡ **Performance Metrics** — TTFT, tokens/sec, total latency on every request
- 📈 **Aggregated `/metrics`** — system-wide stats by backend/model
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(usage.router)
app.include_router(metrics.router)
app.include_router(screen.router)


def error_payload(error: str, detail, code: str):
    return ErrorResponse(error=error, detail=detail, code=code).model_dump()


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    status_code = exc.status_code
    error_name = {
        401: "unauthorized", 403: "forbidden", 404: "not_found", 429: "too_many_requests",
        422: "validation_error", 503: "service_unavailable",
    }.get(status_code, "request_error")
    detail = exc.detail
    # Keep quota specifics useful to the UI while retaining the shared outer format.
    if isinstance(detail, dict):
        detail = detail.get("message", str(detail))
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        body = {"error": {"code": exc.detail["code"], "message": exc.detail["message"]}}
    else:
        body = {"error": {"code": error_name, "message": str(detail)}}
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    issues = [
        {"field": ".".join(str(part) for part in issue.get("loc", ())),
         "message": issue.get("msg", "Invalid value")}
        for issue in exc.errors()
    ]
    message = "; ".join(f"{item['field']}: {item['message']}" for item in issues)
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": message}},
    )


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error_payload("internal_server_error", "An unexpected error occurred.", "500"),
    )


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"], response_model=HealthResponse)
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "ollama_url": settings.ollama_base_url,
        "groq_configured": bool(settings.groq_api_key),
    }


@app.get("/", tags=["health"], response_model=RootResponse)
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs",
        "health": "/health",
    }
