"""Reusable service-layer abstractions for AI applications."""

from .providers.embedding_base import (
    BaseEmbeddingProvider,
    EmbeddingAPIError,
    EmbeddingConfigError,
    EmbeddingError,
    EmbeddingRateLimitError,
    EmbeddingResult,
    EmbeddingUsage,
)
from .providers.factory import ProviderFactory
from .providers.llm_base import (
    BaseLLMProvider,
    LLMAPIError,
    LLMConfigError,
    LLMError,
    LLMMessage,
    LLMRateLimitError,
    LLMResponse,
    LLMUsage,
)
from .providers.llm_factory import LLMProviderFactory
from .providers.llm_registry import LLMProviderRegistry
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
    "BaseLLMProvider",
    "LLMError",
    "LLMConfigError",
    "LLMAPIError",
    "LLMRateLimitError",
    "LLMMessage",
    "LLMResponse",
    "LLMUsage",
    "ProviderFactory",
    "ProviderRegistry",
    "LLMProviderFactory",
    "LLMProviderRegistry",
    "ServiceContext",
    "check_health",
    "get_diagnostics",
    "get_metrics",
    "ping_service",
    "logging",
]
