"""Reusable deterministic mock providers for testing and development.

Both providers require no API credentials and return stable outputs derived
from a SHA-256 hash of the input plus an optional integer seed.  They are
generic enough to be used by any sibling service that wants to activate mock
mode without carrying service-specific mock logic.

Supported config keys (all optional):
    MockLLMProvider
        model       - model name reported in responses (default: "mock-llm")
        seed        - integer seed for deterministic output (default: 0)
        latency_ms  - artificial latency in milliseconds (default: 0)
        prefix      - fixed text prepended to every response (default: "")
        suffix      - fixed text appended to every response (default: "")

    MockEmbeddingProvider
        model       - model name reported in results (default: "mock-embed")
        dimension   - output vector dimension (default: 1536)
        seed        - integer seed for deterministic output (default: 0)
        latency_ms  - artificial latency in milliseconds (default: 0)
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import struct
from typing import Any, Mapping, Sequence

from .base import (
    BaseEmbeddingProvider,
    EmbeddingResult,
    EmbeddingUsage,
    ProviderRegistry,
)
from .llm_base import BaseLLMProvider, LLMMessage, LLMResponse, LLMUsage
from .llm_registry import LLMProviderRegistry, default_llm_provider_registry
from .registry import default_provider_registry


# ---------------------------------------------------------------------------
# MockLLMProvider
# ---------------------------------------------------------------------------


class MockLLMProvider(BaseLLMProvider):
    """Deterministic LLM provider for testing and mock mode.

    No network calls are made and no credentials are required.
    The response content is a short hex digest derived from the input messages
    so that identical inputs always produce identical outputs.
    """

    provider_family = "llm"

    _DEFAULT_MODEL = "mock-llm"
    _AVAILABLE_MODELS = ["mock-llm"]

    def validate_config(self) -> bool:  # type: ignore[override]
        return True

    def get_available_models(self) -> list[str]:
        return list(self._AVAILABLE_MODELS)

    def get_provider_name(self) -> str:
        return "mock"

    async def health_check(self) -> bool:
        return True

    async def generate(
        self,
        messages: Sequence[LLMMessage | Mapping[str, Any]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        latency_ms = int(self.config.get("latency_ms", 0))
        if latency_ms > 0:
            await asyncio.sleep(latency_ms / 1000.0)

        normalized = self.normalize_messages(messages)
        resolved_model = model or str(self.config.get("model", self._DEFAULT_MODEL))
        seed = int(self.config.get("seed", 0))
        prefix = str(self.config.get("prefix", ""))
        suffix = str(self.config.get("suffix", ""))

        digest = self._hash_messages(normalized, seed)
        content = f"{prefix}mock:{digest[:16]}{suffix}"

        prompt_tokens = sum(len(m.content.split()) for m in normalized)
        completion_tokens = len(content.split())
        return LLMResponse(
            content=content,
            model=resolved_model,
            finish_reason="stop",
            provider="mock",
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

    @staticmethod
    def _hash_messages(messages: Sequence[LLMMessage], seed: int) -> str:
        hasher = hashlib.sha256()
        hasher.update(seed.to_bytes(8, "little", signed=True))
        for m in messages:
            hasher.update(m.role.encode())
            hasher.update(m.content.encode())
        return hasher.hexdigest()


# ---------------------------------------------------------------------------
# MockEmbeddingProvider
# ---------------------------------------------------------------------------


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic embedding provider for testing and mock mode.

    No network calls are made and no credentials are required.
    Each text is hashed to produce a stable, L2-normalized float vector of the
    requested dimension.
    """

    provider_family = "embedding"

    _DEFAULT_MODEL = "mock-embed"
    _AVAILABLE_MODELS = ["mock-embed"]

    def validate_config(self) -> bool:  # type: ignore[override]
        dimension = int(self.config.get("dimension", 1536))
        if dimension < 1:
            raise ValueError("MockEmbeddingProvider: dimension must be >= 1")
        return True

    def get_available_models(self) -> list[str]:
        return list(self._AVAILABLE_MODELS)

    def get_provider_name(self) -> str:
        return "mock"

    def get_embedding_dimension(self, model: str | None = None) -> int:
        return int(self.config.get("dimension", 1536))

    async def embed(
        self,
        texts: Sequence[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        latency_ms = int(self.config.get("latency_ms", 0))
        if latency_ms > 0:
            await asyncio.sleep(latency_ms / 1000.0)

        resolved_model = model or str(self.config.get("model", self._DEFAULT_MODEL))
        dimension = int(self.config.get("dimension", 1536))
        seed = int(self.config.get("seed", 0))

        embeddings = [self._embed_text(text, dimension, seed) for text in texts]
        total_tokens = sum(len(t.split()) for t in texts)

        return EmbeddingResult.from_vectors(
            embeddings=embeddings,
            model=resolved_model,
            usage=EmbeddingUsage(
                prompt_tokens=total_tokens,
                completion_tokens=0,
                total_tokens=total_tokens,
            ),
            provider="mock",
            dimension=dimension,
        )

    @staticmethod
    def _embed_text(text: str, dimension: int, seed: int) -> tuple[float, ...]:
        """Return a stable L2-normalized float vector for *text*."""
        hasher = hashlib.sha256()
        hasher.update(seed.to_bytes(8, "little", signed=True))
        hasher.update(text.encode())
        digest = hasher.digest()

        # Stretch the 32-byte digest into `dimension` floats using sequential
        # SHA-256 rounds so the result is both deterministic and well-distributed.
        floats: list[float] = []
        counter = 0
        while len(floats) < dimension:
            block_hasher = hashlib.sha256()
            block_hasher.update(digest)
            block_hasher.update(counter.to_bytes(4, "little"))
            block = block_hasher.digest()
            for i in range(0, len(block) - 3, 4):
                raw = struct.unpack_from("<I", block, i)[0]
                floats.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
                if len(floats) == dimension:
                    break
            counter += 1

        # L2-normalize so the vector lives on the unit sphere.
        magnitude = math.sqrt(sum(f * f for f in floats)) or 1.0
        return tuple(f / magnitude for f in floats)


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def register_mock_providers(
    *,
    embedding_registry: ProviderRegistry | None = None,
    llm_registry: LLMProviderRegistry | None = None,
) -> None:
    """Register ``"mock"`` into provider registries.

    ``"mock"`` is already registered in both default registries at import
    time, so services that use the default registries do not need to call
    this function.  Use it only when you have constructed a custom registry
    instance and want ``"mock"`` available there too.

    Args:
        embedding_registry: Custom embedding registry to register into.
            Pass ``None`` (the default) to target the package-level
            :data:`~ai_service_kit.providers.registry.default_provider_registry`.
        llm_registry: Custom LLM registry to register into.
            Pass ``None`` (the default) to target the package-level
            :data:`~ai_service_kit.providers.llm_registry.default_llm_provider_registry`.

    Example — custom registry::

        from ai_service_kit.providers import register_mock_providers, ProviderRegistry

        my_registry = ProviderRegistry()
        register_mock_providers(embedding_registry=my_registry)
    """
    embedding_target = (
        embedding_registry
        if embedding_registry is not None
        else default_provider_registry
    )
    llm_target = (
        llm_registry if llm_registry is not None else default_llm_provider_registry
    )
    embedding_target.register("mock", MockEmbeddingProvider)
    llm_target.register("mock", MockLLMProvider)


# Auto-register "mock" into the package-level default registries so services
# can use  LLM_PROVIDER=mock / EMBEDDING_PROVIDER=mock in their env without
# any additional registration call, exactly like "openai" or "gemini".
register_mock_providers()
