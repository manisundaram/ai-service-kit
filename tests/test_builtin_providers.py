import pytest

from ai_service_kit.providers import (
    AnthropicEmbeddingProvider,
    AnthropicLLMProvider,
    EmbeddingConfigError,
    GeminiEmbeddingProvider,
    GeminiLLMProvider,
    LLMConfigError,
    LLMMessage,
    LLMProviderFactory,
    OllamaEmbeddingProvider,
    OllamaLLMProvider,
    OpenAIEmbeddingProvider,
    OpenAILLMProvider,
    ProviderFactory,
    register_builtin_providers,
)


@pytest.mark.parametrize("provider_name", ["openai", "gemini", "anthropic", "ollama", "mock"])
def test_default_llm_factory_lists_builtin_and_mock(provider_name: str) -> None:
    available = LLMProviderFactory().get_available_providers()
    assert provider_name in available


@pytest.mark.parametrize("provider_name", ["openai", "gemini", "anthropic", "ollama", "mock"])
def test_default_embedding_factory_lists_builtin_and_mock(provider_name: str) -> None:
    available = ProviderFactory().get_available_providers()
    assert provider_name in available


@pytest.mark.parametrize(
    ("provider_name", "provider_type"),
    [
        ("openai", OpenAILLMProvider),
        ("gemini", GeminiLLMProvider),
        ("anthropic", AnthropicLLMProvider),
        ("ollama", OllamaLLMProvider),
    ],
)
def test_llm_factory_creates_builtin_providers(
    provider_name: str,
    provider_type: type,
) -> None:
    provider = LLMProviderFactory().create_provider(provider_name, {"api_key": "k"})
    assert isinstance(provider, provider_type)


@pytest.mark.parametrize(
    ("provider_name", "provider_type"),
    [
        ("openai", OpenAIEmbeddingProvider),
        ("gemini", GeminiEmbeddingProvider),
        ("anthropic", AnthropicEmbeddingProvider),
        ("ollama", OllamaEmbeddingProvider),
    ],
)
def test_embedding_factory_creates_builtin_providers(
    provider_name: str,
    provider_type: type,
) -> None:
    provider = ProviderFactory().create_provider(provider_name, {"api_key": "k"})
    assert isinstance(provider, provider_type)


@pytest.mark.parametrize(
    "provider_class",
    [OpenAILLMProvider, GeminiLLMProvider, AnthropicLLMProvider],
)
def test_llm_builtin_provider_requires_api_key(provider_class: type) -> None:
    with pytest.raises(LLMConfigError):
        provider_class({})


@pytest.mark.parametrize(
    "provider_class",
    [OpenAIEmbeddingProvider, GeminiEmbeddingProvider, AnthropicEmbeddingProvider],
)
def test_embedding_builtin_provider_requires_api_key(provider_class: type) -> None:
    with pytest.raises(EmbeddingConfigError):
        provider_class({})


@pytest.mark.asyncio
async def test_openai_llm_response_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAILLMProvider({"api_key": "k"})

    async def fake_post_json(**kwargs):
        del kwargs
        return 200, {
            "model": "gpt-4o-mini",
            "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
        }

    monkeypatch.setattr(provider, "_post_json", fake_post_json)
    response = await provider.generate([LLMMessage(role="user", content="hi")])

    assert response.provider == "openai"
    assert response.content == "hello"
    assert response.usage.total_tokens == 3


@pytest.mark.asyncio
async def test_openai_embedding_response_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAIEmbeddingProvider({"api_key": "k"})

    async def fake_post_json(**kwargs):
        del kwargs
        return 200, {
            "model": "text-embedding-3-small",
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ],
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }

    monkeypatch.setattr(provider, "_post_json", fake_post_json)
    result = await provider.embed(["a", "b"])

    assert result.provider == "openai"
    assert result.dimension == 1536
    assert len(result.embeddings) == 2


