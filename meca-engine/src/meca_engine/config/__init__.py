"""Configuration Manager package (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §5).

Foundation-layer package (10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.3) — depends
on nothing else in :mod:`meca_engine` except :mod:`meca_engine.exceptions`
and :mod:`meca_engine.constants`.
"""

from __future__ import annotations

from meca_engine.config.environment import load_environment_settings
from meca_engine.config.loader import ConfigLoader
from meca_engine.config.registry import ConfigRegistry
from meca_engine.config.schema import (
    AppConfig,
    CheckpointSettings,
    ConcurrencySettings,
    DoiRegistrySettings,
    EnvironmentSettings,
    FeatureFlagsConfig,
    JournalConfig,
    LicenseTemplate,
    MediaTypeConfig,
    OutputSettings,
    PublisherConfig,
    RetrySettings,
    RuntimeConfig,
    StagingSettings,
    ValidationSettings,
)

__all__ = [
    "AppConfig",
    "CheckpointSettings",
    "ConcurrencySettings",
    "ConfigLoader",
    "ConfigRegistry",
    "DoiRegistrySettings",
    "EnvironmentSettings",
    "FeatureFlagsConfig",
    "JournalConfig",
    "LicenseTemplate",
    "MediaTypeConfig",
    "OutputSettings",
    "PublisherConfig",
    "RetrySettings",
    "RuntimeConfig",
    "StagingSettings",
    "ValidationSettings",
    "load_environment_settings",
]
