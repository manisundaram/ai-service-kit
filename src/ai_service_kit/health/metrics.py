"""Metrics collector interface and no-op implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import MetricsSnapshot


class MetricsCollector(ABC):
    """Abstract interface for service metrics collection."""

    @abstractmethod
    def record_operation(self, operation_type: str, duration_ms: int, **kwargs: Any) -> None:
        """Record an operation latency observation."""

    @abstractmethod
    def record_error(self, error_type: str, provider: str | None = None, **kwargs: Any) -> None:
        """Record an error event."""

    @abstractmethod
    def record_event(self, event_name: str, **kwargs: Any) -> None:
        """Record an arbitrary domain event."""

    @abstractmethod
    def snapshot(self) -> MetricsSnapshot:
        """Return the current metrics snapshot."""


class NoOpMetricsCollector(MetricsCollector):
    """Metrics collector that preserves the call surface without storing state."""

    def record_operation(self, operation_type: str, duration_ms: int, **kwargs: Any) -> None:
        del operation_type, duration_ms, kwargs
        return None

    def record_error(self, error_type: str, provider: str | None = None, **kwargs: Any) -> None:
        del error_type, provider, kwargs
        return None

    def record_event(self, event_name: str, **kwargs: Any) -> None:
        del event_name, kwargs
        return None

    def snapshot(self) -> MetricsSnapshot:
        return MetricsSnapshot(
            performance={},
            usage={},
            reliability={},
            errors={},
        )
