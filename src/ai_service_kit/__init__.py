"""Reusable service-layer abstractions for AI applications."""

from .providers.base import (
    BaseEmbeddingProvider,
    EmbeddingAPIError,
    EmbeddingConfigError,
    EmbeddingError,
    EmbeddingRateLimitError,
    EmbeddingResult,
    EmbeddingUsage,
)
from .providers.factory import ProviderFactory
from .providers.registry import ProviderRegistry
from .health import ServiceContext, check_health, get_diagnostics, get_metrics, ping_service

# Logging module is available as ai_service_kit.logging
from . import logging

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingAPIError",
    "EmbeddingConfigError",
    "EmbeddingError",
    "EmbeddingRateLimitError",
    "EmbeddingResult",
    "EmbeddingUsage",
    "ProviderFactory",
    "ProviderRegistry",
    "ServiceContext",
    "check_health",
    "get_diagnostics",
    "get_metrics",
    "ping_service",
    "logging",
]
