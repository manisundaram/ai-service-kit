"""Factory helpers for constructing LLM provider instances from a registry."""

from __future__ import annotations

from typing import Any, Mapping

from .llm_base import BaseLLMProvider, LLMConfigError
from .llm_registry import LLMProviderRegistry, default_llm_provider_registry
from .base import ProviderFactory as SharedProviderFactory


class LLMProviderFactory(SharedProviderFactory):
    """Create LLM provider instances from a registry of provider classes."""

    def __init__(self, registry: LLMProviderRegistry | None = None) -> None:
        super().__init__(
            registry=registry or default_llm_provider_registry,
            config_error_class=LLMConfigError,
            family_label="llm provider",
        )

    def create_provider(
        self,
        provider_name: str,
        config: Mapping[str, Any] | None = None,
    ) -> BaseLLMProvider:
        return super().create_provider(provider_name, config)

    def register_provider(self, name: str, provider_class: type[BaseLLMProvider]) -> None:
        super().register_provider(name, provider_class)