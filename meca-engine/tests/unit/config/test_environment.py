"""Unit tests for meca_engine.config.environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.config.environment import load_environment_settings
from meca_engine.constants import Environment
from meca_engine.exceptions import ConfigurationError

pytestmark = pytest.mark.unit


def test_defaults_when_no_environment_variables_set() -> None:
    settings = load_environment_settings(env={})

    assert settings.environment is Environment.DEV
    assert settings.config_dir == Path("config")
    assert settings.debug_logging_enabled is False


def test_reads_explicit_environment_variables() -> None:
    settings = load_environment_settings(
        env={
            "MECA_ENGINE_ENVIRONMENT": "production",
            "MECA_ENGINE_CONFIG_DIR": "/opt/meca-engine/config",
            "MECA_ENGINE_DEBUG_LOGGING": "true",
        }
    )

    assert settings.environment is Environment.PRODUCTION
    assert settings.config_dir == Path("/opt/meca-engine/config")
    assert settings.debug_logging_enabled is True


@pytest.mark.parametrize("truthy_value", ["1", "true", "True", "YES", "on"])
def test_debug_logging_truthy_values(truthy_value: str) -> None:
    settings = load_environment_settings(env={"MECA_ENGINE_DEBUG_LOGGING": truthy_value})

    assert settings.debug_logging_enabled is True


@pytest.mark.parametrize("falsy_value", ["0", "false", "False", "no", "off", ""])
def test_debug_logging_falsy_values(falsy_value: str) -> None:
    settings = load_environment_settings(env={"MECA_ENGINE_DEBUG_LOGGING": falsy_value})

    assert settings.debug_logging_enabled is False


def test_invalid_environment_value_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        load_environment_settings(env={"MECA_ENGINE_ENVIRONMENT": "not-a-real-environment"})

    assert "not-a-real-environment" in excinfo.value.message
