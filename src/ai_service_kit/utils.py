"""Shared utility helpers used across the package."""

from __future__ import annotations

from datetime import datetime, timezone


def normalize_name(value: str) -> str:
    """Normalize registry and provider names to a stable lowercase key."""
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("Name must not be empty")
    return normalized


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return utc_now().isoformat().replace("+00:00", "Z")


def mask_secret(secret: str | None, *, prefix: int = 4, suffix: int = 4) -> str | None:
    """Mask a secret while keeping a small prefix and suffix visible."""
    if secret is None:
        return None
    if prefix < 0 or suffix < 0:
        raise ValueError("prefix and suffix must be non-negative")
    if len(secret) <= prefix + suffix:
        return "*" * len(secret)
    return f"{secret[:prefix]}{'*' * (len(secret) - prefix - suffix)}{secret[-suffix:]}"
