"""JWT-protected resume screening endpoints."""
import asyncio
from io import BytesIO
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import get_settings
from app.database import User, get_daily_token_usage, get_db
from app.schemas.screening import (
    BatchRequest, BatchResponse, FailedResume, RankedResult, ResumeInput, ScreenRequest,
    ScreenResponse, UploadForm,
)
from app.services.screener import ScreeningError, screen_resume

router = APIRouter(prefix="/v1/screen", tags=["resume screening"])
settings = get_settings()
ScreenService = Callable[[ScreenRequest, str, AsyncSession], Awaitable[ScreenResponse]]
PdfTextExtractor = Callable[[bytes], str]


def get_screen_service() -> ScreenService:
    """Dependency seam for tests to supply a fake LLM-backed screening service."""
    return screen_resume


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract PDF text without saving candidate documents to disk."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ScreeningError("pdf_support_unavailable", "PDF uploads require the pypdf package.", 503) from exc
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ScreeningError("invalid_pdf", "Could not read this PDF file.", 422) from exc


def get_pdf_text_extractor() -> PdfTextExtractor:
    """Dependency seam for scanned/invalid PDF tests."""
    return extract_pdf_text


async def require_screening_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Reject screening requests once the user's daily token quota is spent."""
    used = await get_daily_token_usage(db, current_user.username)
    if used >= settings.daily_token_quota:
        raise HTTPException(
            status_code=429,
            detail={"code": "quota_exceeded", "message": "Daily token quota exceeded. Retry after the daily reset."},
        )
    return current_user


def as_http_error(error: ScreeningError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


@router.post("", response_model=ScreenResponse)
async def screen_one(
    request: ScreenRequest,
    current_user: User = Depends(require_screening_quota),
    db: AsyncSession = Depends(get_db),
    screening_service: ScreenService = Depends(get_screen_service),
) -> ScreenResponse:
    try:
        return await screening_service(request, current_user.username, db)
    except ScreeningError as exc:
        raise as_http_error(exc) from exc


@router.post("/batch", response_model=BatchResponse)
async def screen_batch(
    request: BatchRequest,
    current_user: User = Depends(require_screening_quota),
    db: AsyncSession = Depends(get_db),
    screening_service: ScreenService = Depends(get_screen_service),
) -> BatchResponse:
    semaphore = asyncio.Semaphore(2)

    async def screen_item(item: ResumeInput) -> tuple[str, ScreenResponse | None, str | None]:
        async with semaphore:
            try:
                item_request = ScreenRequest(
                    job_description=request.job_description,
                    resume_text=item.resume_text[:15000],
                    required_skills=request.required_skills,
                    provider=request.provider,
                    model=request.model,
                    temperature=request.temperature,
                )
                result = await screening_service(item_request, current_user.username, db)
                return item.filename, result, None
            except ScreeningError as exc:
                return item.filename, None, exc.message
            except Exception:
                return item.filename, None, "Screening failed for this resume."

    entries = await asyncio.gather(*(screen_item(item) for item in request.resumes))
    passed = sorted(
        [(filename, result) for filename, result, error in entries if result is not None],
        key=lambda pair: pair[1].result.match_score,
        reverse=True,
    )
    ranked = [
        RankedResult(rank=index, filename=filename, **result.model_dump())
        for index, (filename, result) in enumerate(passed, start=1)
    ]
    failed = [FailedResume(filename=filename, error=error) for filename, result, error in entries if error]
    return BatchResponse(ranked=ranked, failed=failed)


@router.post("/upload", response_model=BatchResponse)
async def screen_upload(
    request: UploadForm = Depends(UploadForm.as_form),
    files: list[UploadFile] = File(...),
    current_user=Depends(require_screening_quota),
    db: AsyncSession = Depends(get_db),
    screening_service: ScreenService = Depends(get_screen_service),
    pdf_extractor: PdfTextExtractor = Depends(get_pdf_text_extractor),
) -> BatchResponse:
    if not files:
        raise HTTPException(status_code=422, detail={"code": "missing_files", "message": "Upload at least one PDF resume."})
    if len(files) > 10:
        raise HTTPException(status_code=413, detail={"code": "too_many_files", "message": "Upload at most 10 PDF files."})
    batch_items: list[tuple[str, str]] = []
    failed: list[FailedResume] = []
    for file in files:
        filename = file.filename or "resume.pdf"
        if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=422, detail={"code": "invalid_file_type", "message": f"{filename} must be a PDF."})
        contents = await file.read(5 * 1024 * 1024 + 1)
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail={"code": "file_too_large", "message": f"{filename} exceeds the 5 MB limit."})
        if not contents.startswith(b"%PDF-"):
            raise HTTPException(status_code=422, detail={"code": "invalid_pdf", "message": f"{filename} is not a valid PDF."})
        try:
            resume_text = pdf_extractor(contents)
        except ScreeningError as exc:
            if exc.code == "invalid_pdf":
                failed.append(FailedResume(filename=filename, error=exc.message))
                continue
            raise as_http_error(exc) from exc
        if not resume_text.strip():
            failed.append(FailedResume(filename=filename, error="Scanned PDF not supported"))
            continue
        if len(resume_text) < 100:
            failed.append(FailedResume(filename=filename, error="Extracted resume text must be at least 100 characters."))
            continue
        batch_items.append((filename, resume_text[:15000]))

    if batch_items:
        batch_request = BatchRequest(
            job_description=request.job_description,
            resumes=[{"filename": filename, "resume_text": text} for filename, text in batch_items],
            required_skills=request.required_skills,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
        )
        result = await screen_batch(
            batch_request, current_user=current_user, db=db,
            screening_service=screening_service,
        )
        failed.extend(result.failed)
        return BatchResponse(ranked=result.ranked, failed=failed)
    return BatchResponse(ranked=[], failed=failed)
