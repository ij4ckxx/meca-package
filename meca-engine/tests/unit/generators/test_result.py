"""Unit tests for meca_engine.generators.result.GenerationResult."""

from __future__ import annotations

import dataclasses

import pytest

from meca_engine.generators.result import GenerationResult

pytestmark = pytest.mark.unit


def test_generation_result_holds_every_field() -> None:
    result: GenerationResult[str] = GenerationResult(
        document="<article/>",
        generator_name="raw_xml",
        article_id="cs-2025-8827",
        duration_ms=12.5,
        diagnostics=(),
    )

    assert result.document == "<article/>"
    assert result.generator_name == "raw_xml"
    assert result.article_id == "cs-2025-8827"
    assert result.duration_ms == 12.5
    assert result.diagnostics == ()


def test_generation_result_is_frozen() -> None:
    result: GenerationResult[str] = GenerationResult(
        document="<article/>",
        generator_name="raw_xml",
        article_id="cs-2025-8827",
        duration_ms=12.5,
        diagnostics=(),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.document = "changed"  # type: ignore[misc]
