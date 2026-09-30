"""Unit tests for meca_engine.exceptions.batch_errors.

Verifies every batch-level exception is non-retryable by default and is
not tied to a single article_id (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.3).
"""

from __future__ import annotations

import pytest

from meca_engine.exceptions.batch_errors import (
    BatchLevelError,
    CheckpointStoreFatalError,
    ConfigurationError,
    CredentialsRevokedError,
    DtdFilesMissingError,
    SystemicDependencyOutageError,
)

pytestmark = pytest.mark.unit

BATCH_LEVEL_CLASSES = (
    ConfigurationError,
    DtdFilesMissingError,
    CredentialsRevokedError,
    CheckpointStoreFatalError,
    SystemicDependencyOutageError,
)


@pytest.mark.parametrize("error_class", BATCH_LEVEL_CLASSES)
def test_batch_level_errors_are_never_retryable(error_class: type[BatchLevelError]) -> None:
    error = error_class("halt the run")

    assert error.retryable is False
    assert isinstance(error, BatchLevelError)


@pytest.mark.parametrize("error_class", BATCH_LEVEL_CLASSES)
def test_batch_level_errors_default_to_no_article_id(error_class: type[BatchLevelError]) -> None:
    error = error_class("halt the run")

    assert error.article_id is None
