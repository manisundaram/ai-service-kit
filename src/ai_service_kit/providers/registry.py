"""Provider registry for reusable embedding providers."""

from __future__ import annotations

from .base import BaseEmbeddingProvider, ProviderRegistry as SharedProviderRegistry


class ProviderRegistry(SharedProviderRegistry):
    """Embedding-specific registry preserving the existing public API."""

    def __init__(self) -> None:
        super().__init__(provider_base_class=BaseEmbeddingProvider)


default_provider_registry = ProviderRegistry()
