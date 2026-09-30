"""Unit tests for meca_engine.logging_.performance.PerformanceTimer."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from meca_engine.logging_.performance import PerformanceTimer
from meca_engine.logging_.structured_logger import StructuredLogger

if TYPE_CHECKING:
    from collections.abc import Mapping

pytestmark = pytest.mark.unit


def test_emits_a_performance_event_on_successful_exit() -> None:
    logger = MagicMock(spec=StructuredLogger)

    with PerformanceTimer(logger, "extraction.parse", context={"article_id": "cs-2025-8827"}):
        time.sleep(0.001)

    logger.performance.assert_called_once()
    _, kwargs = logger.performance.call_args
    assert kwargs["stage"] == "extraction.parse"
    assert kwargs["duration_ms"] > 0
    context: Mapping[str, Any] = kwargs["context"]
    assert context["article_id"] == "cs-2025-8827"
    assert context["succeeded"] is True


def test_emits_a_performance_event_even_when_the_block_raises() -> None:
    logger = MagicMock(spec=StructuredLogger)

    with pytest.raises(RuntimeError):
        with PerformanceTimer(logger, "packaging.build"):
            raise RuntimeError("disk full")

    logger.performance.assert_called_once()
    _, kwargs = logger.performance.call_args
    assert kwargs["context"]["succeeded"] is False


def test_duration_ms_is_none_before_exit_and_set_after() -> None:
    logger = MagicMock(spec=StructuredLogger)
    timer = PerformanceTimer(logger, "extraction.parse")

    with timer:
        assert timer.duration_ms is None

    assert timer.duration_ms is not None
    assert timer.duration_ms >= 0


def test_duration_ms_is_set_even_when_the_block_raises() -> None:
    logger = MagicMock(spec=StructuredLogger)
    timer = PerformanceTimer(logger, "packaging.build")

    with pytest.raises(RuntimeError), timer:
        raise RuntimeError("disk full")

    assert timer.duration_ms is not None
