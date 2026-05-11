"""Provider registry for reusable LLM providers."""

from __future__ import annotations

from .llm_base import BaseLLMProvider
from .base import ProviderRegistry as SharedProviderRegistry


class LLMProviderRegistry(SharedProviderRegistry):
    """LLM-specific registry preserving consistent provider ergonomics."""

    def __init__(self) -> None:
        super().__init__(provider_base_class=BaseLLMProvider)


default_llm_provider_registry = LLMProviderRegistry()