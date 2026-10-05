"""Strict Pydantic v2 schemas for resume screening."""
from typing import Annotated, Literal

from fastapi import Form
from pydantic import BaseModel, ConfigDict, Field


class ScreeningSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Skill = Annotated[str, Field(min_length=1, max_length=80)]


class ScreenRequest(ScreeningSchema):
    job_description: str = Field(min_length=50, max_length=5000)
    resume_text: str = Field(min_length=100, max_length=15000)
    required_skills: list[Skill] | None = Field(default=None, max_length=100)
    provider: Literal["ollama", "groq"] = "ollama"
    model: str | None = Field(default=None, min_length=1, max_length=120)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [{
                "job_description": "Backend Engineer. 2+ years Python, FastAPI, Docker, PostgreSQL. Kubernetes is a plus.",
                "resume_text": "Aman Sharma. Backend developer, 3 years experience. Skills: Python, FastAPI, Docker, SQL...",
                "required_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Kubernetes"],
                "provider": "ollama",
                "model": "llama3.2:3b",
                "temperature": 0.1,
            }]
        },
    )


class ExtractedProfile(ScreeningSchema):
    candidate_name: str = Field(max_length=120)
    skills: list[Skill] = Field(max_length=200)
    experience_years: float = Field(ge=0, le=50)
    education: str = Field(max_length=1000)
    summary: str = Field(max_length=300)


class ScreenResult(ScreeningSchema):
    candidate_name: str
    match_score: int = Field(ge=0, le=100)
    matched_skills: list[Skill]
    missing_skills: list[Skill]
    experience_years: float = Field(ge=0, le=50)
    summary: str = Field(max_length=300)
    recommendation: Literal["shortlist", "maybe", "reject"]


class Metrics(ScreeningSchema):
    ttft_ms: float | None
    total_ms: float = Field(ge=0)
    tokens_per_sec: float | None = Field(default=None, ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)


class ScreenResponse(ScreeningSchema):
    result: ScreenResult
    provider: Literal["ollama", "groq"]
    model: str
    metrics: Metrics

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "examples": [{
            "result": {
                "candidate_name": "Aman Sharma", "match_score": 74,
                "matched_skills": ["Python", "FastAPI", "Docker"],
                "missing_skills": ["PostgreSQL", "Kubernetes"],
                "experience_years": 3.0,
                "summary": "Backend developer with Python and Docker experience.",
                "recommendation": "shortlist",
            },
            "provider": "ollama", "model": "llama3.2:3b",
            "metrics": {"ttft_ms": 1180, "total_ms": 6420, "tokens_per_sec": 14.2,
                        "input_tokens": 612, "output_tokens": 96, "cost_usd": 0.0},
        }]
    })


class ResumeInput(ScreeningSchema):
    filename: str = Field(min_length=1, max_length=255)
    resume_text: str = Field(min_length=100, max_length=15000)


class BatchRequest(ScreeningSchema):
    job_description: str = Field(min_length=50, max_length=5000)
    resumes: list[ResumeInput] = Field(min_length=1, max_length=10)
    required_skills: list[Skill] | None = Field(default=None, max_length=100)
    provider: Literal["ollama", "groq"] = "ollama"
    model: str | None = Field(default=None, min_length=1, max_length=120)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "examples": [{
            "job_description": "Backend Engineer needing Python, FastAPI, and PostgreSQL.",
            "resumes": [
                {"filename": "aman.pdf", "resume_text": "Aman Sharma has three years of Python backend development experience. " * 3},
                {"filename": "riya.pdf", "resume_text": "Riya Verma has two years of software engineering experience. " * 3},
            ],
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "provider": "ollama", "model": "llama3.2:3b", "temperature": 0.1,
        }]
    })


class UploadForm(ScreeningSchema):
    """Validated fields accompanying uploaded PDF files."""
    job_description: str = Field(min_length=50, max_length=5000)
    required_skills: list[Skill] | None = Field(default=None, max_length=100)
    provider: Literal["ollama", "groq"] = "ollama"
    model: str | None = Field(default=None, min_length=1, max_length=120)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)

    @classmethod
    def as_form(
        cls,
        job_description: Annotated[str, Form(min_length=50, max_length=5000)],
        required_skills: Annotated[list[Skill] | None, Form(max_length=100)] = None,
        provider: Annotated[Literal["ollama", "groq"], Form()] = "ollama",
        model: Annotated[str | None, Form(max_length=120)] = None,
        temperature: Annotated[float, Form(ge=0.0, le=2.0)] = 0.1,
    ) -> "UploadForm":
        return cls(
            job_description=job_description,
            required_skills=required_skills or None,
            provider=provider,
            model=model,
            temperature=temperature,
        )


class RankedResult(ScreeningSchema):
    rank: int = Field(ge=1)
    filename: str
    result: ScreenResult
    provider: Literal["ollama", "groq"]
    model: str
    metrics: Metrics


class FailedResume(ScreeningSchema):
    filename: str
    error: str


class BatchResponse(ScreeningSchema):
    ranked: list[RankedResult]
    failed: list[FailedResume]


class UploadResponse(BatchResponse):
    """Multipart upload response (same result structure as batch)."""


class ExtractedSkills(ScreeningSchema):
    skills: list[Skill] = Field(max_length=100)
