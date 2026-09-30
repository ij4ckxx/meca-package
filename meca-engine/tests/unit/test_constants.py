"""Unit tests for meca_engine.constants."""

from __future__ import annotations

import pytest

from meca_engine.constants import Environment, LogCategory, LogSeverity

pytestmark = pytest.mark.unit


def test_environment_values() -> None:
    assert {e.value for e in Environment} == {"dev", "staging", "production"}


def test_log_category_values() -> None:
    assert {c.value for c in LogCategory} == {
        "structured",
        "audit",
        "performance",
        "error",
        "debug",
    }


def test_log_severity_values() -> None:
    assert {s.value for s in LogSeverity} == {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}


def test_environment_is_constructible_from_its_own_value() -> None:
    for environment in Environment:
        assert Environment(environment.value) is environment
