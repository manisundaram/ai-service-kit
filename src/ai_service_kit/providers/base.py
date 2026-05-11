"""Canonical provider foundations and embedding base interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..utils import normalize_name


@dataclass(slots=True, frozen=True)
class TokenUsage:
    """Normalized token usage metadata shared across provider families."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ProviderError(Exception):
    """Base exception for provider-related failures."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        family: str | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.family = family
        self.error_code = error_code


class ProviderConfigError(ProviderError):
    """Raised when provider configuration is invalid or incomplete."""


class ProviderAPIError(ProviderError):
    """Raised when a provider API request fails."""


class ProviderRateLimitError(ProviderError):
    """Raised when a provider signals rate limiting."""


class BaseProvider(ABC):
    """Base class for normalized provider implementations."""

    provider_family = "provider"

    def __init__(self, config: Mapping[str, Any] | None = None):
        self.config = dict(config or {})
        self.validate_config()

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration and raise on invalid state."""

    def get_provider_name(self) -> str:
        """Return the normalized provider name."""
        suffix = f"{self.provider_family}provider"
        return self.__class__.__name__.lower().replace(suffix, "")


class ProviderRegistry:
    """Registry of named provider classes with optional family validation."""

    def __init__(self, provider_base_class: type[BaseProvider] | None = None) -> None:
        self._provider_base_class = provider_base_class
        self._providers: dict[str, type[BaseProvider]] = {}

    def register(self, name: str, provider_class: type[BaseProvider]) -> None:
        key = normalize_name(name)
        if self._provider_base_class is not None and not issubclass(provider_class, self._provider_base_class):
            raise TypeError(
                f"Provider class must inherit from {self._provider_base_class.__name__}"
            )
        self._providers[key] = provider_class

    def unregister(self, name: str) -> None:
        self._providers.pop(normalize_name(name), None)

    def get(self, name: str) -> type[BaseProvider]:
        return self._providers[normalize_name(name)]

    def has(self, name: str) -> bool:
        return normalize_name(name) in self._providers

    def list_names(self) -> list[str]:
        return sorted(self._providers)

    def copy(self) -> "ProviderRegistry":
        duplicate = ProviderRegistry(provider_base_class=self._provider_base_class)
        duplicate._providers = dict(self._providers)
        return duplicate


class ProviderFactory:
    """Generic provider factory reused by family-specific wrappers."""

    def __init__(
        self,
        *,
        registry: ProviderRegistry,
        config_error_class: type[ProviderError] = ProviderConfigError,
        family_label: str = "provider",
    ) -> None:
        self.registry = registry
        self.config_error_class = config_error_class
        self.family_label = family_label

    def create_provider(
        self,
        provider_name: str,
        config: Mapping[str, Any] | None = None,
    ) -> BaseProvider:
        normalized_name = normalize_name(provider_name)

        if not self.registry.has(normalized_name):
            available = ", ".join(self.registry.list_names()) or "none"
            raise self.config_error_class(
                f"Unsupported {self.family_label}: '{normalized_name}'. Available providers: {available}",
                provider=normalized_name,
            )

        provider_class = self.registry.get(normalized_name)
        try:
            return provider_class(config)
        except self.config_error_class:
            raise
        except Exception as exc:
            raise self.config_error_class(
                f"Failed to initialize {normalized_name} provider: {exc}",
                provider=normalized_name,
            ) from exc

    def get_available_providers(self) -> list[str]:
        return self.registry.list_names()

    def register_provider(self, name: str, provider_class: type[BaseProvider]) -> None:
        self.registry.register(name, provider_class)


@dataclass(slots=True, frozen=True)
class EmbeddingUsage(TokenUsage):
    """Usage metadata returned by an embedding provider."""


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


class BaseEmbeddingProvider(BaseProvider):
    """Abstract base class for embedding providers."""

    provider_family = "embedding"

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

    async def health_check(self) -> bool:
        """Return True when the provider can service requests."""
        return True

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


class EmbeddingConfigError(ProviderConfigError):
    """Raised when provider configuration is invalid or incomplete."""

    def __init__(self, message: str, provider: str, error_code: str | None = None):
        super().__init__(message, provider=provider, family="embedding", error_code=error_code)


class EmbeddingAPIError(ProviderAPIError):
    """Raised when a provider API request fails."""

    def __init__(self, message: str, provider: str, error_code: str | None = None):
        super().__init__(message, provider=provider, family="embedding", error_code=error_code)


class EmbeddingRateLimitError(ProviderRateLimitError):
    """Raised when a provider signals rate limiting."""

    def __init__(self, message: str, provider: str, error_code: str | None = None):
        super().__init__(message, provider=provider, family="embedding", error_code=error_code)
