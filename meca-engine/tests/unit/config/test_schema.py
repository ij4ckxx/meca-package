"""Unit tests for meca_engine.config.schema — dataclass immutability."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from meca_engine.config.schema import EnvironmentSettings, JournalConfig
from meca_engine.constants import Environment

pytestmark = pytest.mark.unit


def test_journal_config_is_frozen() -> None:
    journal = JournalConfig(
        journal_id="example-journal",
        display_name="Example Journal",
        doi_prefix="10.9999",
        acronym="EJ",
        article_type_mapping_ref="article-type-mapping.yaml#example",
        license_templates_ref="license-templates.yaml",
        doi_registry_scope="per-journal",
        publisher_id="example-publisher",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        journal.acronym = "CHANGED"  # type: ignore[misc]


def test_environment_settings_is_frozen() -> None:
    settings = EnvironmentSettings(
        environment=Environment.DEV,
        config_dir=Path("config"),
        debug_logging_enabled=False,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.debug_logging_enabled = True  # type: ignore[misc]
