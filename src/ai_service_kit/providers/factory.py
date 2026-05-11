"""Factory helpers for constructing provider instances from a registry."""

from __future__ import annotations

from typing import Any, Mapping

from .base import BaseEmbeddingProvider, EmbeddingConfigError
from .registry import ProviderRegistry, default_provider_registry
from .base import ProviderFactory as SharedProviderFactory


class ProviderFactory(SharedProviderFactory):
    """Create provider instances from a registry of provider classes."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        super().__init__(
            registry=registry or default_provider_registry,
            config_error_class=EmbeddingConfigError,
            family_label="embedding provider",
        )

    def create_provider(
        self,
        provider_name: str,
        config: Mapping[str, Any] | None = None,
    ) -> BaseEmbeddingProvider:
        return super().create_provider(provider_name, config)

    def register_provider(self, name: str, provider_class: type[BaseEmbeddingProvider]) -> None:
        super().register_provider(name, provider_class)
