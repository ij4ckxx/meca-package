"""In-memory configuration cache, keyed by journal-id / publisher-id.

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4 (Configuration Manager
responsibility) and ADR-028 (multi-tenancy): configuration is loaded once
per run and served read-only to every other module thereafter, without
re-parsing YAML per article.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from meca_engine.exceptions import ConfigurationError

if TYPE_CHECKING:
    from meca_engine.config.loader import ConfigLoader
    from meca_engine.config.schema import AppConfig, JournalConfig, PublisherConfig

_STAGE: Final[str] = "meca_engine.config.registry"


class ConfigRegistry:
    """Read-only, run-scoped access to the fully-loaded application configuration.

    Constructed once per run from an already-loaded :class:`AppConfig`
    (see :meth:`from_loader` for the common construction path), and handed
    to every other module that needs configuration
    (10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.3's dependency diagram).
    """

    def __init__(self, app_config: AppConfig) -> None:
        """Initialize the registry from an already-loaded application configuration.

        Args:
            app_config: The fully-populated configuration for this run.
        """
        self._app_config = app_config

    @classmethod
    def from_loader(
        cls, loader: ConfigLoader, journal_id_hint: str | None = None
    ) -> ConfigRegistry:
        """Build a registry by loading configuration via the given loader.

        Args:
            loader: The :class:`~meca_engine.config.loader.ConfigLoader` to
                load configuration with.
            journal_id_hint: Unused placeholder for a future per-journal-scoped
                load path; Milestone 1 always loads the complete configuration
                tree (all journals/publishers discoverable under ``config/``).

        Returns:
            A populated :class:`ConfigRegistry`.
        """
        del journal_id_hint  # reserved for future use; not needed in Milestone 1
        from meca_engine.config.environment import load_environment_settings

        environment_settings = load_environment_settings()
        app_config = loader.load_app_config(environment_settings)
        return cls(app_config)

    @property
    def app_config(self) -> AppConfig:
        """Return the complete, immutable application configuration."""
        return self._app_config

    def get_journal_config(self, journal_id: str) -> JournalConfig:
        """Return the configuration for one journal.

        Args:
            journal_id: The journal identifier to look up.

        Returns:
            The journal's :class:`JournalConfig`.

        Raises:
            ConfigurationError: If no configuration exists for ``journal_id``
                (Test Specification TC-185 — "missing configuration for an
                encountered journal-id"). This is a batch-level failure per
                12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.3: an unconfigured
                journal cannot be safely defaulted.
        """
        try:
            return self._app_config.journals[journal_id]
        except KeyError as exc:
            raise ConfigurationError(
                f"No configuration found for journal_id={journal_id!r}. "
                f"Configured journals: {sorted(self._app_config.journals)!r}.",
                stage=_STAGE,
                inner_cause=exc,
            ) from exc

    def get_publisher_config(self, publisher_id: str) -> PublisherConfig:
        """Return the configuration for one publisher.

        Args:
            publisher_id: The publisher identifier to look up.

        Returns:
            The publisher's :class:`PublisherConfig`.

        Raises:
            ConfigurationError: If no configuration exists for ``publisher_id``.
        """
        try:
            return self._app_config.publishers[publisher_id]
        except KeyError as exc:
            raise ConfigurationError(
                f"No configuration found for publisher_id={publisher_id!r}. "
                f"Configured publishers: {sorted(self._app_config.publishers)!r}.",
                stage=_STAGE,
                inner_cause=exc,
            ) from exc
