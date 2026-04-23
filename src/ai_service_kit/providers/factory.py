"""Factory helpers for constructing provider instances from a registry."""

from __future__ import annotations

from typing import Any, Mapping

from ..utils import normalize_name
from .base import BaseEmbeddingProvider, EmbeddingConfigError
from .registry import ProviderRegistry, default_provider_registry


class ProviderFactory:
    """Create provider instances from a registry of provider classes."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self.registry = registry or default_provider_registry

    def create_provider(
        self,
        provider_name: str,
        config: Mapping[str, Any] | None = None,
    ) -> BaseEmbeddingProvider:
        normalized_name = normalize_name(provider_name)

        if not self.registry.has(normalized_name):
            available = ", ".join(self.registry.list_names()) or "none"
            raise EmbeddingConfigError(
                f"Unsupported embedding provider: '{normalized_name}'. Available providers: {available}",
                provider=normalized_name,
            )

        provider_class = self.registry.get(normalized_name)
        try:
            return provider_class(config)
        except EmbeddingConfigError:
            raise
        except Exception as exc:
            raise EmbeddingConfigError(
                f"Failed to initialize {normalized_name} provider: {exc}",
                provider=normalized_name,
            ) from exc

    def get_available_providers(self) -> list[str]:
        return self.registry.list_names()

    def register_provider(self, name: str, provider_class: type[BaseEmbeddingProvider]) -> None:
        self.registry.register(name, provider_class)
