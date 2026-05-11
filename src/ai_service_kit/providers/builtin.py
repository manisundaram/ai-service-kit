"""Built-in OpenAI, Gemini, Anthropic, and Ollama provider implementations.

These providers are reusable, service-agnostic adapters built on top of the
shared ai-service-kit provider abstractions.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Mapping, Sequence
from urllib import error as url_error
from urllib import request as url_request

from .base import (
    BaseEmbeddingProvider,
    EmbeddingAPIError,
    EmbeddingConfigError,
    EmbeddingResult,
    EmbeddingUsage,
    ProviderRegistry,
)
from .llm_base import (
    BaseLLMProvider,
    LLMAPIError,
    LLMConfigError,
    LLMMessage,
    LLMResponse,
    LLMUsage,
)
from .llm_registry import LLMProviderRegistry, default_llm_provider_registry
from .registry import default_provider_registry


class _HttpJsonClientMixin:
    """Small stdlib HTTP JSON client reused across providers."""

    @staticmethod
    async def _post_json(
        *,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> tuple[int, Mapping[str, Any]]:
        return await asyncio.to_thread(
            _HttpJsonClientMixin._post_json_sync,
            url,
            payload,
            headers,
            timeout,
        )

    @staticmethod
    def _post_json_sync(
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> tuple[int, Mapping[str, Any]]:
        merged_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **dict(headers),
        }
        body = json.dumps(payload).encode("utf-8")
        request = url_request.Request(
            url,
            data=body,
            headers=merged_headers,
            method="POST",
        )
        try:
            with url_request.urlopen(request, timeout=timeout) as response:
                status = int(response.getcode() or 0)
                content = response.read().decode("utf-8")
        except url_error.HTTPError as exc:
            status = int(exc.code or 500)
            content = exc.read().decode("utf-8") if exc.fp is not None else ""
        except url_error.URLError as exc:
            return 503, {"error": {"message": str(exc.reason)}}

        try:
            parsed = json.loads(content) if content else {}
        except json.JSONDecodeError:
            parsed = {"error": {"message": content}}
        if not isinstance(parsed, Mapping):
            parsed = {"data": parsed}
        return status, parsed

    @staticmethod
    async def _get_json(
        *,
        url: str,
        headers: Mapping[str, str] | None = None,
        timeout: float,
    ) -> tuple[int, Mapping[str, Any]]:
        return await asyncio.to_thread(
            _HttpJsonClientMixin._get_json_sync,
            url,
            headers or {},
            timeout,
        )

    @staticmethod
    def _get_json_sync(
        url: str,
        headers: Mapping[str, str],
        timeout: float,
    ) -> tuple[int, Mapping[str, Any]]:
        merged_headers = {"Accept": "application/json", **dict(headers)}
        request = url_request.Request(url, headers=merged_headers, method="GET")
        try:
            with url_request.urlopen(request, timeout=timeout) as response:
                status = int(response.getcode() or 0)
                content = response.read().decode("utf-8")
        except url_error.HTTPError as exc:
            status = int(exc.code or 500)
            content = exc.read().decode("utf-8") if exc.fp is not None else ""
        except url_error.URLError as exc:
            return 503, {"error": {"message": str(exc.reason)}}

        try:
            parsed = json.loads(content) if content else {}
        except json.JSONDecodeError:
            parsed = {"error": {"message": content}}
        if not isinstance(parsed, Mapping):
            parsed = {"data": parsed}
        return status, parsed


class OpenAILLMProvider(_HttpJsonClientMixin, BaseLLMProvider):
    provider_family = "llm"

    def validate_config(self) -> bool:
        if not str(self.config.get("api_key", "")).strip():
            raise LLMConfigError("OPENAI API key is required", provider="openai")
        return True

    def get_provider_name(self) -> str:
        return "openai"

    def get_available_models(self) -> list[str]:
        return ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1", "o4-mini"]

    async def generate(
        self,
        messages: Sequence[LLMMessage | Mapping[str, Any]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        normalized = self.normalize_messages(messages)
        resolved_model = model or str(self.config.get("model", "gpt-4o-mini"))
        base_url = str(self.config.get("base_url", "https://api.openai.com")).rstrip("/")
        timeout = float(self.config.get("timeout", 30))

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": [{"role": item.role, "content": item.content} for item in normalized],
            "temperature": temperature,
            **kwargs,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        status, response_json = await self._post_json(
            url=f"{base_url}/v1/chat/completions",
            payload=payload,
            headers={"Authorization": f"Bearer {self.config['api_key']}"},
            timeout=timeout,
        )
        if status >= 400:
            message = _extract_error_message(response_json)
            raise LLMAPIError(f"OpenAI request failed: {message}", provider="openai")

        choices = response_json.get("choices") or []
        first_choice = choices[0] if choices else {}
        message_obj = first_choice.get("message") if isinstance(first_choice, Mapping) else {}
        usage_obj = response_json.get("usage") if isinstance(response_json, Mapping) else {}

        prompt_tokens = int((usage_obj or {}).get("prompt_tokens", 0))
        completion_tokens = int((usage_obj or {}).get("completion_tokens", 0))
        total_tokens = int((usage_obj or {}).get("total_tokens", prompt_tokens + completion_tokens))

        return LLMResponse(
            content=str((message_obj or {}).get("content", "")),
            model=str(response_json.get("model") or resolved_model),
            finish_reason=str(first_choice.get("finish_reason")) if isinstance(first_choice, Mapping) and first_choice.get("finish_reason") is not None else None,
            provider="openai",
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    async def health_check(self) -> bool:
        await self.generate([LLMMessage(role="user", content="ping")], max_tokens=1)
        return True


class GeminiLLMProvider(_HttpJsonClientMixin, BaseLLMProvider):
    provider_family = "llm"

    def validate_config(self) -> bool:
        if not str(self.config.get("api_key", "")).strip():
            raise LLMConfigError("GEMINI API key is required", provider="gemini")
        return True

    def get_provider_name(self) -> str:
        return "gemini"

    def get_available_models(self) -> list[str]:
        return ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

    async def generate(
        self,
        messages: Sequence[LLMMessage | Mapping[str, Any]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        normalized = self.normalize_messages(messages)
        resolved_model = model or str(self.config.get("model", "gemini-2.0-flash"))
        base_url = str(self.config.get("base_url", "https://generativelanguage.googleapis.com")).rstrip("/")
        timeout = float(self.config.get("timeout", 30))
        api_key = str(self.config.get("api_key"))

        system_texts = [m.content for m in normalized if m.role == "system" and m.content]
        non_system = [m for m in normalized if m.role != "system"]
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in non_system
        ]
        generation_config: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens

        payload: dict[str, Any] = {
            "contents": contents or [{"role": "user", "parts": [{"text": "ping"}]}],
            "generationConfig": generation_config,
            **kwargs,
        }
        if system_texts:
            payload["system_instruction"] = {"parts": [{"text": "\n".join(system_texts)}]}

        status, response_json = await self._post_json(
            url=f"{base_url}/v1beta/models/{resolved_model}:generateContent?key={api_key}",
            payload=payload,
            headers={},
            timeout=timeout,
        )
        if status >= 400:
            message = _extract_error_message(response_json)
            raise LLMAPIError(f"Gemini request failed: {message}", provider="gemini")

        candidates = response_json.get("candidates") or []
        first_candidate = candidates[0] if candidates else {}
        content_obj = first_candidate.get("content") if isinstance(first_candidate, Mapping) else {}
        parts = content_obj.get("parts") if isinstance(content_obj, Mapping) else []
        text_chunks = [str(part.get("text", "")) for part in parts if isinstance(part, Mapping)]

        usage_obj = response_json.get("usageMetadata") if isinstance(response_json, Mapping) else {}
        prompt_tokens = int((usage_obj or {}).get("promptTokenCount", 0))
        completion_tokens = int((usage_obj or {}).get("candidatesTokenCount", 0))
        total_tokens = int((usage_obj or {}).get("totalTokenCount", prompt_tokens + completion_tokens))

        return LLMResponse(
            content="".join(text_chunks),
            model=resolved_model,
            finish_reason=str(first_candidate.get("finishReason")) if isinstance(first_candidate, Mapping) and first_candidate.get("finishReason") is not None else None,
            provider="gemini",
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    async def health_check(self) -> bool:
        await self.generate([LLMMessage(role="user", content="ping")], max_tokens=1)
        return True


class AnthropicLLMProvider(_HttpJsonClientMixin, BaseLLMProvider):
    provider_family = "llm"

    def validate_config(self) -> bool:
        if not str(self.config.get("api_key", "")).strip():
            raise LLMConfigError("ANTHROPIC API key is required", provider="anthropic")
        return True

    def get_provider_name(self) -> str:
        return "anthropic"

    def get_available_models(self) -> list[str]:
        return ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest", "claude-3-opus-latest"]

    async def generate(
        self,
        messages: Sequence[LLMMessage | Mapping[str, Any]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        normalized = self.normalize_messages(messages)
        resolved_model = model or str(self.config.get("model", "claude-3-5-haiku-latest"))
        base_url = str(self.config.get("base_url", "https://api.anthropic.com")).rstrip("/")
        timeout = float(self.config.get("timeout", 30))
        anthropic_version = str(self.config.get("anthropic_version", "2023-06-01"))

        system_texts = [m.content for m in normalized if m.role == "system" and m.content]
        chat_messages = [
            {"role": "assistant" if m.role == "assistant" else "user", "content": m.content}
            for m in normalized
            if m.role != "system"
        ]

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": chat_messages or [{"role": "user", "content": "ping"}],
            "temperature": temperature,
            "max_tokens": int(max_tokens if max_tokens is not None else self.config.get("max_tokens", 256)),
            **kwargs,
        }
        if system_texts:
            payload["system"] = "\n".join(system_texts)

        status, response_json = await self._post_json(
            url=f"{base_url}/v1/messages",
            payload=payload,
            headers={
                "x-api-key": str(self.config["api_key"]),
                "anthropic-version": anthropic_version,
            },
            timeout=timeout,
        )
        if status >= 400:
            message = _extract_error_message(response_json)
            raise LLMAPIError(f"Anthropic request failed: {message}", provider="anthropic")

        content_items = response_json.get("content") or []
        text_chunks: list[str] = []
        for item in content_items:
            if isinstance(item, Mapping) and item.get("type") == "text":
                text_chunks.append(str(item.get("text", "")))

        usage_obj = response_json.get("usage") if isinstance(response_json, Mapping) else {}
        prompt_tokens = int((usage_obj or {}).get("input_tokens", 0))
        completion_tokens = int((usage_obj or {}).get("output_tokens", 0))
        total_tokens = prompt_tokens + completion_tokens

        return LLMResponse(
            content="".join(text_chunks),
            model=str(response_json.get("model") or resolved_model),
            finish_reason=str(response_json.get("stop_reason")) if response_json.get("stop_reason") is not None else None,
            provider="anthropic",
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    async def health_check(self) -> bool:
        await self.generate([LLMMessage(role="user", content="ping")], max_tokens=1)
        return True


class OpenAIEmbeddingProvider(_HttpJsonClientMixin, BaseEmbeddingProvider):
    provider_family = "embedding"

    def validate_config(self) -> bool:
        if not str(self.config.get("api_key", "")).strip():
            raise EmbeddingConfigError("OPENAI API key is required", provider="openai")
        return True

    def get_provider_name(self) -> str:
        return "openai"

    def get_available_models(self) -> list[str]:
        return ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]

    def get_embedding_dimension(self, model: str | None = None) -> int:
        resolved = model or str(self.config.get("model", "text-embedding-3-small"))
        if resolved == "text-embedding-3-large":
            return 3072
        if resolved == "text-embedding-ada-002":
            return 1536
        return 1536

    async def embed(
        self,
        texts: Sequence[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        resolved_model = model or str(self.config.get("model", "text-embedding-3-small"))
        base_url = str(self.config.get("base_url", "https://api.openai.com")).rstrip("/")
        timeout = float(self.config.get("timeout", 30))

        payload: dict[str, Any] = {
            "model": resolved_model,
            "input": list(texts),
            **kwargs,
        }

        status, response_json = await self._post_json(
            url=f"{base_url}/v1/embeddings",
            payload=payload,
            headers={"Authorization": f"Bearer {self.config['api_key']}"},
            timeout=timeout,
        )
        if status >= 400:
            message = _extract_error_message(response_json)
            raise EmbeddingAPIError(f"OpenAI request failed: {message}", provider="openai")

        data = response_json.get("data") or []
        vectors = [tuple(item.get("embedding") or []) for item in data if isinstance(item, Mapping)]
        usage_obj = response_json.get("usage") if isinstance(response_json, Mapping) else {}
        prompt_tokens = int((usage_obj or {}).get("prompt_tokens", 0))
        total_tokens = int((usage_obj or {}).get("total_tokens", prompt_tokens))

        return EmbeddingResult.from_vectors(
            embeddings=vectors,
            model=str(response_json.get("model") or resolved_model),
            usage=EmbeddingUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                total_tokens=total_tokens,
            ),
            provider="openai",
            dimension=self.get_embedding_dimension(resolved_model),
        )

    async def health_check(self) -> bool:
        result = await self.embed(["health check"])
        return len(result.embeddings) == 1 and len(result.embeddings[0]) > 0


class GeminiEmbeddingProvider(_HttpJsonClientMixin, BaseEmbeddingProvider):
    provider_family = "embedding"

    def validate_config(self) -> bool:
        if not str(self.config.get("api_key", "")).strip():
            raise EmbeddingConfigError("GEMINI API key is required", provider="gemini")
        return True

    def get_provider_name(self) -> str:
        return "gemini"

    def get_available_models(self) -> list[str]:
        return ["text-embedding-004", "gemini-embedding-001"]

    def get_embedding_dimension(self, model: str | None = None) -> int:
        del model
        configured = self.config.get("dimension")
        if configured is not None:
            return int(configured)
        return 768

    async def embed(
        self,
        texts: Sequence[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        del kwargs
        resolved_model = model or str(self.config.get("model", "text-embedding-004"))
        base_url = str(self.config.get("base_url", "https://generativelanguage.googleapis.com")).rstrip("/")
        timeout = float(self.config.get("timeout", 30))
        api_key = str(self.config.get("api_key"))

        vectors: list[Sequence[float]] = []
        prompt_tokens = 0

        for text in texts:
            status, response_json = await self._post_json(
                url=f"{base_url}/v1beta/models/{resolved_model}:embedContent?key={api_key}",
                payload={"content": {"parts": [{"text": text}] }},
                headers={},
                timeout=timeout,
            )
            if status >= 400:
                message = _extract_error_message(response_json)
                raise EmbeddingAPIError(f"Gemini request failed: {message}", provider="gemini")

            embedding_obj = response_json.get("embedding") if isinstance(response_json, Mapping) else {}
            vector = embedding_obj.get("values") if isinstance(embedding_obj, Mapping) else []
            vectors.append(tuple(vector or []))
            usage_obj = response_json.get("usageMetadata") if isinstance(response_json, Mapping) else {}
            prompt_tokens += int((usage_obj or {}).get("promptTokenCount", 0))

        return EmbeddingResult.from_vectors(
            embeddings=vectors,
            model=resolved_model,
            usage=EmbeddingUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                total_tokens=prompt_tokens,
            ),
            provider="gemini",
            dimension=self.get_embedding_dimension(resolved_model),
        )

    async def health_check(self) -> bool:
        result = await self.embed(["health check"])
        return len(result.embeddings) == 1 and len(result.embeddings[0]) > 0


class AnthropicEmbeddingProvider(_HttpJsonClientMixin, BaseEmbeddingProvider):
    provider_family = "embedding"

    def validate_config(self) -> bool:
        if not str(self.config.get("api_key", "")).strip():
            raise EmbeddingConfigError("ANTHROPIC API key is required", provider="anthropic")
        return True

    def get_provider_name(self) -> str:
        return "anthropic"

    def get_available_models(self) -> list[str]:
        return ["claude-embedding-v1"]

    def get_embedding_dimension(self, model: str | None = None) -> int:
        del model
        configured = self.config.get("dimension")
        if configured is not None:
            return int(configured)
        return 1024

    async def embed(
        self,
        texts: Sequence[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        resolved_model = model or str(self.config.get("model", "claude-embedding-v1"))
        base_url = str(self.config.get("base_url", "https://api.anthropic.com")).rstrip("/")
        timeout = float(self.config.get("timeout", 30))
        anthropic_version = str(self.config.get("anthropic_version", "2023-06-01"))

        payload: dict[str, Any] = {
            "model": resolved_model,
            "input": list(texts),
            **kwargs,
        }

        status, response_json = await self._post_json(
            url=f"{base_url}/v1/embeddings",
            payload=payload,
            headers={
                "x-api-key": str(self.config["api_key"]),
                "anthropic-version": anthropic_version,
            },
            timeout=timeout,
        )
        if status >= 400:
            message = _extract_error_message(response_json)
            raise EmbeddingAPIError(f"Anthropic request failed: {message}", provider="anthropic")

        vectors = _extract_embedding_vectors(response_json)
        usage_obj = response_json.get("usage") if isinstance(response_json, Mapping) else {}
        prompt_tokens = int((usage_obj or {}).get("input_tokens", 0))
        total_tokens = int((usage_obj or {}).get("total_tokens", prompt_tokens))

        return EmbeddingResult.from_vectors(
            embeddings=vectors,
            model=str(response_json.get("model") or resolved_model),
            usage=EmbeddingUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                total_tokens=total_tokens,
            ),
            provider="anthropic",
            dimension=self.get_embedding_dimension(resolved_model),
        )

    async def health_check(self) -> bool:
        result = await self.embed(["health check"])
        return len(result.embeddings) == 1 and len(result.embeddings[0]) > 0


class OllamaLLMProvider(_HttpJsonClientMixin, BaseLLMProvider):
    """LLM provider that targets a locally-running Ollama server.

    No API key is required.  The server must already be running and the
    requested model must have been pulled (``ollama pull <model>``).

    Supported config keys:
        base_url    - Ollama server address (default: http://localhost:11434)
        model       - Model tag to use (default: llama3.2)
        timeout     - Request timeout in seconds (default: 120)
    """

    provider_family = "llm"

    def validate_config(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "ollama"

    def get_available_models(self) -> list[str]:
        return ["llama3.2", "llama3.1", "mistral", "qwen2.5", "phi4", "deepseek-r1"]

    async def generate(
        self,
        messages: Sequence[LLMMessage | Mapping[str, Any]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        normalized = self.normalize_messages(messages)
        resolved_model = model or str(self.config.get("model", "llama3.2"))
        base_url = str(self.config.get("base_url", "http://localhost:11434")).rstrip("/")
        timeout = float(self.config.get("timeout", 120))

        options: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": [{"role": m.role, "content": m.content} for m in normalized],
            "stream": False,
            "options": options,
            **kwargs,
        }

        status, response_json = await self._post_json(
            url=f"{base_url}/api/chat",
            payload=payload,
            headers={},
            timeout=timeout,
        )
        if status >= 400:
            message = _extract_error_message(response_json)
            raise LLMAPIError(f"Ollama request failed: {message}", provider="ollama")

        message_obj = response_json.get("message") if isinstance(response_json, Mapping) else {}
        prompt_tokens = int(response_json.get("prompt_eval_count") or 0)
        completion_tokens = int(response_json.get("eval_count") or 0)

        return LLMResponse(
            content=str((message_obj or {}).get("content", "")),
            model=str(response_json.get("model") or resolved_model),
            finish_reason=str(response_json.get("done_reason")) if response_json.get("done_reason") is not None else None,
            provider="ollama",
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

    async def health_check(self) -> bool:
        base_url = str(self.config.get("base_url", "http://localhost:11434")).rstrip("/")
        timeout = float(self.config.get("timeout", 10))
        status, _ = await self._get_json(url=f"{base_url}/api/version", timeout=timeout)
        return status == 200


class OllamaEmbeddingProvider(_HttpJsonClientMixin, BaseEmbeddingProvider):
    """Embedding provider that targets a locally-running Ollama server.

    No API key is required.  Uses Ollama's ``/api/embed`` endpoint which
    supports batching multiple texts in a single request.

    Supported config keys:
        base_url    - Ollama server address (default: http://localhost:11434)
        model       - Embedding model tag (default: nomic-embed-text)
        dimension   - Expected vector size override (default: inferred from model)
        timeout     - Request timeout in seconds (default: 120)
    """

    provider_family = "embedding"

    # Known output dimensions for common Ollama embedding models.
    _KNOWN_DIMENSIONS: dict[str, int] = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
        "snowflake-arctic-embed": 1024,
        "bge-m3": 1024,
    }

    def validate_config(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "ollama"

    def get_available_models(self) -> list[str]:
        return list(self._KNOWN_DIMENSIONS)

    def get_embedding_dimension(self, model: str | None = None) -> int:
        if self.config.get("dimension") is not None:
            return int(self.config["dimension"])
        resolved = model or str(self.config.get("model", "nomic-embed-text"))
        return self._KNOWN_DIMENSIONS.get(resolved, 768)

    async def embed(
        self,
        texts: Sequence[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        del kwargs
        resolved_model = model or str(self.config.get("model", "nomic-embed-text"))
        base_url = str(self.config.get("base_url", "http://localhost:11434")).rstrip("/")
        timeout = float(self.config.get("timeout", 120))

        status, response_json = await self._post_json(
            url=f"{base_url}/api/embed",
            payload={"model": resolved_model, "input": list(texts)},
            headers={},
            timeout=timeout,
        )
        if status >= 400:
            message = _extract_error_message(response_json)
            raise EmbeddingAPIError(f"Ollama request failed: {message}", provider="ollama")

        raw_embeddings = response_json.get("embeddings") or []
        vectors: list[tuple[float, ...]] = [tuple(vec) for vec in raw_embeddings]
        prompt_tokens = int(response_json.get("prompt_eval_count") or 0)
        dimension = self.get_embedding_dimension(resolved_model)

        return EmbeddingResult.from_vectors(
            embeddings=vectors,
            model=str(response_json.get("model") or resolved_model),
            usage=EmbeddingUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                total_tokens=prompt_tokens,
            ),
            provider="ollama",
            dimension=dimension,
        )

    async def health_check(self) -> bool:
        base_url = str(self.config.get("base_url", "http://localhost:11434")).rstrip("/")
        timeout = float(self.config.get("timeout", 10))
        status, _ = await self._get_json(url=f"{base_url}/api/version", timeout=timeout)
        return status == 200


def _extract_error_message(response_json: Mapping[str, Any]) -> str:
    err = response_json.get("error")
    if isinstance(err, Mapping):
        return str(err.get("message") or err)
    if err is not None:
        return str(err)
    return "unknown error"


def _extract_embedding_vectors(response_json: Mapping[str, Any]) -> list[Sequence[float]]:
    data = response_json.get("data")
    if isinstance(data, Sequence):
        vectors: list[Sequence[float]] = []
        for item in data:
            if isinstance(item, Mapping) and isinstance(item.get("embedding"), Sequence):
                vectors.append(item.get("embedding") or [])
        if vectors:
            return vectors

    embeddings = response_json.get("embeddings")
    if isinstance(embeddings, Sequence):
        if embeddings and isinstance(embeddings[0], Mapping):
            return [item.get("embedding") or [] for item in embeddings if isinstance(item, Mapping)]
        return [item for item in embeddings if isinstance(item, Sequence)]

    single = response_json.get("embedding")
    if isinstance(single, Sequence):
        return [single]

    return []


def register_builtin_providers(
    *,
    embedding_registry: ProviderRegistry | None = None,
    llm_registry: LLMProviderRegistry | None = None,
) -> None:
    """Register built-in OpenAI/Gemini/Anthropic/Ollama providers."""
    embedding_target = embedding_registry or default_provider_registry
    llm_target = llm_registry or default_llm_provider_registry

    embedding_target.register("openai", OpenAIEmbeddingProvider)
    embedding_target.register("gemini", GeminiEmbeddingProvider)
    embedding_target.register("anthropic", AnthropicEmbeddingProvider)
    embedding_target.register("ollama", OllamaEmbeddingProvider)

    llm_target.register("openai", OpenAILLMProvider)
    llm_target.register("gemini", GeminiLLMProvider)
    llm_target.register("anthropic", AnthropicLLMProvider)
    llm_target.register("ollama", OllamaLLMProvider)


# Auto-register built-in providers into default registries so downstream
# services can switch via env only (LLM_PROVIDER / EMBEDDING_PROVIDER).
register_builtin_providers()
