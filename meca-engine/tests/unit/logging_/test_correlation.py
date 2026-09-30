"""Unit tests for meca_engine.logging_.correlation."""

from __future__ import annotations

import pytest

from meca_engine.logging_.correlation import (
    correlation_scope,
    get_correlation_id,
    get_trace_id,
    trace_scope,
)

pytestmark = pytest.mark.unit


def test_ids_are_unset_by_default() -> None:
    assert get_correlation_id() is None
    assert get_trace_id() is None


def test_correlation_scope_sets_and_restores() -> None:
    with correlation_scope("run-2026-09-07-0001"):
        assert get_correlation_id() == "run-2026-09-07-0001"
    assert get_correlation_id() is None


def test_trace_scope_sets_and_restores() -> None:
    with trace_scope("cs-2025-8827"):
        assert get_trace_id() == "cs-2025-8827"
    assert get_trace_id() is None


def test_scopes_compose() -> None:
    with correlation_scope("run-1"), trace_scope("article-1"):
        assert get_correlation_id() == "run-1"
        assert get_trace_id() == "article-1"
    assert get_correlation_id() is None
    assert get_trace_id() is None


def test_nested_trace_scope_restores_outer_value() -> None:
    with trace_scope("outer-article"):
        with trace_scope("inner-article"):
            assert get_trace_id() == "inner-article"
        assert get_trace_id() == "outer-article"
    assert get_trace_id() is None


def test_scope_restores_even_on_exception() -> None:
    with pytest.raises(RuntimeError):
        with trace_scope("article-that-fails"):
            raise RuntimeError("boom")
    assert get_trace_id() is None
