"""Tests for MockLLMProvider, MockEmbeddingProvider, and register_mock_providers."""

from __future__ import annotations

import math
import pytest

from ai_service_kit.providers import (
    LLMMessage,
    LLMProviderFactory,
    LLMProviderRegistry,
    MockEmbeddingProvider,
    MockLLMProvider,
    ProviderFactory,
    ProviderRegistry,
    register_mock_providers,
)


# ---------------------------------------------------------------------------
# MockLLMProvider
# ---------------------------------------------------------------------------


class TestMockLLMProvider:
    def _make(self, **config) -> MockLLMProvider:
        return MockLLMProvider(config or None)

    def test_validate_config_always_passes(self):
        provider = self._make()
        assert provider.validate_config() is True

    def test_get_available_models(self):
        provider = self._make()
        models = provider.get_available_models()
        assert isinstance(models, list)
        assert len(models) >= 1

    def test_get_provider_name(self):
        provider = self._make()
        assert provider.get_provider_name() == "mock"

    @pytest.mark.asyncio
    async def test_health_check(self):
        provider = self._make()
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_generate_returns_response(self):
        provider = self._make()
        messages = [LLMMessage(role="user", content="hello")]
        response = await provider.generate(messages)
        assert isinstance(response.content, str)
        assert len(response.content) > 0
        assert response.provider == "mock"
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_deterministic(self):
        provider = self._make(seed=42)
        messages = [LLMMessage(role="user", content="hello world")]
        r1 = await provider.generate(messages)
        r2 = await provider.generate(messages)
        assert r1.content == r2.content

    @pytest.mark.asyncio
    async def test_generate_different_seeds_differ(self):
        messages = [LLMMessage(role="user", content="hello")]
        p1 = self._make(seed=0)
        p2 = self._make(seed=1)
        r1 = await p1.generate(messages)
        r2 = await p2.generate(messages)
        assert r1.content != r2.content

    @pytest.mark.asyncio
    async def test_generate_different_input_differs(self):
        provider = self._make()
        r1 = await provider.generate([LLMMessage(role="user", content="alpha")])
        r2 = await provider.generate([LLMMessage(role="user", content="beta")])
        assert r1.content != r2.content

    @pytest.mark.asyncio
    async def test_generate_uses_model_config(self):
        provider = self._make(model="custom-model")
        messages = [LLMMessage(role="user", content="test")]
        response = await provider.generate(messages)
        assert response.model == "custom-model"

    @pytest.mark.asyncio
    async def test_generate_model_override(self):
        provider = self._make()
        messages = [LLMMessage(role="user", content="test")]
        response = await provider.generate(messages, model="override-model")
        assert response.model == "override-model"

    @pytest.mark.asyncio
    async def test_generate_prefix_suffix(self):
        provider = self._make(prefix="START:", suffix=":END")
        messages = [LLMMessage(role="user", content="hi")]
        response = await provider.generate(messages)
        assert response.content.startswith("START:")
        assert response.content.endswith(":END")

    @pytest.mark.asyncio
    async def test_generate_usage_populated(self):
        provider = self._make()
        messages = [LLMMessage(role="user", content="one two three")]
        response = await provider.generate(messages)
        assert response.usage.prompt_tokens > 0
        assert response.usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_generate_accepts_dict_messages(self):
        provider = self._make()
        response = await provider.generate([{"role": "user", "content": "hi"}])
        assert isinstance(response.content, str)

    @pytest.mark.asyncio
    async def test_generate_no_latency_by_default(self):
        import time
        provider = self._make()
        messages = [LLMMessage(role="user", content="fast")]
        start = time.monotonic()
        await provider.generate(messages)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100


# ---------------------------------------------------------------------------
# MockEmbeddingProvider
# ---------------------------------------------------------------------------


