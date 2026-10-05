"""Ollama streaming client with TTFT and tokens/sec measurement."""
import time
import json
from typing import AsyncGenerator, Optional

import httpx

from app.config import get_settings

settings = get_settings()


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token (GPT standard heuristic)."""
    return max(1, len(text) // 4)


async def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> dict:
    """
    Non-streaming chat completion via Ollama /api/chat.
    Returns content + performance metrics.
    """
    model = model or settings.ollama_default_model
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens

    start = time.perf_counter()

    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=120.0) as client:
        resp = await client.post("/api/chat", json=payload)
        resp.raise_for_status()

    total_latency_ms = (time.perf_counter() - start) * 1000
    data = resp.json()

    content = data.get("message", {}).get("content", "")
    eval_count = data.get("eval_count", 0) or _estimate_tokens(content)
    prompt_eval_count = data.get("prompt_eval_count", 0) or _estimate_tokens(
        " ".join(m["content"] for m in messages)
    )
    eval_duration_ns = data.get("eval_duration", 0)
    tokens_per_second = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns else None

    return {
        "content": content,
        "model": model,
        "input_tokens": prompt_eval_count,
        "output_tokens": eval_count,
        "total_latency_ms": total_latency_ms,
        "ttft_ms": None,          # no TTFT in non-stream mode
        "tokens_per_second": tokens_per_second,
        "finish_reason": data.get("done_reason", "stop"),
    }


async def chat_completion_stream(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> dict:
    """
    Streaming chat completion via Ollama — measures TTFT accurately.
    Collects full response and returns dict (same schema as non-stream).
    """
    model = model or settings.ollama_default_model
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"temperature": temperature},
    }
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens

    start = time.perf_counter()
    ttft_ms: Optional[float] = None
    chunks: list[str] = []
    input_tokens = 0
    output_tokens = 0
    tokens_per_second: Optional[float] = None
    finish_reason = "stop"

    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=120.0) as client:
        async with client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token and ttft_ms is None:
                    ttft_ms = (time.perf_counter() - start) * 1000
                chunks.append(token)
                if data.get("done"):
                    input_tokens = data.get("prompt_eval_count", 0)
                    output_tokens = data.get("eval_count", 0)
                    eval_dur = data.get("eval_duration", 0)
                    if eval_dur and output_tokens:
                        tokens_per_second = output_tokens / (eval_dur / 1e9)
                    finish_reason = data.get("done_reason", "stop")

    content = "".join(chunks)
    total_latency_ms = (time.perf_counter() - start) * 1000

    if not input_tokens:
        input_tokens = _estimate_tokens(" ".join(m["content"] for m in messages))
    if not output_tokens:
        output_tokens = _estimate_tokens(content)

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
    """Return available Ollama models."""
    try:
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=10.0) as client:
            resp = await client.get("/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []
