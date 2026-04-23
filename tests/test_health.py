from ai_service_kit.health import (
    CheckResult,
    HealthStatus,
    NoOpMetricsCollector,
    aggregate_check_results,
)


def test_aggregate_check_results_degraded_when_any_check_degraded() -> None:
    report = aggregate_check_results(
        [
            CheckResult(name="providers", status=HealthStatus.HEALTHY, summary="ok"),
            CheckResult(name="vectorstore", status=HealthStatus.DEGRADED, summary="slow"),
        ],
        metadata={"service": "ai-service-kit"},
    )

    assert report.status == HealthStatus.DEGRADED
    assert report.metadata["service"] == "ai-service-kit"
    assert len(report.checks) == 2


def test_aggregate_check_results_escalates_error_to_critical() -> None:
    report = aggregate_check_results(
        [CheckResult(name="providers", status=HealthStatus.ERROR, summary="failed")]
    )

    assert report.status == HealthStatus.CRITICAL


def test_noop_metrics_collector_returns_empty_snapshot() -> None:
    collector = NoOpMetricsCollector()
    collector.record_operation("embed", 12, provider="dummy")
    collector.record_error("timeout", provider="dummy")
    collector.record_event("collection_created", name="docs")

    snapshot = collector.snapshot()

    assert snapshot.collection_period == "lifetime"
    assert snapshot.performance == {}
    assert snapshot.usage == {}
    assert snapshot.reliability == {}
    assert snapshot.errors == {}