@pytest.mark.asyncio
async def test_gemini_llm_response_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiLLMProvider({"api_key": "k"})

    async def fake_post_json(**kwargs):
        del kwargs
        return 200, {
            "candidates": [
                {
                    "content": {"parts": [{"text": "world"}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 4,
                "candidatesTokenCount": 2,
                "totalTokenCount": 6,
            },
        }

    monkeypatch.setattr(provider, "_post_json", fake_post_json)
    response = await provider.generate([{"role": "user", "content": "hi"}])

    assert response.provider == "gemini"
    assert response.content == "world"
    assert response.usage.total_tokens == 6


@pytest.mark.asyncio
async def test_anthropic_llm_response_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = AnthropicLLMProvider({"api_key": "k"})

    async def fake_post_json(**kwargs):
        del kwargs
        return 200, {
            "model": "claude-3-5-haiku-latest",
            "content": [{"type": "text", "text": "anthropic-ok"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 3, "output_tokens": 2},
        }

    monkeypatch.setattr(provider, "_post_json", fake_post_json)
    response = await provider.generate([{"role": "user", "content": "hi"}])

    assert response.provider == "anthropic"
    assert response.content == "anthropic-ok"
    assert response.usage.total_tokens == 5


# ---------------------------------------------------------------------------
# Ollama (local) providers
# ---------------------------------------------------------------------------


def test_ollama_llm_provider_requires_no_api_key() -> None:
    provider = OllamaLLMProvider({})
    assert provider.validate_config() is True


def test_ollama_embedding_provider_requires_no_api_key() -> None:
    provider = OllamaEmbeddingProvider({})
    assert provider.validate_config() is True


def test_ollama_llm_defaults() -> None:
    provider = OllamaLLMProvider({})
    assert provider.get_provider_name() == "ollama"
    assert "llama3.2" in provider.get_available_models()


def test_ollama_embedding_defaults() -> None:
    provider = OllamaEmbeddingProvider({})
    assert provider.get_provider_name() == "ollama"
    assert "nomic-embed-text" in provider.get_available_models()


def test_ollama_embedding_known_dimensions() -> None:
    assert OllamaEmbeddingProvider({}).get_embedding_dimension("nomic-embed-text") == 768
    assert OllamaEmbeddingProvider({}).get_embedding_dimension("mxbai-embed-large") == 1024
    assert OllamaEmbeddingProvider({"dimension": 512}).get_embedding_dimension() == 512


@pytest.mark.asyncio
async def test_ollama_llm_response_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLLMProvider({})

    async def fake_post_json(**kwargs):
        del kwargs
        return 200, {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "local response"},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 5,
            "eval_count": 3,
        }

    monkeypatch.setattr(provider, "_post_json", fake_post_json)
    response = await provider.generate([LLMMessage(role="user", content="hi")])

    assert response.provider == "ollama"
    assert response.content == "local response"
    assert response.model == "llama3.2"
    assert response.finish_reason == "stop"
    assert response.usage.prompt_tokens == 5
    assert response.usage.completion_tokens == 3
    assert response.usage.total_tokens == 8


@pytest.mark.asyncio
async def test_ollama_llm_uses_model_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLLMProvider({"model": "mistral"})

    async def fake_post_json(*, url, payload, **kwargs):
        del kwargs
        assert payload["model"] == "mistral"
        return 200, {
            "model": "mistral",
            "message": {"role": "assistant", "content": "ok"},
            "done": True,
        }

    monkeypatch.setattr(provider, "_post_json", fake_post_json)
    response = await provider.generate([LLMMessage(role="user", content="hi")])
    assert response.model == "mistral"


@pytest.mark.asyncio
async def test_ollama_llm_custom_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLLMProvider({"base_url": "http://remote-host:11434"})
    captured = {}

    async def fake_post_json(*, url, **kwargs):
        captured["url"] = url
        return 200, {"model": "llama3.2", "message": {"role": "assistant", "content": "hi"}, "done": True}

    monkeypatch.setattr(provider, "_post_json", fake_post_json)
    await provider.generate([LLMMessage(role="user", content="hi")])
    assert captured["url"] == "http://remote-host:11434/api/chat"


@pytest.mark.asyncio
async def test_ollama_embedding_response_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaEmbeddingProvider({})

    async def fake_post_json(**kwargs):
        del kwargs
        return 200, {
            "model": "nomic-embed-text",
            "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            "prompt_eval_count": 4,
        }

    monkeypatch.setattr(provider, "_post_json", fake_post_json)
    result = await provider.embed(["hello", "world"])

    assert result.provider == "ollama"
    assert len(result.embeddings) == 2
    assert result.embeddings[0] == (0.1, 0.2, 0.3)
    assert result.usage.prompt_tokens == 4


@pytest.mark.asyncio
async def test_ollama_health_check_passes_on_200(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLLMProvider({})

    async def fake_get_json(*, url, **kwargs):
        del kwargs
        return 200, {"version": "0.6.0"}

    monkeypatch.setattr(provider, "_get_json", fake_get_json)
    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_ollama_health_check_fails_on_503(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLLMProvider({})

    async def fake_get_json(*, url, **kwargs):
        del kwargs
        return 503, {"error": {"message": "connection refused"}}

    monkeypatch.setattr(provider, "_get_json", fake_get_json)
    assert await provider.health_check() is False


def test_register_builtin_providers_is_idempotent() -> None:
    # register() overwrites existing keys, so this should not fail on repeated calls.
    register_builtin_providers()
    register_builtin_providers()

    llm_available = LLMProviderFactory().get_available_providers()
    embedding_available = ProviderFactory().get_available_providers()

    assert "openai" in llm_available
    assert "gemini" in llm_available
    assert "anthropic" in llm_available
    assert "ollama" in llm_available
    assert "openai" in embedding_available
    assert "gemini" in embedding_available
    assert "anthropic" in embedding_available
    assert "ollama" in embedding_available
