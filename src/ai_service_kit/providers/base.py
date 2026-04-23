"""Embedding provider base interfaces and shared error types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(slots=True, frozen=True)
class EmbeddingUsage:
    """Usage metadata returned by an embedding provider."""

    prompt_tokens: int = 0
    total_tokens: int = 0


@dataclass(slots=True, frozen=True)
class EmbeddingResult:
    """Normalized embedding response shared across providers."""

    embeddings: tuple[tuple[float, ...], ...]
    model: str
    usage: EmbeddingUsage
    provider: str
    dimension: int

    @classmethod
    def from_vectors(
        cls,
        *,
        embeddings: Sequence[Sequence[float]],
        model: str,
        usage: EmbeddingUsage | None = None,
        provider: str,
        dimension: int | None = None,
    ) -> "EmbeddingResult":
        normalized_embeddings = tuple(tuple(vector) for vector in embeddings)
        resolved_dimension = dimension
        if resolved_dimension is None:
            resolved_dimension = len(normalized_embeddings[0]) if normalized_embeddings else 0
        return cls(
            embeddings=normalized_embeddings,
            model=model,
            usage=usage or EmbeddingUsage(),
            provider=provider,
            dimension=resolved_dimension,
        )


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: Mapping[str, Any] | None = None):
        self.config = dict(config or {})
        self.validate_config()

    @abstractmethod
    async def embed(
        self,
        texts: Sequence[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        """Generate embeddings for the provided texts."""

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Return the available embedding model identifiers."""

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration and raise on invalid state."""

    def get_provider_name(self) -> str:
        """Return the normalized provider name."""
        return self.__class__.__name__.lower().replace("embeddingprovider", "")

    def get_max_input_tokens(self) -> int:
        """Return the maximum supported input token count."""
        return 8192

    def get_embedding_dimension(self, model: str | None = None) -> int:
        """Return the embedding vector dimension for the given model."""
        del model
        return 1536


class EmbeddingError(Exception):
    """Base exception for embedding-provider related failures."""

    def __init__(self, message: str, provider: str, error_code: str | None = None):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code


class EmbeddingConfigError(EmbeddingError):
    """Raised when provider configuration is invalid or incomplete."""


class EmbeddingAPIError(EmbeddingError):
    """Raised when a provider API request fails."""


class EmbeddingRateLimitError(EmbeddingError):
    """Raised when a provider signals rate limiting."""
