import asyncio

from ai_service_kit.health import (
    HealthStatus,
    InMemoryMetricsCollector,
    benchmark_operation,
    run_benchmark_suite,
    run_provider_readiness_check,
    run_vectorstore_readiness_check,
    validate_required_config,
)


def test_validate_required_config_marks_missing_values() -> None:
    check = validate_required_config(
        "configuration",
        {
            "openai_api_key": None,
            "provider_type": "openai",
        },
    )

    assert check.status == HealthStatus.DEGRADED
    assert any("openai_api_key" in item for item in check.errors)


def test_run_provider_readiness_check_healthy() -> None:
    async def healthy_check() -> bool:
        return True

    result = asyncio.run(run_provider_readiness_check("openai", healthy_check, configured=True))
    assert result.status == HealthStatus.HEALTHY
    assert result.error is None


def test_run_vectorstore_readiness_check_failure() -> None:
    async def failing_check() -> bool:
        raise RuntimeError("connection failed")

    result = asyncio.run(run_vectorstore_readiness_check("chromadb", failing_check, configured=True))
    assert result.status == HealthStatus.CRITICAL
    assert "connection failed" in (result.error or "")


def test_benchmark_operation_returns_statistics() -> None:
    async def operation() -> str:
        return "ok"

    result = asyncio.run(benchmark_operation(operation, iterations=2, warmup_iterations=0))
    assert result["iterations"] == 2
    assert result["avg_ms"] >= 0


def test_run_benchmark_suite_collects_named_results() -> None:
    async def op_a() -> int:
        return 1

    async def op_b() -> int:
        return 2

    results = asyncio.run(
        run_benchmark_suite(
            {"a": op_a, "b": op_b},
            iterations=1,
            warmup_iterations=0,
        )
    )

    assert set(results.keys()) == {"a", "b"}
    assert results["a"]["iterations"] == 1


def test_in_memory_metrics_collector_records_operations_events_and_errors() -> None:
    collector = InMemoryMetricsCollector(collection_period="test-window")

    collector.record_operation("embed", 10)
    collector.record_operation("embed", 20)
    collector.record_event("collection_created", name="docs")
    collector.record_error("timeout", provider="openai")

    snapshot = collector.snapshot()

    assert snapshot.collection_period == "test-window"
    assert snapshot.performance["embed"]["total_count"] == 2
    assert snapshot.usage["events"]["collection_created"] == 1
    assert snapshot.errors["by_type"]["timeout"] == 1
    assert snapshot.errors["by_provider"]["openai"] == 1