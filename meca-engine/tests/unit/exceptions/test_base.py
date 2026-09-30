"""Unit tests for meca_engine.exceptions.base.MecaEngineError."""

from __future__ import annotations

import pytest

from meca_engine.exceptions.base import MecaEngineError

pytestmark = pytest.mark.unit


class _ExampleError(MecaEngineError):
    """A concrete subclass used only to exercise the base class."""


def test_default_fields_are_none_or_empty() -> None:
    error = _ExampleError("something went wrong")

    assert error.message == "something went wrong"
    assert error.article_id is None
    assert error.stage == ""
    assert error.rule_id is None
    assert error.inner_cause is None
    assert str(error) == "something went wrong"


def test_all_fields_are_captured() -> None:
    cause = ValueError("root cause")

    error = _ExampleError(
        "wrapped failure",
        article_id="cs-2025-8827",
        stage="meca_engine.extraction.kriyadocs_parser",
        rule_id="BR-001",
        inner_cause=cause,
    )

    assert error.article_id == "cs-2025-8827"
    assert error.stage == "meca_engine.extraction.kriyadocs_parser"
    assert error.rule_id == "BR-001"
    assert error.inner_cause is cause


def test_retryable_class_default_can_be_overridden_per_instance() -> None:
    class _RetryableByDefaultError(MecaEngineError):
        retryable = True

    default_instance = _RetryableByDefaultError("default")
    overridden_instance = _RetryableByDefaultError("overridden", retryable=False)

    assert default_instance.retryable is True
    assert overridden_instance.retryable is False


def test_repr_is_informative() -> None:
    error = _ExampleError("boom", article_id="cs-2025-8827", stage="stage.x", rule_id="BR-042")

    representation = repr(error)

    assert "_ExampleError" in representation
    assert "cs-2025-8827" in representation
    assert "BR-042" in representation


def test_is_a_real_exception() -> None:
    with pytest.raises(_ExampleError):
        raise _ExampleError("must be raisable")
