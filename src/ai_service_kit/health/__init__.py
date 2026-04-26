"""Reusable health and metrics abstractions."""

from .checks import BaseHealthCheck, aggregate_check_results
from .metrics import MetricsCollector, NoOpMetricsCollector
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
    "MetricsCollector",
    "MetricsSnapshot",
    "NoOpMetricsCollector",
    "ProviderDiagnosticsResult",
    "ServiceConfiguration",
    "SimpleHealthResponse",
    "ServiceContext",
    "VectorStoreDiagnosticsResult",
    "aggregate_check_results",
    "check_health",
    "get_diagnostics",
    "get_metrics",
]
