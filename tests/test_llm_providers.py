import asyncio

from ai_service_kit.providers import (
    BaseLLMProvider,
    LLMConfigError,
    LLMMessage,
    LLMProviderFactory,
    LLMProviderRegistry,
    LLMResponse,
    LLMUsage,
)


class DummyLLMProvider(BaseLLMProvider):
    def validate_config(self) -> bool:
        if "api_key" not in self.config:
            raise LLMConfigError("missing api key", provider="dummy")
        return True

    async def generate(self, messages, model=None, temperature=0.1, max_tokens=None, **kwargs):
        del temperature, max_tokens, kwargs
        normalized = self.normalize_messages(messages)
        resolved_model = model or "dummy-llm-model"
        combined = " | ".join(message.content for message in normalized)
        return LLMResponse(
            content=combined,
            usage=LLMUsage(prompt_tokens=len(normalized), completion_tokens=1, total_tokens=len(normalized) + 1),
            model=resolved_model,
            provider=self.get_provider_name(),
        )

    def get_available_models(self) -> list[str]:
        return ["dummy-llm-model"]


def test_llm_registry_registers_and_lists_names() -> None:
    registry = LLMProviderRegistry()
    registry.register(" Dummy ", DummyLLMProvider)

    assert registry.has("dummy") is True
    assert registry.list_names() == ["dummy"]


def test_llm_factory_creates_registered_provider() -> None:
    registry = LLMProviderRegistry()
    registry.register("dummy", DummyLLMProvider)
    factory = LLMProviderFactory(registry)

    provider = factory.create_provider("DuMmY", {"api_key": "secret"})

    assert isinstance(provider, DummyLLMProvider)
    assert factory.get_available_providers() == ["dummy"]


def test_llm_factory_raises_for_unknown_provider() -> None:
    factory = LLMProviderFactory(LLMProviderRegistry())

    try:
        factory.create_provider("missing", {})
    except LLMConfigError as exc:
        assert "Unsupported llm provider" in str(exc)
    else:
        raise AssertionError("expected LLMConfigError for unknown provider")


def test_llm_message_normalization_supports_dict_and_dataclass() -> None:
    provider = DummyLLMProvider({"api_key": "secret"})
    normalized = provider.normalize_messages(
        [
            {"role": "system", "content": "be concise"},
            LLMMessage(role="user", content="hello"),
        ]
    )

    assert len(normalized) == 2
    assert normalized[0].role == "system"
    assert normalized[1].content == "hello"


def test_llm_response_normalizes_usage_shape() -> None:
    response = asyncio.run(
        DummyLLMProvider({"api_key": "secret"}).generate([
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ])
    )

    assert response.provider == "dummy"
    assert response.model == "dummy-llm-model"
    assert response.usage.total_tokens == 3