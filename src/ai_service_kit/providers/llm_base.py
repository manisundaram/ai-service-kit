"""LLM provider base interfaces and shared error types."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .base import (
    BaseProvider,
    ProviderAPIError,
    ProviderConfigError,
    ProviderError,
    ProviderRateLimitError,
    TokenUsage,
)


@dataclass(slots=True, frozen=True)
class LLMUsage(TokenUsage):
    """Usage metadata returned by an LLM provider."""


@dataclass(slots=True, frozen=True)
class LLMMessage:
    """Normalized chat-style message payload."""

    role: str
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, message: Mapping[str, Any]) -> "LLMMessage":
        return cls(
            role=str(message.get("role", "user")),
            content=str(message.get("content", "")),
            name=str(message["name"]) if message.get("name") is not None else None,
            metadata={
                key: value
                for key, value in message.items()
                if key not in {"role", "content", "name"}
            },
        )


@dataclass(slots=True, frozen=True)
class LLMResponse:
    """Normalized LLM response shared across providers."""

    content: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    model: str | None = None
    finish_reason: str | None = None
    provider: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(BaseProvider):
    """Abstract base class for LLM providers."""

    provider_family = "llm"

    @abstractmethod
    async def generate(
        self,
        messages: Sequence[LLMMessage | Mapping[str, Any]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a completion from the provided messages."""

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Return the available LLM model identifiers."""

    async def health_check(self) -> bool:
        """Return True when the provider can service requests."""
        return True

    @staticmethod
    def normalize_messages(
        messages: Sequence[LLMMessage | Mapping[str, Any]],
    ) -> tuple[LLMMessage, ...]:
        normalized: list[LLMMessage] = []
        for message in messages:
            if isinstance(message, LLMMessage):
                normalized.append(message)
            else:
                normalized.append(LLMMessage.from_mapping(message))
        return tuple(normalized)


class LLMError(ProviderError):
    """Base exception for LLM-provider related failures."""

    def __init__(self, message: str, provider: str, error_code: str | None = None):
        super().__init__(message, provider=provider, family="llm", error_code=error_code)


class LLMConfigError(ProviderConfigError):
    """Raised when LLM provider configuration is invalid or incomplete."""

    def __init__(self, message: str, provider: str, error_code: str | None = None):
        super().__init__(message, provider=provider, family="llm", error_code=error_code)


class LLMAPIError(ProviderAPIError):
    """Raised when an LLM provider API request fails."""

    def __init__(self, message: str, provider: str, error_code: str | None = None):
        super().__init__(message, provider=provider, family="llm", error_code=error_code)


class LLMRateLimitError(ProviderRateLimitError):
    """Raised when an LLM provider signals rate limiting."""

    def __init__(self, message: str, provider: str, error_code: str | None = None):
        super().__init__(message, provider=provider, family="llm", error_code=error_code)