"""Unit tests for meca_engine.retry."""

from __future__ import annotations

import pytest

from meca_engine.config.schema import RetrySettings
from meca_engine.exceptions.article_errors import (
    DoiRegistryUnavailableError,
    FileReferenceMissingError,
)
from meca_engine.retry import classify_retryable, compute_backoff_seconds, run_with_retry

pytestmark = pytest.mark.unit

_SETTINGS = RetrySettings(
    max_attempts=3, backoff_base_seconds=0.0, backoff_multiplier=2.0, backoff_max_seconds=1.0
)


def test_classify_retryable_true_for_article_transient_error() -> None:
    exc = DoiRegistryUnavailableError("unreachable", article_id="a-1", stage="test")
    assert classify_retryable(exc) is True


def test_classify_retryable_false_for_deterministic_meca_engine_error() -> None:
    exc = FileReferenceMissingError("missing", article_id="a-1", stage="test")
    assert classify_retryable(exc) is False


def test_classify_retryable_true_for_transient_stdlib_exception() -> None:
    assert classify_retryable(ConnectionError("dropped")) is True
    assert classify_retryable(TimeoutError("timed out")) is True
    assert classify_retryable(OSError("resource busy")) is True


def test_classify_retryable_false_for_missing_file() -> None:
    assert classify_retryable(FileNotFoundError("no such file")) is False


def test_classify_retryable_false_for_unrelated_exception() -> None:
    assert classify_retryable(ValueError("bad input")) is False


def test_compute_backoff_seconds_exponential_and_capped() -> None:
    settings = RetrySettings(
        max_attempts=5, backoff_base_seconds=1.0, backoff_multiplier=2.0, backoff_max_seconds=3.0
    )
    assert compute_backoff_seconds(1, settings) == 1.0
    assert compute_backoff_seconds(2, settings) == 2.0
    assert compute_backoff_seconds(3, settings) == 3.0  # capped (would be 4.0)


def test_run_with_retry_succeeds_without_retry() -> None:
    assert run_with_retry(lambda: 42, settings=_SETTINGS) == 42


def test_run_with_retry_retries_transient_then_succeeds() -> None:
    attempts = {"count": 0}

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ConnectionError("dropped")
        return "ok"

    retries_seen: list[int] = []
    result = run_with_retry(
        flaky, settings=_SETTINGS, on_retry=lambda attempt, exc, delay: retries_seen.append(attempt)
    )

    assert result == "ok"
    assert attempts["count"] == 2
    assert retries_seen == [1]


def test_run_with_retry_never_retries_deterministic_failure() -> None:
    calls = {"count": 0}

    def always_fails() -> None:
        calls["count"] += 1
        raise FileReferenceMissingError("missing", article_id="a-1", stage="test")

    with pytest.raises(FileReferenceMissingError):
        run_with_retry(always_fails, settings=_SETTINGS)
    assert calls["count"] == 1


def test_run_with_retry_raises_after_max_attempts() -> None:
    calls = {"count": 0}

    def always_flaky() -> None:
        calls["count"] += 1
        raise ConnectionError("dropped")

    with pytest.raises(ConnectionError):
        run_with_retry(always_flaky, settings=_SETTINGS)
    assert calls["count"] == _SETTINGS.max_attempts
