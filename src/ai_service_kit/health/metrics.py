"""Metrics collector interface and no-op implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
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


@dataclass(slots=True)
class _OperationAggregate:
    total_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float | None = None
    max_duration_ms: float | None = None

    def record(self, duration_ms: int) -> None:
        self.total_count += 1
        self.total_duration_ms += float(duration_ms)
        if self.min_duration_ms is None or duration_ms < self.min_duration_ms:
            self.min_duration_ms = float(duration_ms)
        if self.max_duration_ms is None or duration_ms > self.max_duration_ms:
            self.max_duration_ms = float(duration_ms)

    def as_dict(self) -> dict[str, float | int]:
        avg_duration = self.total_duration_ms / self.total_count if self.total_count else 0.0
        return {
            "total_count": self.total_count,
            "avg_duration_ms": round(avg_duration, 2),
            "min_duration_ms": round(self.min_duration_ms or 0.0, 2),
            "max_duration_ms": round(self.max_duration_ms or 0.0, 2),
        }


class InMemoryMetricsCollector(MetricsCollector):
    """Default in-memory collector shape that services can extend."""

    def __init__(self, *, collection_period: str = "runtime") -> None:
        self._lock = Lock()
        self._collection_period = collection_period
        self._operations: dict[str, _OperationAggregate] = {}
        self._errors: dict[str, int] = defaultdict(int)
        self._errors_by_provider: dict[str, int] = defaultdict(int)
        self._events: dict[str, int] = defaultdict(int)

    def record_operation(self, operation_type: str, duration_ms: int, **kwargs: Any) -> None:
        del kwargs
        with self._lock:
            aggregate = self._operations.setdefault(operation_type, _OperationAggregate())
            aggregate.record(duration_ms)

    def record_error(self, error_type: str, provider: str | None = None, **kwargs: Any) -> None:
        del kwargs
        with self._lock:
            self._errors[error_type] += 1
            if provider:
                self._errors_by_provider[provider] += 1

    def record_event(self, event_name: str, **kwargs: Any) -> None:
        del kwargs
        with self._lock:
            self._events[event_name] += 1

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            operations_snapshot = {
                operation_name: aggregate.as_dict()
                for operation_name, aggregate in self._operations.items()
            }
            total_operations = sum(aggregate.total_count for aggregate in self._operations.values())
            total_errors = sum(self._errors.values())

            reliability = {
                "success_rate_percent": round(
                    100.0 if total_operations == 0 else (1 - (total_errors / total_operations)) * 100,
                    2,
                ),
                "total_operations": total_operations,
                "total_errors": total_errors,
            }

            return MetricsSnapshot(
                collection_period=self._collection_period,
                performance=operations_snapshot,
                usage={
                    "events": dict(self._events),
                    "operation_counts": {
                        operation_name: aggregate.total_count
                        for operation_name, aggregate in self._operations.items()
                    },
                },
                reliability=reliability,
                errors={
                    "by_type": dict(self._errors),
                    "by_provider": dict(self._errors_by_provider),
                },
            )
