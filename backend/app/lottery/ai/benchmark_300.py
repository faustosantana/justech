"""Compatibility shim — suite lives in app.lottery.ai.benchmark."""

from app.lottery.ai.benchmark import (  # noqa: F401
    build_benchmark_300,
    build_cases,
    compare_v2_v3,
    evaluate_case,
    run_benchmark,
    run_benchmark_300,
    write_evaluation_docs,
)

__all__ = [
    "build_benchmark_300",
    "build_cases",
    "compare_v2_v3",
    "evaluate_case",
    "run_benchmark",
    "run_benchmark_300",
    "write_evaluation_docs",
]
