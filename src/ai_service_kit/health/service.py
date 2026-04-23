"""Reusable operational service methods for health, diagnostics, and metrics."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable, Sequence

from .checks import BaseHealthCheck, aggregate_check_results
from .metrics import MetricsCollector, NoOpMetricsCollector
from .models import (
    CheckResult,
    ComponentStatus,
    DiagnosticsResponse,
    DiagnosticsSummary,
    HealthResponse,
    HealthStatus,
    MetricsSnapshot,
    ProviderDiagnosticsResult,
    ServiceConfiguration,
    VectorStoreDiagnosticsResult,
)

HealthCheckRunner = BaseHealthCheck | Callable[[], Awaitable[CheckResult]]
ComponentStatusResolver = Callable[[], Awaitable[Sequence[ComponentStatus]]]
ProviderDiagnosticsResolver = Callable[[], Awaitable[Sequence[ProviderDiagnosticsResult]]]
VectorStoreDiagnosticsResolver = Callable[[], Awaitable[Sequence[VectorStoreDiagnosticsResult]]]
BenchmarksResolver = Callable[[], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class ServiceContext:
    """Runtime context consumed by reusable operational service methods."""

    service_name: str
    service_version: str
    provider: str | None = None
    available_providers: tuple[str, ...] = ()
    vectorstore: str | None = None
    available_vectorstores: tuple[str, ...] = ()
    mock_mode: bool = False
    debug_mode: bool = False
    cors_enabled: bool = False
    masked_secrets: dict[str, str | None] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    metrics_collector: MetricsCollector = field(default_factory=NoOpMetricsCollector)
    health_checks: tuple[HealthCheckRunner, ...] = ()
    diagnostics_checks: tuple[HealthCheckRunner, ...] = ()
    provider_statuses: tuple[ComponentStatus, ...] = ()
    vectorstore_statuses: tuple[ComponentStatus, ...] = ()
    provider_diagnostics: tuple[ProviderDiagnosticsResult, ...] = ()
    vectorstore_diagnostics: tuple[VectorStoreDiagnosticsResult, ...] = ()
    performance_benchmarks: dict[str, Any] = field(default_factory=dict)
    provider_status_resolver: ComponentStatusResolver | None = None
    vectorstore_status_resolver: ComponentStatusResolver | None = None
    provider_diagnostics_resolver: ProviderDiagnosticsResolver | None = None
    vectorstore_diagnostics_resolver: VectorStoreDiagnosticsResolver | None = None
    benchmarks_resolver: BenchmarksResolver | None = None

    def configuration(self) -> ServiceConfiguration:
        """Return a normalized configuration snapshot for operational responses."""
        return ServiceConfiguration(
            provider=self.provider,
            available_providers=self.available_providers,
            vectorstore=self.vectorstore,
            available_vectorstores=self.available_vectorstores,
            mock_mode=self.mock_mode,
            debug_mode=self.debug_mode,
            cors_enabled=self.cors_enabled,
            masked_secrets=dict(self.masked_secrets),
            settings=dict(self.settings),
        )


async def _run_check(check: HealthCheckRunner) -> CheckResult:
    if isinstance(check, BaseHealthCheck):
        return await check.run()
    run = getattr(check, "run", None)
    if callable(run):
        return await run()
    return await check()


async def _run_checks(checks: Sequence[HealthCheckRunner]) -> tuple[CheckResult, ...]:
    if not checks:
        return ()
    return tuple(await asyncio.gather(*(_run_check(check) for check in checks)))


def _combine_health_status(statuses: Iterable[HealthStatus]) -> HealthStatus:
    normalized = tuple(statuses)
    if any(status in {HealthStatus.ERROR, HealthStatus.CRITICAL} for status in normalized):
        return HealthStatus.CRITICAL
    if any(status == HealthStatus.DEGRADED for status in normalized):
        return HealthStatus.DEGRADED
    return HealthStatus.HEALTHY


async def _resolve_component_statuses(
    static_statuses: Sequence[ComponentStatus],
    resolver: ComponentStatusResolver | None,
) -> tuple[ComponentStatus, ...]:
    if resolver is not None:
        return tuple(await resolver())
    return tuple(static_statuses)


async def _resolve_provider_diagnostics(
    static_results: Sequence[ProviderDiagnosticsResult],
    resolver: ProviderDiagnosticsResolver | None,
) -> tuple[ProviderDiagnosticsResult, ...]:
    if resolver is not None:
        return tuple(await resolver())
    return tuple(static_results)


async def _resolve_vectorstore_diagnostics(
    static_results: Sequence[VectorStoreDiagnosticsResult],
    resolver: VectorStoreDiagnosticsResolver | None,
) -> tuple[VectorStoreDiagnosticsResult, ...]:
    if resolver is not None:
        return tuple(await resolver())
    return tuple(static_results)


async def _resolve_benchmarks(
    static_benchmarks: dict[str, Any],
    resolver: BenchmarksResolver | None,
) -> dict[str, Any]:
    if resolver is not None:
        return dict(await resolver())
    return dict(static_benchmarks)


async def check_health(context: ServiceContext) -> HealthResponse:
    """Build a rich health response from a service context."""
    start_time = time.perf_counter()

    checks = await _run_checks(context.health_checks)
    providers = await _resolve_component_statuses(
        context.provider_statuses,
        context.provider_status_resolver,
    )
    vectorstores = await _resolve_component_statuses(
        context.vectorstore_statuses,
        context.vectorstore_status_resolver,
    )

    aggregate = aggregate_check_results(checks, metadata={"service": context.service_name})
    statuses = [aggregate.status, *(provider.status for provider in providers), *(store.status for store in vectorstores)]
    overall_status = _combine_health_status(statuses)
    response_time_ms = int((time.perf_counter() - start_time) * 1000)

    return HealthResponse(
        status=overall_status,
        version=context.service_version,
        response_time_ms=response_time_ms,
        checks=checks,
        providers=providers,
        vectorstores=vectorstores,
        configuration=context.configuration(),
        summary={
            "checks_count": len(checks),
            "providers_count": len(providers),
            "vectorstores_count": len(vectorstores),
            "mock_mode": context.mock_mode,
        },
    )


async def get_diagnostics(context: ServiceContext) -> DiagnosticsResponse:
    """Build a rich diagnostics response from a service context."""
    start_time = time.perf_counter()

    functional_checks = await _run_checks(context.diagnostics_checks)
    providers = await _resolve_provider_diagnostics(
        context.provider_diagnostics,
        context.provider_diagnostics_resolver,
    )
    vectorstores = await _resolve_vectorstore_diagnostics(
        context.vectorstore_diagnostics,
        context.vectorstore_diagnostics_resolver,
    )
    performance_benchmarks = await _resolve_benchmarks(
        context.performance_benchmarks,
        context.benchmarks_resolver,
    )

    total_checks = len(functional_checks) + len(providers) + len(vectorstores)
    passed = sum(1 for item in providers if item.status == HealthStatus.HEALTHY)
    passed += sum(1 for item in vectorstores if item.status == HealthStatus.HEALTHY)
    passed += sum(1 for item in functional_checks if item.status == HealthStatus.HEALTHY)

    failed = sum(1 for item in providers if item.status in {HealthStatus.ERROR, HealthStatus.CRITICAL})
    failed += sum(1 for item in vectorstores if item.status in {HealthStatus.ERROR, HealthStatus.CRITICAL})
    failed += sum(1 for item in functional_checks if item.status in {HealthStatus.ERROR, HealthStatus.CRITICAL})

    warnings = total_checks - passed - failed
    total_duration_ms = int((time.perf_counter() - start_time) * 1000)

    if failed == 0 and warnings == 0:
        overall_status = HealthStatus.HEALTHY
    elif passed > 0 or warnings > 0:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.CRITICAL

    return DiagnosticsResponse(
        status=overall_status,
        total_duration_ms=total_duration_ms,
        providers=providers,
        vectorstores=vectorstores,
        functional_checks=functional_checks,
        performance_benchmarks=performance_benchmarks,
        summary=DiagnosticsSummary(
            total_checks=total_checks,
            passed=passed,
            failed=failed,
            warnings=warnings,
        ),
    )


def get_metrics(context: ServiceContext) -> MetricsSnapshot:
    """Return a normalized metrics snapshot for a service context."""
    snapshot = context.metrics_collector.snapshot()
    return MetricsSnapshot(
        timestamp=snapshot.timestamp,
        collection_period=snapshot.collection_period,
        service_name=context.service_name,
        service_version=context.service_version,
        provider=context.provider,
        vectorstore=context.vectorstore,
        performance=dict(snapshot.performance),
        usage=dict(snapshot.usage),
        reliability=dict(snapshot.reliability),
        errors=dict(snapshot.errors),
    )
