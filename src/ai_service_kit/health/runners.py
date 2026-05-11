"""Reusable diagnostics runners for readiness, config checks, and benchmarks."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from statistics import mean
from typing import Any

from .models import (
    CheckResult,
    HealthStatus,
    ProviderDiagnosticsResult,
    VectorStoreDiagnosticsResult,
)


def validate_required_config(
    name: str,
    required_values: Mapping[str, Any],
    *,
    summary: str = "Configuration validation",
) -> CheckResult:
    """Validate required config values and return a normalized check result."""
    def _is_missing(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False

    missing = tuple(key for key, value in required_values.items() if _is_missing(value))
    if missing:
        status = HealthStatus.DEGRADED
        result_summary = f"{summary}: missing required values"
    else:
        status = HealthStatus.HEALTHY
        result_summary = f"{summary}: valid"
    return CheckResult(
        name=name,
        status=status,
        summary=result_summary,
        details={"required_values": dict(required_values)},
        errors=tuple(f"Missing required config: {item}" for item in missing),
    )


async def run_provider_readiness_check(
    provider: str,
    check: Callable[[], Awaitable[bool]],
    *,
    configured: bool = True,
    available: bool | None = None,
    initialized: bool | None = None,
    models_available: Sequence[str] = (),
) -> ProviderDiagnosticsResult:
    """Run a provider readiness probe and normalize diagnostics output."""
    start_time = time.perf_counter()
    try:
        healthy = await check()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return ProviderDiagnosticsResult(
            provider=provider,
            status=HealthStatus.HEALTHY if healthy else HealthStatus.DEGRADED,
            duration_ms=duration_ms,
            configured=configured,
            available=available,
            initialized=initialized,
            models_available=tuple(models_available),
            error=None if healthy else "Provider readiness probe returned unhealthy",
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return ProviderDiagnosticsResult(
            provider=provider,
            status=HealthStatus.CRITICAL,
            duration_ms=duration_ms,
            configured=configured,
            available=available,
            initialized=initialized,
            models_available=tuple(models_available),
            error=str(exc),
        )


async def run_vectorstore_readiness_check(
    backend: str,
    check: Callable[[], Awaitable[bool]],
    *,
    configured: bool = True,
    available: bool | None = None,
    initialized: bool | None = None,
    collections_count: int = 0,
    default_collection: str | None = None,
) -> VectorStoreDiagnosticsResult:
    """Run a vector-store readiness probe and normalize diagnostics output."""
    start_time = time.perf_counter()
    try:
        healthy = await check()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return VectorStoreDiagnosticsResult(
            backend=backend,
            status=HealthStatus.HEALTHY if healthy else HealthStatus.DEGRADED,
            duration_ms=duration_ms,
            configured=configured,
            available=available,
            initialized=initialized,
            collections_count=collections_count,
            default_collection=default_collection,
            error=None if healthy else "Vector store readiness probe returned unhealthy",
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return VectorStoreDiagnosticsResult(
            backend=backend,
            status=HealthStatus.CRITICAL,
            duration_ms=duration_ms,
            configured=configured,
            available=available,
            initialized=initialized,
            collections_count=collections_count,
            default_collection=default_collection,
            error=str(exc),
        )


async def benchmark_operation(
    operation: Callable[[], Awaitable[Any]],
    *,
    iterations: int = 3,
    warmup_iterations: int = 1,
) -> dict[str, Any]:
    """Benchmark an async operation and return summary statistics."""
    if iterations <= 0:
        raise ValueError("iterations must be greater than 0")
    if warmup_iterations < 0:
        raise ValueError("warmup_iterations must be non-negative")

    for _ in range(warmup_iterations):
        await operation()

    durations: list[float] = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        await operation()
        durations.append((time.perf_counter() - start_time) * 1000)

    return {
        "iterations": iterations,
        "avg_ms": round(mean(durations), 2),
        "min_ms": round(min(durations), 2),
        "max_ms": round(max(durations), 2),
        "total_ms": round(sum(durations), 2),
    }


async def run_benchmark_suite(
    operations: Mapping[str, Callable[[], Awaitable[Any]]],
    *,
    iterations: int = 3,
    warmup_iterations: int = 1,
) -> dict[str, Any]:
    """Run a named benchmark suite and return per-operation summaries."""
    results: dict[str, Any] = {}
    for name, operation in operations.items():
        try:
            results[name] = await benchmark_operation(
                operation,
                iterations=iterations,
                warmup_iterations=warmup_iterations,
            )
        except Exception as exc:
            results[name] = {"error": str(exc)}
    return results