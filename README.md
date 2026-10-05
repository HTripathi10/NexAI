# NexAI — AI Workspace

NexAI is a local-first AI workspace with a Streamlit interface and a FastAPI backend. It supports chat with local Ollama models or the Groq API, JWT-protected accounts, usage quotas and performance metrics, and AI-assisted resume screening.

## Features

- **Chat:** send messages to Ollama or Groq models and review response metrics.
- **Authentication:** register and sign in with passwords stored as hashes; protected API routes require a JWT bearer token.
- **Usage and quotas:** per-user daily and monthly token usage is stored in SQLite and requests are subject to configured limits.
- **Metrics:** inspect request latency, time to first token (TTFT), tokens per second, and usage summaries.
- **Resume screening:** compare resume text or PDF uploads against a job description, with matched and missing skills, a match score, and a recommendation. Batch screening supports up to 10 resumes.
- **Validation and errors:** Pydantic v2 schemas validate API inputs and outputs; API errors use a consistent JSON envelope.

## Requirements

- Python 3.10 or later
- Ollama running locally for local model inference
- A Groq API key only if you want to use Groq models

The dependencies, including `pypdf` for PDF uploads, are listed in `requirements.txt`.

## Run locally

Open a terminal in the project directory and install the dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a local environment file and update its values:

```bash
cp .env.example .env
```

Set `JWT_SECRET_KEY` to a private random value of at least 32 characters. Set `GROQ_API_KEY` if you plan to use Groq. Do not commit `.env` or share its secrets.

For local Ollama inference, install Ollama, then start its server and download a model:

```bash
ollama serve
```

In another terminal:

```bash
ollama pull llama3.2
```

Start the API and UI in separate terminals (with the virtual environment activated in each):

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
streamlit run streamlit_app.py
```

Open the Streamlit app at <http://localhost:8501>. The API is at <http://localhost:8000>; interactive API docs are at <http://localhost:8000/docs>.

The frontend defaults to `http://localhost:8000` for the API. For a different address, set `API_BASE` in `streamlit_app.py` or adapt the configuration for your deployment.

## Run with Docker Compose

Docker Compose starts Ollama, the API, and Streamlit:

```bash
docker compose up --build
```

In another terminal, download a model into the Ollama container:

```bash
docker exec ollama ollama pull llama3.2
```

Then open <http://localhost:8501>. To configure Groq or override the JWT secret and quotas, set the corresponding environment variables before starting Compose. Use a strong, private `JWT_SECRET_KEY` for any shared or production deployment.

## Configuration

Settings are read from environment variables and `.env` through Pydantic Settings.

| Variable | Default | Purpose |
| --- | --- | --- |
| `JWT_SECRET_KEY` | Development fallback in `app/config.py` | Secret used to sign JWTs. Set a private value outside local development. |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Access token lifetime in minutes. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address. |
| `OLLAMA_DEFAULT_MODEL` | `llama3.2` | Default local model. |
| `GROQ_API_KEY` | Unset | API key required for Groq. |
| `GROQ_DEFAULT_MODEL` | `openai/gpt-oss-20b` | Default Groq model. |
| `DAILY_TOKEN_QUOTA` | `50000` | Per-user daily token limit. |
| `MONTHLY_TOKEN_QUOTA` | `500000` | Per-user monthly token limit. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./usage.db` | Async SQLAlchemy database URL. |
| `DEBUG` | `false` | Enables SQLAlchemy debug logging. |

## API overview

Protected endpoints expect this header:

```text
Authorization: Bearer <access_token>
```

### Register and sign in

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"a-long-password"}'
```

```bash
curl -X POST http://localhost:8000/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"a-long-password"}'
```

The token response contains `access_token`, `token_type`, and `expires_in`.

### Chat

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"backend":"ollama","messages":[{"role":"user","content":"Hello!"}]}'
```

Set `backend` to `groq` to use the configured Groq account. Chat requests accept a bounded message list, temperature from `0` to `2`, and an optional maximum token count.

### Resume screening

The API supports:

- `POST /v1/screen` for a single resume supplied as text.
- `POST /v1/screen/batch` for up to 10 resumes supplied as text.
- `POST /v1/screen/upload` for up to 10 PDF files (up to 5 MB each).

All screening routes require authentication. Job descriptions and resume text have schema-defined length limits. PDF text is extracted for processing and resume text is not stored by the screening service.

Example single-resume request:

```json
{
  "job_description": "Backend engineer role requiring Python, FastAPI, Docker, and PostgreSQL experience.",
  "resume_text": "Paste at least 100 characters of resume text here...",
  "required_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
  "provider": "ollama",
  "model": "llama3.2",
  "temperature": 0.1
}
```

The result includes extracted candidate details, matched and missing skills, a match score, a recommendation, provider/model details, and performance metrics. The score combines skill overlap (80%) and experience (20%); recommendations are `shortlist` for scores of 70 or more, `maybe` for 40–69, and `reject` below 40.

### Usage, metrics, and health

| Endpoint | Authentication | Description |
| --- | --- | --- |
| `GET /v1/usage` | JWT required | Current user's token usage and quotas. |
| `GET /metrics` | JWT required | Aggregated request performance metrics. |
| `GET /health` | Public | Service health and configured providers. |
| `GET /docs` | Public | Interactive OpenAPI documentation. |

## Validation and error responses

Pydantic v2 models validate request fields, types, and configured size/range limits. Invalid requests return HTTP `422`. Other common statuses include `401` for invalid/missing authentication, `429` for exhausted quotas, and `503` when a required inference or PDF-processing service is unavailable.

Errors use a consistent JSON structure:

```json
{
  "error": {
    "code": "validation_error",
    "message": "body.resume_text: String should have at least 100 characters"
  }
}
```

## Development

Run the resume-screening tests with:

```bash
python -m pytest -q tests/test_screening.py
```

Run the benchmark against a running API with:

```bash
python benchmark.py
python benchmark.py --runs 3
python benchmark.py --token <access_token>
```

## Project layout

```text
app/
  api/v1/       Resume-screening API
  llm/          Ollama and Groq clients
  routes/       Auth, chat, metrics, and usage endpoints
  schemas/      Pydantic screening schemas
  services/     Resume-screening logic
streamlit_app.py  Streamlit user interface
benchmark.py      API benchmark utility
tests/            Automated tests
```
