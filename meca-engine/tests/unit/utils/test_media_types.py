"""Unit tests for meca_engine.utils.media_types.resolve_media_type."""

from __future__ import annotations

import pytest

from meca_engine.config.schema import MediaTypeConfig
from meca_engine.utils.media_types import resolve_media_type

pytestmark = pytest.mark.unit


@pytest.fixture
def media_type_config() -> MediaTypeConfig:
    return MediaTypeConfig(
        mappings={".pdf": "application/pdf", ".jpg": "image/jpeg"},
        unmapped_extension_policy="warn_and_default",
        unmapped_extension_default="application/octet-stream",
    )


def test_mapped_extension_resolves_and_reports_matched(media_type_config: MediaTypeConfig) -> None:
    media_type, matched = resolve_media_type("figure.pdf", media_type_config)

    assert media_type == "application/pdf"
    assert matched is True


def test_extension_matching_is_case_insensitive(media_type_config: MediaTypeConfig) -> None:
    media_type, matched = resolve_media_type("FIGURE.JPG", media_type_config)

    assert media_type == "image/jpeg"
    assert matched is True


def test_unmapped_extension_falls_back_to_default_and_reports_unmatched(
    media_type_config: MediaTypeConfig,
) -> None:
    media_type, matched = resolve_media_type("data.zip", media_type_config)

    assert media_type == "application/octet-stream"
    assert matched is False


def test_extensionless_filename_falls_back_to_default(media_type_config: MediaTypeConfig) -> None:
    media_type, matched = resolve_media_type("README", media_type_config)

    assert media_type == "application/octet-stream"
    assert matched is False


def test_only_the_extension_is_consulted_not_the_full_path(
    media_type_config: MediaTypeConfig,
) -> None:
    media_type, matched = resolve_media_type(
        "/staged/R1/Supplementary Table 2.pdf", media_type_config
    )

    assert media_type == "application/pdf"
    assert matched is True
