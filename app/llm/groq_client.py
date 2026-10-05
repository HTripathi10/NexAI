"""Groq API client (OpenAI-compatible) with TTFT and tokens/sec measurement."""
import time
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()

GROQ_HEADERS = lambda: {
    "Authorization": f"Bearer {settings.groq_api_key}",
    "Content-Type": "application/json",
}


async def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> dict:
    """Non-streaming Groq chat completion."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    model = model or settings.groq_default_model
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    start = time.perf_counter()
    async with httpx.AsyncClient(base_url=settings.groq_base_url, timeout=60.0) as client:
        resp = await client.post(
            "/chat/completions",
            json=payload,
            headers=GROQ_HEADERS(),
        )
        if resp.status_code != 200:
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise ValueError(f"Groq API Error ({resp.status_code}): {err_msg}")
    total_latency_ms = (time.perf_counter() - start) * 1000
    data = resp.json()

    choice = data["choices"][0]
    usage = data.get("usage", {})
    content = choice["message"]["content"]
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    tokens_per_second = (
        output_tokens / (total_latency_ms / 1000) if total_latency_ms > 0 else None
    )

    return {
        "content": content,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_latency_ms": total_latency_ms,
        "ttft_ms": None,
        "tokens_per_second": tokens_per_second,
        "finish_reason": choice.get("finish_reason", "stop"),
    }


async def chat_completion_stream(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> dict:
    """Streaming Groq chat completion — measures TTFT accurately."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    model = model or settings.groq_default_model
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    start = time.perf_counter()
    ttft_ms: Optional[float] = None
    chunks: list[str] = []
    input_tokens = 0
    output_tokens = 0
    finish_reason = "stop"

    async with httpx.AsyncClient(base_url=settings.groq_base_url, timeout=60.0) as client:
        async with client.stream(
            "POST", "/chat/completions", json=payload, headers=GROQ_HEADERS()
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                try:
                    import json
                    err_data = json.loads(body)
                    err_msg = err_data.get("error", {}).get("message", body.decode("utf-8", errors="ignore"))
                except Exception:
                    err_msg = body.decode("utf-8", errors="ignore")
                raise ValueError(f"Groq API Error ({resp.status_code}): {err_msg}")
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                import json
                data = json.loads(raw)

                # grab usage from final chunk
                if data.get("usage"):
                    input_tokens = data["usage"].get("prompt_tokens", 0)
                    output_tokens = data["usage"].get("completion_tokens", 0)

                choices = data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                token = delta.get("content", "")
                if token and ttft_ms is None:
                    ttft_ms = (time.perf_counter() - start) * 1000
                if token:
                    chunks.append(token)
                if choices[0].get("finish_reason"):
                    finish_reason = choices[0]["finish_reason"]

    content = "".join(chunks)
    total_latency_ms = (time.perf_counter() - start) * 1000
    tokens_per_second = (
        output_tokens / (total_latency_ms / 1000) if total_latency_ms > 0 and output_tokens else None
    )

    return {
        "content": content,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_latency_ms": total_latency_ms,
        "ttft_ms": ttft_ms,
        "tokens_per_second": tokens_per_second,
        "finish_reason": finish_reason,
    }


async def list_models() -> list[str]:
    """Return available Groq text completion models."""
    if not settings.groq_api_key:
        return []
    try:
        async with httpx.AsyncClient(base_url=settings.groq_base_url, timeout=10.0) as client:
            resp = await client.get("/models", headers=GROQ_HEADERS())
            resp.raise_for_status()
            models_data = resp.json().get("data", [])
            # Filter for text output models and exclude audio/guard models if needed
            chat_models = []
            for m in models_data:
                mid = m.get("id", "")
                output_modalities = m.get("output_modalities", ["text"])
                if "text" in output_modalities and not mid.startswith("whisper") and "prompt-guard" not in mid:
                    chat_models.append(mid)
            return chat_models if chat_models else ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
    except Exception:
        return ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
