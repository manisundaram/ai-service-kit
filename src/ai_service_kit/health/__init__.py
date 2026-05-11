"""Reusable health and metrics abstractions."""

from .checks import BaseHealthCheck, aggregate_check_results
from .fastapi import apply_operational_middleware, register_operational_endpoints
from .metrics import InMemoryMetricsCollector, MetricsCollector, NoOpMetricsCollector
from .models import (
    CheckResult,
    ComponentKind,
    ComponentStatus,
    DiagnosticsResponse,
    DiagnosticsSummary,
    HealthReport,
    HealthResponse,
    HealthStatus,
    MetricsSnapshot,
    PingResponse,
    ProviderDiagnosticsResult,
    ServiceConfiguration,
    SimpleHealthResponse,
    VectorStoreDiagnosticsResult,
)
from .runners import (
    benchmark_operation,
    run_benchmark_suite,
    run_provider_readiness_check,
    run_vectorstore_readiness_check,
    validate_required_config,
)
from .service import ServiceContext, check_health, get_diagnostics, get_metrics, ping_service

__all__ = [
    "BaseHealthCheck",
    "CheckResult",
    "ComponentKind",
    "ComponentStatus",
    "DiagnosticsResponse",
    "DiagnosticsSummary",
    "HealthReport",
    "HealthResponse",
    "HealthStatus",
    "InMemoryMetricsCollector",
    "MetricsCollector",
    "MetricsSnapshot",
    "NoOpMetricsCollector",
    "ProviderDiagnosticsResult",
    "ServiceConfiguration",
    "SimpleHealthResponse",
    "ServiceContext",
    "VectorStoreDiagnosticsResult",
    "aggregate_check_results",
    "apply_operational_middleware",
    "benchmark_operation",
    "check_health",
    "get_diagnostics",
    "get_metrics",
    "register_operational_endpoints",
    "run_benchmark_suite",
    "run_provider_readiness_check",
    "run_vectorstore_readiness_check",
    "validate_required_config",
    "ping_service",
]
