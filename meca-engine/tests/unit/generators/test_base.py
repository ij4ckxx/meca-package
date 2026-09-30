"""Unit tests for meca_engine.generators.base.BaseGenerator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from meca_engine.exceptions import GeneratorInvariantError, ModelBuildError
from meca_engine.generators.base import BaseGenerator
from meca_engine.generators.result import GenerationResult

if TYPE_CHECKING:
    from meca_engine.generators.context import GeneratorContext

pytestmark = pytest.mark.unit


class _EchoGenerator(BaseGenerator[str]):
    @property
    def generator_name(self) -> str:
        return "echo"

    def _generate(self, context: GeneratorContext) -> str:
        return f"<article id='{context.model.identity.article_id}'/>"


class _FailingGenerator(BaseGenerator[str]):
    @property
    def generator_name(self) -> str:
        return "failing"

    def _generate(self, context: GeneratorContext) -> str:
        raise ValueError("unexpected internal failure")


class _AlreadyClassifiedFailureGenerator(BaseGenerator[str]):
    @property
    def generator_name(self) -> str:
        return "already-classified"

    def _generate(self, context: GeneratorContext) -> str:
        raise ModelBuildError("a lower-layer failure", article_id=context.model.identity.article_id)


class _DiagnosticEmittingGenerator(BaseGenerator[str]):
    @property
    def generator_name(self) -> str:
        return "diagnostic-emitting"

    def _generate(self, context: GeneratorContext) -> str:
        context.diagnostics.warn(self.generator_name, "something worth noting")
        return "<article/>"


def test_generate_returns_a_generation_result(generator_context: GeneratorContext) -> None:
    result = _EchoGenerator().generate(generator_context)

    assert isinstance(result, GenerationResult)
    assert result.document == "<article id='cs-2025-0001'/>"
    assert result.generator_name == "echo"
    assert result.article_id == "cs-2025-0001"
    assert result.duration_ms >= 0
    assert result.diagnostics == ()


def test_generate_wraps_an_unexpected_exception_in_generator_invariant_error(
    generator_context: GeneratorContext,
) -> None:
    with pytest.raises(GeneratorInvariantError) as exc_info:
        _FailingGenerator().generate(generator_context)

    assert exc_info.value.article_id == "cs-2025-0001"
    assert exc_info.value.stage == "generators.failing"
    assert isinstance(exc_info.value.inner_cause, ValueError)


def test_generate_propagates_an_already_classified_engine_error_unchanged(
    generator_context: GeneratorContext,
) -> None:
    with pytest.raises(ModelBuildError):
        _AlreadyClassifiedFailureGenerator().generate(generator_context)


def test_generate_includes_diagnostics_recorded_during_generation(
    generator_context: GeneratorContext,
) -> None:
    result = _DiagnosticEmittingGenerator().generate(generator_context)

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].message == "something worth noting"


def test_base_generator_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BaseGenerator()  # type: ignore[abstract]
