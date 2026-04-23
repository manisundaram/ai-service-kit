import asyncio

from ai_service_kit.providers import (
    BaseEmbeddingProvider,
    EmbeddingConfigError,
    EmbeddingResult,
    EmbeddingUsage,
    ProviderFactory,
    ProviderRegistry,
)


class DummyEmbeddingProvider(BaseEmbeddingProvider):
    def validate_config(self) -> bool:
        if "api_key" not in self.config:
            raise EmbeddingConfigError("missing api key", provider="dummy")
        return True

    async def embed(self, texts, model=None, **kwargs):
        del kwargs
        resolved_model = model or "dummy-model"
        return EmbeddingResult.from_vectors(
            embeddings=[[float(len(text))] for text in texts],
            model=resolved_model,
            usage=EmbeddingUsage(prompt_tokens=len(texts), total_tokens=len(texts)),
            provider=self.get_provider_name(),
            dimension=1,
        )

    def get_available_models(self) -> list[str]:
        return ["dummy-model"]


def test_registry_registers_and_lists_names() -> None:
    registry = ProviderRegistry()
    registry.register(" Dummy ", DummyEmbeddingProvider)

    assert registry.has("dummy") is True
    assert registry.list_names() == ["dummy"]


def test_registry_rejects_invalid_provider_class() -> None:
    registry = ProviderRegistry()

    try:
        registry.register("invalid", object)
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for non-provider class")


def test_factory_creates_registered_provider() -> None:
    registry = ProviderRegistry()
    registry.register("dummy", DummyEmbeddingProvider)
    factory = ProviderFactory(registry)

    provider = factory.create_provider("DuMmY", {"api_key": "secret"})

    assert isinstance(provider, DummyEmbeddingProvider)
    assert factory.get_available_providers() == ["dummy"]


def test_factory_raises_for_unknown_provider() -> None:
    factory = ProviderFactory(ProviderRegistry())

    try:
        factory.create_provider("missing", {})
    except EmbeddingConfigError as exc:
        assert "Unsupported embedding provider" in str(exc)
    else:
        raise AssertionError("expected EmbeddingConfigError for unknown provider")


def test_embedding_result_normalizes_vectors() -> None:
    result = asyncio.run(
        DummyEmbeddingProvider({"api_key": "secret"}).embed(["a", "bb"])
    )

    assert result.provider == "dummy"
    assert result.dimension == 1
    assert result.embeddings == ((1.0,), (2.0,))
