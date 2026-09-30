"""Unit tests for meca_engine.generators.context.GeneratorContext."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from meca_engine.generators.context import GeneratorContext

pytestmark = pytest.mark.unit


def test_context_holds_every_dependency(generator_context: GeneratorContext) -> None:
    assert generator_context.model.identity.article_id == "cs-2025-0001"
    assert generator_context.journal_config.journal_id == "clinical-science"
    assert generator_context.publisher_config.publisher_id == "portland-press"
    assert generator_context.runtime_config.doi_registry.backend == "postgres"
    assert generator_context.feature_flags.strict_replication_mode is False


def test_context_is_frozen(generator_context: GeneratorContext) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        generator_context.model = generator_context.model  # type: ignore[misc]


def test_diagnostics_collector_is_mutable_through_the_frozen_context(
    generator_context: GeneratorContext,
) -> None:
    generator_context.diagnostics.warn("raw_xml", "an observation")

    assert len(generator_context.diagnostics.diagnostics) == 1
