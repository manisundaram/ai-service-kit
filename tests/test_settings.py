import os

import pytest

pydantic_settings = pytest.importorskip("pydantic_settings")
assert pydantic_settings is not None

from ai_service_kit.settings import (
    ServiceSettings,
    build_provider_config,
    build_two_level_provider_config,
    parse_csv_list,
    resolve_provider_setting,
)


class DemoSettings(ServiceSettings):
    openai_api_key: str | None = None
    gemini_api_key: str | None = None


def test_parse_csv_list_supports_string_and_list() -> None:
    assert parse_csv_list("a, b, c") == ["a", "b", "c"]
    assert parse_csv_list([" a ", "", "b"]) == ["a", "b"]


def test_service_settings_parses_cors_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, http://localhost:5173")
    settings = DemoSettings()
    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:5173"]


def test_service_settings_masked_secrets_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-1234567890")
    settings = DemoSettings()
    masked = settings.masked_secrets(["openai_api_key"])
    assert masked["openai_api_key"] is not None
    assert "*" in masked["openai_api_key"]


def test_build_provider_config_selects_by_provider_type() -> None:
    selected = build_provider_config(
        provider_type="OpenAI",
        providers={
            "openai": {"api_key": "secret", "model": "gpt-4o-mini"},
            "gemini": {"api_key": "other"},
        },
    )
    assert selected["model"] == "gpt-4o-mini"


def test_build_provider_config_returns_empty_for_unknown() -> None:
    assert build_provider_config(provider_type="unknown", providers={"openai": {"x": 1}}) == {}


def test_debug_snapshot_includes_operational_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "demo-service")
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    settings = DemoSettings()
    snapshot = settings.debug_snapshot(secret_fields=["openai_api_key"], extras={"provider_type": "openai"})
    assert snapshot["app_name"] == "demo-service"
    assert snapshot["app_version"] == "1.2.3"
    assert snapshot["provider_type"] == "openai"
    assert "masked_secrets" in snapshot


def test_resolve_provider_setting_prefers_family_specific_value() -> None:
    values = {
        "LLM_OPENAI_API_KEY": "family-key",
        "OPENAI_API_KEY": "shared-key",
    }

    value, source = resolve_provider_setting(
        values=values,
        family="llm",
        provider="openai",
        field="api_key",
    )

    assert value == "family-key"
    assert source == "LLM_OPENAI_API_KEY"


def test_resolve_provider_setting_falls_back_to_shared_provider() -> None:
    values = {
        "OPENAI_API_KEY": "shared-key",
    }

    value, source = resolve_provider_setting(
        values=values,
        family="embedding",
        provider="openai",
        field="api_key",
    )

    assert value == "shared-key"
    assert source == "OPENAI_API_KEY"


def test_resolve_provider_setting_treats_blank_family_specific_as_missing() -> None:
    values = {
        "LLM_OPENAI_API_KEY": "  ",
        "OPENAI_API_KEY": "shared-key",
    }

    value, source = resolve_provider_setting(
        values=values,
        family="llm",
        provider="openai",
        field="api_key",
    )

    assert value == "shared-key"
    assert source == "OPENAI_API_KEY"


def test_build_two_level_provider_config_resolves_requested_fields() -> None:
    values = {
        "EMBEDDING_OPENAI_MODEL": "text-embedding-3-large",
        "OPENAI_API_KEY": "shared-key",
        "OPENAI_TIMEOUT": 20,
    }

    config = build_two_level_provider_config(
        values=values,
        family="embedding",
        provider_type="openai",
        fields=["api_key", "model", "timeout", "base_url"],
    )

    assert config == {
        "api_key": "shared-key",
        "model": "text-embedding-3-large",
        "timeout": 20,
    }


def test_two_level_fallback_supports_gemini_family_override() -> None:
    values = {
        "LLM_GEMINI_API_KEY": "gemini-llm-key",
        "GEMINI_API_KEY": "gemini-shared-key",
        "GEMINI_MODEL": "gemini-2.0-flash",
    }

    config = build_two_level_provider_config(
        values=values,
        family="llm",
        provider_type="gemini",
        fields=["api_key", "model"],
    )

    assert config == {
        "api_key": "gemini-llm-key",
        "model": "gemini-2.0-flash",
    }


def test_two_level_fallback_supports_anthropic_shared_defaults() -> None:
    values = {
        "ANTHROPIC_API_KEY": "anthropic-shared-key",
        "ANTHROPIC_MODEL": "claude-3-5-haiku-latest",
    }

    config = build_two_level_provider_config(
        values=values,
        family="embedding",
        provider_type="anthropic",
        fields=["api_key", "model"],
    )

    assert config == {
        "api_key": "anthropic-shared-key",
        "model": "claude-3-5-haiku-latest",
    }


def test_build_two_level_provider_config_skips_missing_fields() -> None:
    values = {
        "OPENAI_MODEL": "gpt-4o-mini",
    }

    config = build_two_level_provider_config(
        values=values,
        family="llm",
        provider_type="openai",
        fields=["api_key", "model", "timeout"],
    )

    assert config == {
        "model": "gpt-4o-mini",
    }