class TestMockEmbeddingProvider:
    def _make(self, **config) -> MockEmbeddingProvider:
        return MockEmbeddingProvider(config or None)

    def test_validate_config_passes(self):
        provider = self._make()
        assert provider.validate_config() is True

    def test_validate_config_rejects_zero_dimension(self):
        with pytest.raises(ValueError, match="dimension"):
            MockEmbeddingProvider({"dimension": 0})

    def test_get_available_models(self):
        provider = self._make()
        assert isinstance(provider.get_available_models(), list)

    def test_get_provider_name(self):
        provider = self._make()
        assert provider.get_provider_name() == "mock"

    def test_get_embedding_dimension_default(self):
        provider = self._make()
        assert provider.get_embedding_dimension() == 1536

    def test_get_embedding_dimension_custom(self):
        provider = self._make(dimension=256)
        assert provider.get_embedding_dimension() == 256

    @pytest.mark.asyncio
    async def test_embed_returns_result(self):
        provider = self._make()
        result = await provider.embed(["hello world"])
        assert len(result.embeddings) == 1
        assert len(result.embeddings[0]) == 1536

    @pytest.mark.asyncio
    async def test_embed_correct_dimension(self):
        provider = self._make(dimension=128)
        result = await provider.embed(["test"])
        assert result.dimension == 128
        assert len(result.embeddings[0]) == 128

    @pytest.mark.asyncio
    async def test_embed_deterministic(self):
        provider = self._make(seed=7)
        r1 = await provider.embed(["deterministic text"])
        r2 = await provider.embed(["deterministic text"])
        assert r1.embeddings == r2.embeddings

    @pytest.mark.asyncio
    async def test_embed_different_seeds_differ(self):
        p1 = self._make(seed=0)
        p2 = self._make(seed=1)
        r1 = await p1.embed(["hello"])
        r2 = await p2.embed(["hello"])
        assert r1.embeddings != r2.embeddings

    @pytest.mark.asyncio
    async def test_embed_different_text_differs(self):
        provider = self._make()
        r1 = await provider.embed(["alpha"])
        r2 = await provider.embed(["beta"])
        assert r1.embeddings != r2.embeddings

    @pytest.mark.asyncio
    async def test_embed_multiple_texts(self):
        provider = self._make(dimension=64)
        result = await provider.embed(["foo", "bar", "baz"])
        assert len(result.embeddings) == 3
        for vec in result.embeddings:
            assert len(vec) == 64

    @pytest.mark.asyncio
    async def test_embed_vectors_are_unit_normalized(self):
        provider = self._make(dimension=64)
        result = await provider.embed(["normalize me"])
        vec = result.embeddings[0]
        magnitude = math.sqrt(sum(f * f for f in vec))
        assert abs(magnitude - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_embed_usage_populated(self):
        provider = self._make()
        result = await provider.embed(["one two", "three"])
        assert result.usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_embed_provider_field(self):
        provider = self._make()
        result = await provider.embed(["x"])
        assert result.provider == "mock"

    @pytest.mark.asyncio
    async def test_embed_model_override(self):
        provider = self._make()
        result = await provider.embed(["x"], model="alt-model")
        assert result.model == "alt-model"


# ---------------------------------------------------------------------------
# register_mock_providers helper
# ---------------------------------------------------------------------------


class TestRegisterMockProviders:
    def _fresh_registries(self):
        embedding_reg = ProviderRegistry()
        llm_reg = LLMProviderRegistry()
        return embedding_reg, llm_reg

    def test_registers_mock_into_both_registries(self):
        emb_reg, llm_reg = self._fresh_registries()
        register_mock_providers(embedding_registry=emb_reg, llm_registry=llm_reg)
        assert emb_reg.has("mock")
        assert llm_reg.has("mock")

    def test_embedding_registry_creates_correct_class(self):
        emb_reg, llm_reg = self._fresh_registries()
        register_mock_providers(embedding_registry=emb_reg, llm_registry=llm_reg)
        provider_class = emb_reg.get("mock")
        assert provider_class is MockEmbeddingProvider

    def test_llm_registry_creates_correct_class(self):
        emb_reg, llm_reg = self._fresh_registries()
        register_mock_providers(embedding_registry=emb_reg, llm_registry=llm_reg)
        provider_class = llm_reg.get("mock")
        assert provider_class is MockLLMProvider

    def test_factory_creates_embedding_provider(self):
        from ai_service_kit.providers.factory import ProviderFactory as EmbFactory
        emb_reg, llm_reg = self._fresh_registries()
        register_mock_providers(embedding_registry=emb_reg, llm_registry=llm_reg)
        factory = EmbFactory()
        factory.registry = emb_reg
        provider = factory.create_provider("mock")
        assert isinstance(provider, MockEmbeddingProvider)

    def test_factory_creates_llm_provider(self):
        emb_reg, llm_reg = self._fresh_registries()
        register_mock_providers(embedding_registry=emb_reg, llm_registry=llm_reg)
        factory = LLMProviderFactory()
        factory.registry = llm_reg
        provider = factory.create_provider("mock")
        assert isinstance(provider, MockLLMProvider)

    def test_uses_default_registries_when_none_supplied(self):
        from ai_service_kit.providers.registry import default_provider_registry
        from ai_service_kit.providers.llm_registry import default_llm_provider_registry
        register_mock_providers()
        assert default_provider_registry.has("mock")
        assert default_llm_provider_registry.has("mock")
