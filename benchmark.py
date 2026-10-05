#!/usr/bin/env python3
"""
benchmark.py — Compare Ollama vs Groq on identical prompts.

Usage:
    python benchmark.py
    python benchmark.py --token YOUR_JWT_TOKEN
    python benchmark.py --runs 3
"""
import argparse
import asyncio
import statistics
import time
from typing import Optional
import httpx

API_BASE = "http://localhost:8000"

PROMPTS = [
    "Explain the concept of attention mechanism in transformers in 3 sentences.",
    "Write a Python function to compute Fibonacci numbers using memoization.",
    "What is the difference between TCP and UDP? Give 3 key differences.",
    "Summarize the CAP theorem in simple terms.",
    "Write a haiku about machine learning.",
]


def print_table(rows: list[dict], title: str):
    """Pretty-print a table with borders."""
    if not rows:
        return
    headers = list(rows[0].keys())
    widths = {h: max(len(str(h)), max(len(str(r[h])) for r in rows)) for h in headers}
    sep = "+" + "+".join("-" * (widths[h] + 2) for h in headers) + "+"
    header_row = "|" + "|".join(f" {h:<{widths[h]}} " for h in headers) + "|"

    print(f"\n{'='*len(sep)}")
    print(f" {title}")
    print(f"{'='*len(sep)}")
    print(sep)
    print(header_row)
    print(sep)
    for row in rows:
        print("|" + "|".join(f" {str(row[h]):<{widths[h]}} " for h in headers) + "|")
    print(sep)


