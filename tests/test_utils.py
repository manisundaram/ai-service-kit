import re

from ai_service_kit.utils import mask_secret, normalize_name, utc_now_iso


def test_normalize_name_strips_and_lowercases() -> None:
    assert normalize_name(" OpenAI ") == "openai"


def test_normalize_name_rejects_empty_values() -> None:
    try:
        normalize_name("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for empty normalized name")


def test_mask_secret_preserves_edges() -> None:
    assert mask_secret("abcdefgh12345678", prefix=4, suffix=4) == "abcd********5678"


def test_mask_secret_masks_short_values_fully() -> None:
    assert mask_secret("short", prefix=4, suffix=4) == "*****"


def test_utc_now_iso_returns_utc_timestamp() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*Z", utc_now_iso())
