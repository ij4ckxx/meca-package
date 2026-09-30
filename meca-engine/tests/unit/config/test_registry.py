"""Unit tests for meca_engine.config.registry.ConfigRegistry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from meca_engine.config.environment import load_environment_settings
from meca_engine.config.loader import ConfigLoader
from meca_engine.config.registry import ConfigRegistry
from meca_engine.exceptions import ConfigurationError

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


@pytest.fixture
def registry(valid_config_dir: Path, schema_dir: Path) -> ConfigRegistry:
    loader = ConfigLoader(config_dir=valid_config_dir, schema_dir=schema_dir)
    return ConfigRegistry.from_loader(loader)


def test_get_journal_config_returns_the_right_journal(registry: ConfigRegistry) -> None:
    journal = registry.get_journal_config("example-journal")

    assert journal.journal_id == "example-journal"


def test_get_journal_config_raises_for_unconfigured_journal(registry: ConfigRegistry) -> None:
    with pytest.raises(ConfigurationError, match="No configuration found for journal_id"):
        registry.get_journal_config("unknown-journal")


def test_get_publisher_config_returns_the_right_publisher(registry: ConfigRegistry) -> None:
    publisher = registry.get_publisher_config("example-publisher")

    assert publisher.publisher_id == "example-publisher"


def test_get_publisher_config_raises_for_unconfigured_publisher(registry: ConfigRegistry) -> None:
    with pytest.raises(ConfigurationError, match="No configuration found for publisher_id"):
        registry.get_publisher_config("unknown-publisher")


def test_app_config_property_exposes_the_full_configuration(registry: ConfigRegistry) -> None:
    assert "example-journal" in registry.app_config.journals
    assert "example-publisher" in registry.app_config.publishers


def test_construction_directly_from_app_config(valid_config_dir: Path, schema_dir: Path) -> None:
    loader = ConfigLoader(config_dir=valid_config_dir, schema_dir=schema_dir)
    app_config = loader.load_app_config(load_environment_settings(env={}))

    registry = ConfigRegistry(app_config)

    assert registry.get_journal_config("example-journal").journal_id == "example-journal"
