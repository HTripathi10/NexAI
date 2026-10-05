"""Resume screening tests with injected fake provider and database dependencies."""
import asyncio
from functools import wraps
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.api.v1.screen import (
    get_pdf_text_extractor,
    get_screen_service,
    require_screening_quota,
)
from app.database import get_db
from app.main import app
from app.schemas.screening import Metrics, ScreenRequest, ScreenResponse, ScreenResult
from app.services import screener


def async_test(function):
    """Run an async test without requiring a pytest asyncio plugin."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        return asyncio.run(function(*args, **kwargs))
    return wrapped


def make_response(name: str, score: int) -> ScreenResponse:
    return ScreenResponse(
        result=ScreenResult(
            candidate_name=name,
            match_score=score,
            matched_skills=["Python"],
            missing_skills=[],
            experience_years=3,
            summary="Relevant backend experience.",
            recommendation="shortlist" if score >= 70 else "maybe" if score >= 40 else "reject",
        ),
        provider="ollama",
        model="fake-model",
        metrics=Metrics(ttft_ms=10, total_ms=20, tokens_per_sec=5, input_tokens=8, output_tokens=4, cost_usd=0),
    )


async def client_with_overrides(overrides: dict):
    app.dependency_overrides.update(overrides)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return client


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@async_test
async def test_valid_screen_uses_fake_provider_dependency():
    async def fake_screen(request, username, db):
        assert request.provider == "ollama"
        return make_response("Aman Sharma", 74)

    async def fake_db():
        yield object()

    async def fake_user():
        return SimpleNamespace(username="test-user")

    client = await client_with_overrides({
        get_screen_service: lambda: fake_screen,
        require_screening_quota: fake_user,
        get_db: fake_db,
    })
    async with client:
        response = await client.post("/v1/screen", json={
            "job_description": "Backend Engineer needing Python and database skills for a growing software team.",
            "resume_text": "Aman Sharma has three years building Python API services and backend systems. " * 2,
            "required_skills": ["Python"],
        })
    assert response.status_code == 200
    assert response.json()["result"]["candidate_name"] == "Aman Sharma"


@async_test
async def test_invalid_json_retries_once_then_succeeds(monkeypatch):
    outputs = iter(["not-json", '{"candidate_name":"Aman","skills":[],"experience_years":3,"education":"","summary":"Backend developer"}'])
    prompts = []

    async def fake_call(provider, model, prompt, temperature, schema):
        prompts.append(prompt)
        return {"content": next(outputs), "input_tokens": 2, "output_tokens": 2,
                "ttft_ms": 1.0, "total_ms": 3.0, "tokens_per_sec": 1.0}

    monkeypatch.setattr(screener, "_provider_call", fake_call)
    parsed, calls = await screener._validated_call("ollama", "fake", "extract", 0.1, screener.ExtractedProfile)
    assert parsed.candidate_name == "Aman"
    assert len(calls) == 2
    assert "failed schema validation" in prompts[1]


@async_test
async def test_double_invalid_json_raises_422(monkeypatch):
    async def fake_call(provider, model, prompt, temperature, schema):
        return {"content": "{bad", "input_tokens": 2, "output_tokens": 1,
                "ttft_ms": None, "total_ms": 1.0, "tokens_per_sec": None}

    monkeypatch.setattr(screener, "_provider_call", fake_call)
    with pytest.raises(screener.ScreeningError) as error:
        await screener._validated_call("ollama", "fake", "extract", 0.1, screener.ExtractedProfile)
    assert error.value.status_code == 422


@async_test
async def test_missing_token_returns_401():
    client = await client_with_overrides({get_db: lambda: None})
    async with client:
        response = await client.post("/v1/screen", json={
            "job_description": "Backend Engineer requiring Python for service development.",
            "resume_text": "This is a sufficiently long resume describing backend engineering experience.",
        })
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@async_test
async def test_quota_exceeded_returns_429():
    async def over_quota():
        raise HTTPException(status_code=429, detail={"code": "quota_exceeded", "message": "Daily token quota exceeded."})

    async def fake_db():
        yield object()

    client = await client_with_overrides({require_screening_quota: over_quota, get_db: fake_db})
    async with client:
        response = await client.post("/v1/screen", json={
            "job_description": "Backend Engineer requiring Python for service development.",
            "resume_text": "This is a sufficiently long resume describing backend engineering experience.",
        })
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "quota_exceeded"


@async_test
async def test_scanned_pdf_is_reported_as_failed():
    async def fake_screen(request, username, db):
        return make_response("Candidate", 50)

    async def fake_user():
        return SimpleNamespace(username="test-user")

    async def fake_db():
        yield object()

    client = await client_with_overrides({
        require_screening_quota: fake_user,
        get_db: fake_db,
        get_screen_service: lambda: fake_screen,
        get_pdf_text_extractor: lambda: (lambda _: "  "),
    })
    async with client:
        response = await client.post(
            "/v1/screen/upload",
            data={"job_description": "Backend Engineer requiring Python for service development."},
            files=[("files", ("scan.pdf", b"%PDF-1.4\n", "application/pdf"))],
        )
    assert response.status_code == 200
    assert response.json()["failed"] == [{"filename": "scan.pdf", "error": "Scanned PDF not supported"}]


@async_test
async def test_batch_results_are_ranked_descending():
    async def fake_screen(request, username, db):
        score = 82 if "strong" in request.resume_text else 45
        return make_response("Strong Candidate" if score == 82 else "Maybe Candidate", score)

    async def fake_user():
        return SimpleNamespace(username="test-user")

    async def fake_db():
        yield object()

    client = await client_with_overrides({
        require_screening_quota: fake_user,
        get_db: fake_db,
        get_screen_service: lambda: fake_screen,
    })
    async with client:
        response = await client.post("/v1/screen/batch", json={
            "job_description": "Backend Engineer requiring Python for service development.",
            "resumes": [
                {"filename": "maybe.pdf", "resume_text": "ordinary candidate resume text of adequate length." * 3},
                {"filename": "strong.pdf", "resume_text": "strong candidate resume text of adequate length." * 3},
            ],
            "required_skills": ["Python"],
        })
    assert response.status_code == 200
    assert [row["filename"] for row in response.json()["ranked"]] == ["strong.pdf", "maybe.pdf"]