async def get_token(username: str = "benchmark_user", password: str = "bench12345") -> str:
    """Register+login a benchmark user, return JWT."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15) as client:
        # Try register (may already exist)
        await client.post("/v1/auth/register", json={"username": username, "password": password})
        resp = await client.post(
            "/v1/auth/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def run_single(
    client: httpx.AsyncClient,
    token: str,
    prompt: str,
    backend: str,
    model: Optional[str],
    run_id: int,
) -> dict:
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "backend": backend,
        "stream": True,       # always stream to capture TTFT
        "temperature": 0.1,   # low temp for consistency
        "max_tokens": 200,
    }
    if model:
        payload["model"] = model

    start = time.perf_counter()
    resp = await client.post(
        "/v1/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    elapsed = (time.perf_counter() - start) * 1000

    if resp.status_code == 429:
        return {"error": "quota_exceeded", "prompt_idx": run_id}
    if resp.status_code != 200:
        return {"error": resp.text[:100], "prompt_idx": run_id}

    data = resp.json()
    m = data.get("metrics", {})
    return {
        "prompt_preview": prompt[:40] + "…",
        "backend": backend,
        "model": m.get("model", model or "?"),
        "ttft_ms": m.get("ttft_ms"),
        "latency_ms": m.get("total_latency_ms"),
        "tok_per_sec": m.get("tokens_per_second"),
        "in_tok": m.get("input_tokens", 0),
        "out_tok": m.get("output_tokens", 0),
    }


async def benchmark(token: str, runs: int = 1):
    results = {"ollama": [], "groq": []}

    async with httpx.AsyncClient(base_url=API_BASE, timeout=180) as client:
        for run in range(runs):
            print(f"\n▶ Run {run+1}/{runs}")
            for i, prompt in enumerate(PROMPTS):
                print(f"  Prompt {i+1}/{len(PROMPTS)}: {prompt[:50]}…")

                # Ollama
                print(f"    [ollama] ", end="", flush=True)
                ollama_result = await run_single(client, token, prompt, "ollama", None, i)
                if "error" not in ollama_result:
                    results["ollama"].append(ollama_result)
                    print(f"✓ {ollama_result['latency_ms']:.0f}ms | TTFT: {ollama_result.get('ttft_ms') or 'N/A'}")
                else:
                    print(f"✗ {ollama_result['error']}")

                # Groq
                print(f"    [groq]   ", end="", flush=True)
                groq_result = await run_single(client, token, prompt, "groq", None, i)
                if "error" not in groq_result:
                    results["groq"].append(groq_result)
                    print(f"✓ {groq_result['latency_ms']:.0f}ms | TTFT: {groq_result.get('ttft_ms') or 'N/A'}")
                else:
                    print(f"✗ {groq_result['error']}")

    # ── Per-prompt comparison table ───────────────────────────────────────────
    comparison_rows = []
    for r in results["ollama"]:
        gr = next((g for g in results["groq"] if g["prompt_preview"] == r["prompt_preview"]), None)
        row = {
            "Prompt": r["prompt_preview"],
            "Ollama TTFT (ms)": f"{r['ttft_ms']:.0f}" if r.get("ttft_ms") else "N/A",
            "Ollama Lat (ms)": f"{r['latency_ms']:.0f}",
            "Ollama tok/s": f"{r['tok_per_sec']:.1f}" if r.get("tok_per_sec") else "N/A",
            "Groq TTFT (ms)": f"{gr['ttft_ms']:.0f}" if gr and gr.get("ttft_ms") else "N/A",
            "Groq Lat (ms)": f"{gr['latency_ms']:.0f}" if gr else "N/A",
            "Groq tok/s": f"{gr['tok_per_sec']:.1f}" if gr and gr.get("tok_per_sec") else "N/A",
            "Faster?": "🟢 Ollama" if gr and r["latency_ms"] < gr["latency_ms"] else "🟡 Groq",
        }
        comparison_rows.append(row)
    print_table(comparison_rows, "Per-Prompt Comparison: Ollama vs Groq")

    # ── Summary stats ─────────────────────────────────────────────────────────
    def summarize(data: list[dict]) -> dict:
        latencies = [d["latency_ms"] for d in data if d.get("latency_ms")]
        ttfts = [d["ttft_ms"] for d in data if d.get("ttft_ms")]
        tps_list = [d["tok_per_sec"] for d in data if d.get("tok_per_sec")]
        return {
            "Runs": len(data),
            "Avg Latency (ms)": f"{statistics.mean(latencies):.0f}" if latencies else "N/A",
            "P50 Latency (ms)": f"{statistics.median(latencies):.0f}" if latencies else "N/A",
            "Avg TTFT (ms)": f"{statistics.mean(ttfts):.0f}" if ttfts else "N/A",
            "Avg tok/s": f"{statistics.mean(tps_list):.1f}" if tps_list else "N/A",
        }

    summary_rows = []
    for backend, data in results.items():
        if data:
            row = {"Backend": backend.upper(), **summarize(data)}
            summary_rows.append(row)
    print_table(summary_rows, "Summary Statistics")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print("\n🔍 VERDICT")
    if results["ollama"] and results["groq"]:
        ol_avg = statistics.mean(r["latency_ms"] for r in results["ollama"] if r.get("latency_ms"))
        gr_avg = statistics.mean(r["latency_ms"] for r in results["groq"] if r.get("latency_ms"))
        if ol_avg < gr_avg:
            print(f"  Ollama is {(gr_avg/ol_avg):.1f}x faster on average ({ol_avg:.0f}ms vs {gr_avg:.0f}ms)")
        else:
            print(f"  Groq is {(ol_avg/gr_avg):.1f}x faster on average ({gr_avg:.0f}ms vs {ol_avg:.0f}ms)")
        print("  Note: Groq quality = cloud model; Ollama quality depends on your local model.")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Ollama vs Groq")
    parser.add_argument("--token", default=None, help="JWT bearer token (auto-created if omitted)")
    parser.add_argument("--runs", type=int, default=1, help="Number of benchmark runs")
    args = parser.parse_args()

    print("🚀 NexAI Benchmark: Ollama vs Groq")
    print(f"   API: {API_BASE}  |  Prompts: {len(PROMPTS)}  |  Runs: {args.runs}")

    token = args.token
    if not token:
        print("   Creating benchmark user...")
        token = await get_token()
        print("   ✓ Got JWT token")

    await benchmark(token, args.runs)


if __name__ == "__main__":
    asyncio.run(main())
