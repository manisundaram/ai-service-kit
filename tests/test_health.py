import asyncio

from ai_service_kit.health import (
    CheckResult,
    ComponentKind,
    ComponentStatus,
    DiagnosticsResponse,
    DiagnosticsSummary,
    MetricsSnapshot,
    HealthResponse,
    HealthStatus,
    NoOpMetricsCollector,
    PingResponse,
    ProviderDiagnosticsResult,
    ServiceContext,
    ServiceConfiguration,
    SimpleHealthResponse,
    VectorStoreDiagnosticsResult,
    aggregate_check_results,
    check_health,
    get_diagnostics,
    get_metrics,
    ping_service,
)


class StaticCheck:
    def __init__(self, name: str, status: HealthStatus, summary: str) -> None:
        self._name = name
        self._status = status
        self._summary = summary

    @property
    def name(self) -> str:
        return self._name

    async def run(self) -> CheckResult:
        return CheckResult(name=self._name, status=self._status, summary=self._summary)


class StaticMetricsCollector(NoOpMetricsCollector):
    def snapshot(self) -> MetricsSnapshot:
        return MetricsSnapshot(
            collection_period="1h",
            performance={"requests": 10},
            usage={"providers": 1},
            reliability={"uptime_seconds": 60},
            errors={"total_lifetime": 0},
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


def test_rich_health_response_supports_generic_provider_and_vectorstore_status() -> None:
    response = HealthResponse(
        status=HealthStatus.HEALTHY,
        version="0.1.0",
        response_time_ms=12,
        providers=(
            ComponentStatus(
                name="claude",
                kind=ComponentKind.PROVIDER,
                status=HealthStatus.HEALTHY,
                configured=True,
                available=True,
                initialized=True,
            ),
        ),
        vectorstores=(
            ComponentStatus(
                name="chromadb",
                kind=ComponentKind.VECTORSTORE,
                status=HealthStatus.HEALTHY,
                configured=True,
                available=True,
                initialized=True,
            ),
        ),
        configuration=ServiceConfiguration(
            provider="claude",
            available_providers=("openai", "gemini", "claude"),
            vectorstore="chromadb",
            available_vectorstores=("chromadb",),
            mock_mode=False,
        ),
    )

    assert response.providers[0].name == "claude"
    assert response.vectorstores[0].name == "chromadb"
    assert response.configuration is not None
    assert response.configuration.available_providers[-1] == "claude"


def test_diagnostics_response_supports_expandable_backends() -> None:
    diagnostics = DiagnosticsResponse(
        status=HealthStatus.DEGRADED,
        total_duration_ms=35,
        providers=(
            ProviderDiagnosticsResult(
                provider="openai",
                status=HealthStatus.HEALTHY,
                configured=True,
                available=True,
                initialized=True,
                models_available=("text-embedding-3-small",),
                test_embedding_dimensions=1536,
            ),
            ProviderDiagnosticsResult(
                provider="claude",
                status=HealthStatus.DEGRADED,
                configured=False,
                available=None,
                initialized=False,
                error="not configured",
            ),
        ),
        vectorstores=(
            VectorStoreDiagnosticsResult(
                backend="chromadb",
                status=HealthStatus.HEALTHY,
                configured=True,
                available=True,
                initialized=True,
                collections_count=2,
                default_collection="default",
            ),
        ),
        summary=DiagnosticsSummary(total_checks=3, passed=2, failed=0, warnings=1),
    )

    assert diagnostics.providers[1].provider == "claude"
    assert diagnostics.vectorstores[0].backend == "chromadb"
    assert diagnostics.summary.warnings == 1


def test_simple_health_response_remains_available_for_compatibility() -> None:
    response = SimpleHealthResponse(status="healthy", version="1.0.0", provider="openai")

    assert response.status == "healthy"
    assert response.provider == "openai"


def test_check_health_uses_context_checks_and_component_statuses() -> None:
    context = ServiceContext(
        service_name="template-service",
        service_version="1.2.3",
        provider="openai",
        available_providers=("openai", "claude"),
        vectorstore="chromadb",
        available_vectorstores=("chromadb",),
        mock_mode=True,
        health_checks=(
            StaticCheck("startup", HealthStatus.HEALTHY, "ok"),
            StaticCheck("provider", HealthStatus.DEGRADED, "slow"),
        ),
        provider_statuses=(
            ComponentStatus(
                name="openai",
                kind=ComponentKind.PROVIDER,
                status=HealthStatus.HEALTHY,
                configured=True,
                available=True,
                initialized=True,
            ),
        ),
        vectorstore_statuses=(
            ComponentStatus(
                name="chromadb",
                kind=ComponentKind.VECTORSTORE,
                status=HealthStatus.HEALTHY,
                configured=True,
                available=True,
                initialized=True,
            ),
        ),
    )

    response = asyncio.run(check_health(context))

    assert response.status == HealthStatus.DEGRADED
    assert response.configuration is not None
    assert response.configuration.mock_mode is True
    assert len(response.checks) == 2
    assert response.summary["providers_count"] == 1


def test_get_diagnostics_aggregates_provider_and_vectorstore_results() -> None:
    async def provider_resolver() -> tuple[ProviderDiagnosticsResult, ...]:
        return (
            ProviderDiagnosticsResult(
                provider="openai",
                status=HealthStatus.HEALTHY,
                configured=True,
                available=True,
                initialized=True,
            ),
            ProviderDiagnosticsResult(
                provider="claude",
                status=HealthStatus.DEGRADED,
                configured=False,
                initialized=False,
                error="not configured",
            ),
        )

    async def vectorstore_resolver() -> tuple[VectorStoreDiagnosticsResult, ...]:
        return (
            VectorStoreDiagnosticsResult(
                backend="chromadb",
                status=HealthStatus.HEALTHY,
                configured=True,
                available=True,
                initialized=True,
            ),
        )

    async def benchmarks_resolver() -> dict[str, str]:
        return {"single_embedding_ms": "5.0ms"}

    context = ServiceContext(
        service_name="template-service",
        service_version="1.2.3",
        diagnostics_checks=(StaticCheck("vector_operations", HealthStatus.HEALTHY, "ok"),),
        provider_diagnostics_resolver=provider_resolver,
        vectorstore_diagnostics_resolver=vectorstore_resolver,
        benchmarks_resolver=benchmarks_resolver,
    )

    response = asyncio.run(get_diagnostics(context))

    assert response.status == HealthStatus.DEGRADED
    assert response.summary.total_checks == 4
    assert response.summary.passed == 3
    assert response.summary.warnings == 1
    assert response.performance_benchmarks["single_embedding_ms"] == "5.0ms"


def test_get_metrics_enriches_snapshot_with_service_metadata() -> None:
    context = ServiceContext(
        service_name="template-service",
        service_version="1.2.3",
        provider="openai",
        vectorstore="chromadb",
        metrics_collector=StaticMetricsCollector(),
    )

    snapshot = get_metrics(context)

    assert snapshot.service_name == "template-service"
    assert snapshot.service_version == "1.2.3"
    assert snapshot.provider == "openai"
    assert snapshot.vectorstore == "chromadb"
    assert snapshot.performance["requests"] == 10


def test_ping_service_returns_minimal_response_without_expensive_operations() -> None:
    context = ServiceContext(
        service_name="ping-test-service",
        service_version="2.1.0",
        provider="claude",
        vectorstore="chromadb",
        mock_mode=True,
        # Note: no health_checks, no resolvers - ping should work without them
    )

    response = ping_service(context)

    assert response.status == "ok"
    assert response.service_name == "ping-test-service"
    assert response.service_version == "2.1.0"
    assert response.timestamp is not None


def test_ping_response_model_supports_basic_service_identification() -> None:
    response = PingResponse(
        status="ok",
        service_name="example-service", 
        service_version="1.0.0",
    )

    assert response.status == "ok"
    assert response.service_name == "example-service"
    assert response.service_version == "1.0.0"
