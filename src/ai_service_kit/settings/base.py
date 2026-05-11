"""Reusable pydantic-settings patterns for AI services."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..utils import mask_secret


def parse_csv_list(value: str | Sequence[str] | None) -> list[str]:
    """Parse comma-separated values or return an already normalized list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def _has_setting_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def resolve_provider_setting(
    *,
    values: Mapping[str, Any],
    family: str,
    provider: str,
    field: str,
) -> tuple[Any | None, str | None]:
    """Resolve a provider setting with 2-level fallback.

    Resolution order:
    1. family-specific provider key (for example LLM_OPENAI_API_KEY)
    2. shared provider key (for example OPENAI_API_KEY)
    """
    normalized_family = family.strip().lower()
    normalized_provider = provider.strip().lower()
    normalized_field = field.strip().lower()

    candidate_keys = [
        f"{normalized_family}_{normalized_provider}_{normalized_field}",
        f"{normalized_provider}_{normalized_field}",
    ]

    for key in candidate_keys:
        variants = (key, key.upper(), key.lower())
        for variant in variants:
            if variant in values and _has_setting_value(values[variant]):
                return values[variant], variant

    return None, None


def build_two_level_provider_config(
    *,
    values: Mapping[str, Any],
    family: str,
    provider_type: str,
    fields: Sequence[str],
) -> dict[str, Any]:
    """Build provider config using 2-level fallback for requested fields."""
    resolved: dict[str, Any] = {}
    for field in fields:
        value, _ = resolve_provider_setting(
            values=values,
            family=family,
            provider=provider_type,
            field=field,
        )
        if value is not None:
            resolved[field] = value
    return resolved


class ServiceSettings(BaseSettings):
    """Generic settings primitives reusable across FastAPI AI services."""

    app_name: str = Field(default="ai-service", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    mock_mode: bool = Field(default=False, alias="MOCK_MODE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_cors: bool = Field(default=True, alias="ENABLE_CORS")
    cors_origins: list[str] = Field(default_factory=list, alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
        enable_decoding=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | Sequence[str] | None) -> list[str]:
        return parse_csv_list(value)

    def operational_settings(self) -> dict[str, Any]:
        """Return operational settings safe to include in health/debug output."""
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "app_env": self.app_env,
            "app_debug": self.app_debug,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "mock_mode": self.mock_mode,
            "log_level": self.log_level,
            "enable_cors": self.enable_cors,
            "cors_origins": list(self.cors_origins),
        }

    def masked_secrets(
        self,
        secret_fields: Sequence[str],
        *,
        extras: Mapping[str, str | None] | None = None,
    ) -> dict[str, str | None]:
        """Mask named secret fields and optional extra secret values."""
        masked = {field_name: mask_secret(getattr(self, field_name, None)) for field_name in secret_fields}
        if extras:
            masked.update({key: mask_secret(value) for key, value in extras.items()})
        return masked

    def debug_snapshot(
        self,
        *,
        secret_fields: Sequence[str] = (),
        extras: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Return a debug-safe settings snapshot with optional secret masking."""
        snapshot: dict[str, Any] = dict(self.operational_settings())
        if secret_fields:
            snapshot["masked_secrets"] = self.masked_secrets(secret_fields)
        if extras:
            snapshot.update(dict(extras))
        return snapshot


def build_provider_config(
    *,
    provider_type: str,
    providers: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Select provider configuration by normalized provider type."""
    normalized_provider = provider_type.strip().lower()
    selected = providers.get(normalized_provider)
    if selected is None:
        return {}
    return dict(selected)