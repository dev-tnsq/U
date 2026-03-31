from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.twin.benchmark import (
    aggregate_model_score,
    build_prompt_benchmark,
    prompt_suite,
    select_best_model,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark local ollama models and recommend defaults.")
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Optional model names. If omitted, uses installed models from 'ollama list'.",
    )
    parser.add_argument(
        "--max-models",
        type=int,
        default=3,
        help="Maximum number of models to benchmark (default: 3).",
    )
    return parser.parse_args()


def _parse_ollama_list_output(raw_output: str) -> list[str]:
    models: list[str] = []
    for line in raw_output.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.lower().startswith("name"):
            continue
        models.append(cleaned.split()[0])
    return models


def discover_installed_models() -> list[str]:
    try:
        completed = subprocess.run(
            ["ollama", "list"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []

    if completed.returncode != 0:
        return []

    return _parse_ollama_list_output(completed.stdout)


def select_models(candidates: list[str], max_models: int) -> list[str]:
    if not candidates:
        return []

    bounded_max = max(1, max_models)
    target = min(len(candidates), bounded_max)
    if len(candidates) >= 2 and target < 2:
        target = 2

    return candidates[:target]


def normalize_model_inputs(tokens: list[str] | None) -> list[str]:
    if not tokens:
        return []

    normalized: list[str] = []
    for token in tokens:
        for part in token.split(","):
            candidate = part.strip()
            if candidate:
                normalized.append(candidate)
    return normalized


def run_model_prompt(model_name: str, prompt: str) -> tuple[str, float]:
    started = perf_counter()
    completed = subprocess.run(
        ["ollama", "run", model_name, prompt],
        check=False,
        capture_output=True,
        text=True,
    )
    elapsed_ms = (perf_counter() - started) * 1000.0

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(stderr or f"ollama run exited with {completed.returncode}")

    return (completed.stdout or "").strip(), elapsed_ms


def benchmark_model(model_name: str, prompts: tuple[str, ...]) -> dict | None:
    prompt_results = []
    failures: list[dict[str, str]] = []

    for prompt in prompts:
        try:
            response, latency_ms = run_model_prompt(model_name, prompt)
        except Exception as exc:
            failures.append({"prompt": prompt, "error": str(exc)})
            continue

        prompt_results.append(build_prompt_benchmark(prompt, response, latency_ms))

    if not prompt_results:
        return None

    summary = aggregate_model_score(model_name, prompt_results)
    payload = asdict(summary)
    payload["failures"] = failures
    return payload


def _resolve_report_path() -> Path:
    primary = (
        Path.home()
        / "Library"
        / "Application Support"
        / "U"
        / "runtime"
        / "benchmarks"
        / "latest_model_benchmark.json"
    )
    fallback = Path.home() / "U" / "data" / "runtime" / "benchmarks" / "latest_model_benchmark.json"

    try:
        primary.parent.mkdir(parents=True, exist_ok=True)
        return primary
    except OSError:
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback


def write_report(payload: dict) -> Path:
    path = _resolve_report_path()
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
    except OSError:
        fallback = Path.home() / "U" / "data" / "runtime" / "benchmarks" / "latest_model_benchmark.json"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        fallback.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return fallback


def main() -> int:
    args = parse_args()

    normalized_models = normalize_model_inputs(args.models)
    candidates = normalized_models if normalized_models else discover_installed_models()
    models = select_models(candidates, args.max_models)

    if not models:
        print("No models found. Install with 'ollama pull <model>' or pass --models.")
        return 1

    prompts = prompt_suite()
    model_results: list[dict] = []

    for model_name in models:
        print(f"[benchmark] running {model_name}")
        result = benchmark_model(model_name, prompts)
        if result is not None:
            model_results.append(result)

    if not model_results:
        print("No model was successfully benchmarked.")
        return 2

    summaries = [
        aggregate_model_score(
            item["model_name"],
            [
                build_prompt_benchmark(
                    prompt_result["prompt"],
                    prompt_result["response"],
                    float(prompt_result["latency_ms"]),
                )
                for prompt_result in item["prompt_results"]
            ],
        )
        for item in model_results
    ]
    best = select_best_model(summaries)
    assert best is not None

    report = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "prompt_count": len(prompts),
        "benchmarked_models": model_results,
        "recommended": {
            "runtime": "ollama",
            "profile": best.recommended_profile,
            "model_name": best.model_name,
            "overall_score": best.overall_score,
        },
    }

    report_path = write_report(report)

    print(f"Report written: {report_path}")
    print("Recommended environment values:")
    print("U_MODEL_RUNTIME=ollama")
    print(f"U_MODEL_PROFILE={best.recommended_profile}")
    print(f"U_MODEL_NAME={best.model_name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
