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
class HealthReport:
    """Aggregated service health report."""

    status: HealthStatus
    checks: tuple[CheckResult, ...]
    generated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class MetricsSnapshot:
    """Standardized metrics payload shape."""

    timestamp: str = field(default_factory=utc_now_iso)
    collection_period: str = "lifetime"
    performance: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    reliability: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, Any] = field(default_factory=dict)
