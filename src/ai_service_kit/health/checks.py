"""Health check abstractions and aggregation helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from .models import CheckResult, HealthReport, HealthStatus


class BaseHealthCheck(ABC):
    """Abstract interface for a reusable health check."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable health check name."""

    @abstractmethod
    async def run(self) -> CheckResult:
        """Execute the health check and return a normalized result."""


def aggregate_check_results(
    results: Iterable[CheckResult],
    *,
    metadata: dict[str, object] | None = None,
) -> HealthReport:
    """Aggregate individual check results into an overall report."""
    checks = tuple(results)
    statuses = {result.status for result in checks}

    if HealthStatus.ERROR in statuses or HealthStatus.CRITICAL in statuses:
        overall_status = HealthStatus.CRITICAL
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY

    return HealthReport(
        status=overall_status,
        checks=checks,
        metadata=dict(metadata or {}),
    )
