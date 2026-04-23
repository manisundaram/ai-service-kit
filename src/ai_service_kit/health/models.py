"""Portable health and metrics models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..utils import utc_now_iso


class HealthStatus(StrEnum):
    """Common service health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    ERROR = "error"


class ComponentKind(StrEnum):
    """Kinds of operational components tracked by health systems."""

    PROVIDER = "provider"
    VECTORSTORE = "vectorstore"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    MOCK = "mock"
    CUSTOM = "custom"


@dataclass(slots=True, frozen=True)
class CheckResult:
    """Result from a single health check."""

    name: str
    status: HealthStatus
    summary: str
    duration_ms: int = 0
    details: dict[str, Any] = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    observed_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True, frozen=True)
class ComponentStatus:
    """Status for a named operational component such as a provider or vector store."""

    name: str
    kind: ComponentKind
    status: HealthStatus
    configured: bool = True
    available: bool | None = None
    initialized: bool | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    observed_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True, frozen=True)
class ServiceConfiguration:
    """Normalized service configuration details safe to expose in diagnostics."""

    provider: str | None = None
    available_providers: tuple[str, ...] = ()
    vectorstore: str | None = None
    available_vectorstores: tuple[str, ...] = ()
    mock_mode: bool = False
    debug_mode: bool = False
    cors_enabled: bool = False
    masked_secrets: dict[str, str | None] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class HealthReport:
    """Aggregated service health report."""

    status: HealthStatus
    checks: tuple[CheckResult, ...]
    generated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class HealthResponse:
    """Rich service health response suitable for a standard /health endpoint."""

    status: HealthStatus
    version: str
    timestamp: str = field(default_factory=utc_now_iso)
    response_time_ms: int = 0
    checks: tuple[CheckResult, ...] = ()
    providers: tuple[ComponentStatus, ...] = ()
    vectorstores: tuple[ComponentStatus, ...] = ()
    configuration: ServiceConfiguration | None = None
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class SimpleHealthResponse:
    """Small compatibility payload for lightweight health probes."""

    status: str = HealthStatus.HEALTHY
    version: str = ""
    provider: str = "unknown"
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass(slots=True, frozen=True)
class ProviderDiagnosticsResult:
    """Diagnostics result for a single provider implementation."""

    provider: str
    status: HealthStatus
    duration_ms: int = 0
    configured: bool = False
    available: bool | None = None
    initialized: bool | None = None
    mock_mode: bool = False
    models_available: tuple[str, ...] = ()
    test_embedding_dimensions: int | None = None
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class VectorStoreDiagnosticsResult:
    """Diagnostics result for a single vector store backend."""

    backend: str
    status: HealthStatus
    duration_ms: int = 0
    configured: bool = False
    available: bool | None = None
    initialized: bool | None = None
    collections_count: int = 0
    default_collection: str | None = None
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DiagnosticsSummary:
    """Top-level summary counts for diagnostics output."""

    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0


@dataclass(slots=True, frozen=True)
class DiagnosticsResponse:
    """Rich diagnostics response suitable for a standard /diagnostics endpoint."""

    status: HealthStatus
    timestamp: str = field(default_factory=utc_now_iso)
    total_duration_ms: int = 0
    providers: tuple[ProviderDiagnosticsResult, ...] = ()
    vectorstores: tuple[VectorStoreDiagnosticsResult, ...] = ()
    functional_checks: tuple[CheckResult, ...] = ()
    performance_benchmarks: dict[str, Any] = field(default_factory=dict)
    summary: DiagnosticsSummary = field(default_factory=DiagnosticsSummary)


@dataclass(slots=True, frozen=True)
class MetricsSnapshot:
    """Standardized metrics payload shape."""

    timestamp: str = field(default_factory=utc_now_iso)
    collection_period: str = "lifetime"
    service_name: str | None = None
    service_version: str | None = None
    provider: str | None = None
    vectorstore: str | None = None
    performance: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    reliability: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, Any] = field(default_factory=dict)
