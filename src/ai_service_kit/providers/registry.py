"""Provider registry for reusable embedding providers."""

from __future__ import annotations

from typing import TypeVar

from ..utils import normalize_name
from .base import BaseEmbeddingProvider

ProviderType = TypeVar("ProviderType", bound=type[BaseEmbeddingProvider])


class ProviderRegistry:
    """Registry of named provider classes."""

    def __init__(self) -> None:
        self._providers: dict[str, type[BaseEmbeddingProvider]] = {}

    def register(self, name: str, provider_class: type[BaseEmbeddingProvider]) -> None:
        key = normalize_name(name)
        if not issubclass(provider_class, BaseEmbeddingProvider):
            raise TypeError("Provider class must inherit from BaseEmbeddingProvider")
        self._providers[key] = provider_class

    def unregister(self, name: str) -> None:
        self._providers.pop(normalize_name(name), None)

    def get(self, name: str) -> type[BaseEmbeddingProvider]:
        return self._providers[normalize_name(name)]

    def has(self, name: str) -> bool:
        return normalize_name(name) in self._providers

    def list_names(self) -> list[str]:
        return sorted(self._providers)

    def copy(self) -> "ProviderRegistry":
        duplicate = ProviderRegistry()
        duplicate._providers = dict(self._providers)
        return duplicate


default_provider_registry = ProviderRegistry()
