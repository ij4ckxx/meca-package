"""Configuration loading and schema validation.

Reads the YAML configuration tree described in
12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §5, validates every file against its
corresponding JSON Schema in ``schemas/config-schema/`` before constructing
any typed dataclass, and never returns partially-validated configuration —
per §5.9, a config file that fails schema validation is a batch-level
startup failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import jsonschema
import yaml

from meca_engine.config.schema import (
    AppConfig,
    ArticleTypeMappingConfig,
    ArticleXmlConfig,
    CheckpointSettings,
    ConcurrencySettings,
    DashboardSettings,
    DoiRegistrySettings,
    EnvironmentSettings,
    FeatureFlagsConfig,
    InputSettings,
    ItemTypeMappingConfig,
    JournalConfig,
    LicenseTemplate,
    LicenseTemplatesConfig,
    LoggingSettings,
    ManifestXmlConfig,
    MediaTypeConfig,
    NamespaceConfig,
    OutputSettings,
    PackagingSettings,
    PublisherAbbreviationMappingConfig,
    PublisherConfig,
    RawXmlConfig,
    RetrySettings,
    ReviewsXmlConfig,
    RuntimeConfig,
    StagingSettings,
    TransferXmlConfig,
    ValidationSettings,
)
from meca_engine.exceptions import ConfigurationError

_STAGE: Final[str] = "meca_engine.config.loader"

# ADR-007 placeholder sentinel convention — see 11_LLD_02.../schema.py docstring
# and 16_LLD_07_READINESS_ASSESSMENT.md §15.3. A journal config file carrying
# this literal value has not yet had its acronym confirmed by the business
# and must never be loaded successfully.
_UNCONFIRMED_PLACEHOLDER_PREFIX: Final[str] = "<CONFIRM-VIA-"


class ConfigLoader:
    """Loads and validates every configuration file in the ``config/`` tree.

    Attributes:
        config_dir: Root directory containing the versioned YAML
            configuration tree (``journals/``, ``publishers/``,
            ``runtime.yaml``, ``feature-flags.yaml``, etc.).
        schema_dir: Root directory containing the JSON Schema files each
            config file is validated against.
    """

    def __init__(self, config_dir: Path, schema_dir: Path) -> None:
        """Initialize the loader.

        Args:
            config_dir: Root directory containing the ``config/`` YAML tree.
            schema_dir: Root directory containing ``schemas/config-schema/``.
        """
        self.config_dir = config_dir
        self.schema_dir = schema_dir

    def load_runtime_config(self) -> RuntimeConfig:
        """Load and validate ``config/runtime.yaml``.

        Returns:
            The typed, immutable :class:`RuntimeConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("runtime.yaml", "runtime.schema.json")
        return RuntimeConfig(
            concurrency=ConcurrencySettings(**data["concurrency"]),
            retry=RetrySettings(**data["retry"]),
            validation=ValidationSettings(**data["validation"]),
            staging=StagingSettings(**data["staging"]),
            output=OutputSettings(**data["output"]),
            checkpoint=CheckpointSettings(**data["checkpoint"]),
            doi_registry=DoiRegistrySettings(**data["doi_registry"]),
            packaging=PackagingSettings(**data["packaging"]),
            input=InputSettings(**data["input"]),
            dashboard=DashboardSettings(**data["dashboard"]),
            logging=LoggingSettings(**data["logging"]),
        )

    def load_feature_flags(self) -> FeatureFlagsConfig:
        """Load and validate ``config/feature-flags.yaml``.

        Returns:
            The typed, immutable :class:`FeatureFlagsConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("feature-flags.yaml", "feature-flags.schema.json")
        return FeatureFlagsConfig(**data)

    def load_media_type_config(self) -> MediaTypeConfig:
        """Load and validate ``config/media-types.yaml``.

        Returns:
            The typed, immutable :class:`MediaTypeConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("media-types.yaml", "media-types.schema.json")
        return MediaTypeConfig(
            mappings=data["mappings"],
            unmapped_extension_policy=data["unmapped_extension_policy"],
            unmapped_extension_default=data["unmapped_extension_default"],
        )

    def load_article_type_mapping(self) -> ArticleTypeMappingConfig:
        """Load and validate ``config/article-type-mapping.yaml``.

        Returns:
            The typed, immutable :class:`ArticleTypeMappingConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate(
            "article-type-mapping.yaml", "article-type-mapping.schema.json"
        )
        return ArticleTypeMappingConfig(
            mappings=data["mappings"],
            default_article_type=data["default_article_type"],
        )

    def load_publisher_abbreviation_mapping(self) -> PublisherAbbreviationMappingConfig:
        """Load and validate ``config/publisher-abbreviation-mapping.yaml``.

        Returns:
            The typed, immutable :class:`PublisherAbbreviationMappingConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate(
            "publisher-abbreviation-mapping.yaml", "publisher-abbreviation-mapping.schema.json"
        )
        return PublisherAbbreviationMappingConfig(mappings=data["mappings"])

    def load_item_type_mapping(self) -> ItemTypeMappingConfig:
        """Load and validate ``config/item-type-mapping.yaml``.

        Returns:
            The typed, immutable :class:`ItemTypeMappingConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("item-type-mapping.yaml", "item-type-mapping.schema.json")
        return ItemTypeMappingConfig(
            mappings=data["mappings"],
            default_item_type=data["default_item_type"],
        )

    def load_namespace_config(self) -> NamespaceConfig:
        """Load and validate ``config/namespaces.yaml``.

        Returns:
            The typed, immutable :class:`NamespaceConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("namespaces.yaml", "namespaces.schema.json")
        return NamespaceConfig(namespaces=data["namespaces"])

    def load_raw_xml_config(self) -> RawXmlConfig:
        """Load and validate ``config/raw-xml.yaml``.

        Returns:
            The typed, immutable :class:`RawXmlConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("raw-xml.yaml", "raw-xml.schema.json")
        return RawXmlConfig(
            doctype_public_id=data["doctype_public_id"],
            doctype_system_id=data["doctype_system_id"],
            article_type=data["article_type"],
            dtd_version=data["dtd_version"],
            default_xml_lang=data["default_xml_lang"],
            encoding=data["encoding"],
            namespace_prefixes=tuple(data["namespace_prefixes"]),
            pretty_indent_spaces=data["pretty_indent_spaces"],
        )

    def load_article_xml_config(self) -> ArticleXmlConfig:
        """Load and validate ``config/article-xml.yaml``.

        Returns:
            The typed, immutable :class:`ArticleXmlConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("article-xml.yaml", "article-xml.schema.json")
        return ArticleXmlConfig(
            doctype_public_id=data["doctype_public_id"],
            doctype_system_id=data["doctype_system_id"],
            dtd_version=data["dtd_version"],
            encoding=data["encoding"],
            pretty_indent_spaces=data["pretty_indent_spaces"],
        )

    def load_manifest_xml_config(self) -> ManifestXmlConfig:
        """Load and validate ``config/manifest-xml.yaml``.

        Returns:
            The typed, immutable :class:`ManifestXmlConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("manifest-xml.yaml", "manifest-xml.schema.json")
        return ManifestXmlConfig(
            doctype_public_id=data["doctype_public_id"],
            doctype_system_id=data["doctype_system_id"],
            encoding=data["encoding"],
            manifest_version=data["manifest_version"],
            pretty_indent_spaces=data["pretty_indent_spaces"],
            item_article_description_template=data["item_article_description_template"],
            item_reviews_description=data["item_reviews_description"],
            item_transfer_description=data["item_transfer_description"],
            article_filename_pattern=data["article_filename_pattern"],
            reviews_filename_pattern=data["reviews_filename_pattern"],
            transfer_filename_pattern=data["transfer_filename_pattern"],
            file_item_id_prefix=data["file_item_id_prefix"],
            file_item_description_template=data["file_item_description_template"],
        )

    def load_reviews_xml_config(self) -> ReviewsXmlConfig:
        """Load and validate ``config/reviews-xml.yaml``.

        Returns:
            The typed, immutable :class:`ReviewsXmlConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("reviews-xml.yaml", "reviews-xml.schema.json")
        return ReviewsXmlConfig(
            doctype_public_id=data["doctype_public_id"],
            doctype_system_id=data["doctype_system_id"],
            encoding=data["encoding"],
            content_version=data["content_version"],
            pretty_indent_spaces=data["pretty_indent_spaces"],
            blinding=data["blinding"],
            permission_to_publish=data["permission_to_publish"],
            permission_to_transfer=data["permission_to_transfer"],
            review_item_data_type=data["review_item_data_type"],
            reviews_filename_pattern=data["reviews_filename_pattern"],
            scorecard_review_item_title=data["scorecard_review_item_title"],
            decline_review_item_title=data["decline_review_item_title"],
            decision_review_item_title=data["decision_review_item_title"],
            duplicate_correspondence_review_item_title=data[
                "duplicate_correspondence_review_item_title"
            ],
            extended_history_review_item_title=data["extended_history_review_item_title"],
        )

    def load_transfer_xml_config(self) -> TransferXmlConfig:
        """Load and validate ``config/transfer-xml.yaml``.

        Returns:
            The typed, immutable :class:`TransferXmlConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("transfer-xml.yaml", "transfer-xml.schema.json")
        return TransferXmlConfig(
            doctype_public_id=data["doctype_public_id"],
            doctype_system_id=data["doctype_system_id"],
            transfer_version=data["transfer_version"],
            publication_type=data["publication_type"],
            pretty_indent_spaces=data["pretty_indent_spaces"],
            authentication_code_separator=data["authentication_code_separator"],
            processing_instructions=tuple(data["processing_instructions"]),
            processing_comments_template=data["processing_comments_template"],
            raw_xml_filename_pattern=data["raw_xml_filename_pattern"],
            transfer_filename_pattern=data["transfer_filename_pattern"],
            source_section_comment=data["source_section_comment"],
            destination_section_comment=data["destination_section_comment"],
            instructions_section_comment=data["instructions_section_comment"],
        )

    def load_license_templates(self) -> LicenseTemplatesConfig:
        """Load and validate ``config/license-templates.yaml``.

        Returns:
            The typed, immutable :class:`LicenseTemplatesConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                or fails schema validation.
        """
        data = self._read_and_validate("license-templates.yaml", "license-templates.schema.json")
        return LicenseTemplatesConfig(
            templates={key: LicenseTemplate(**value) for key, value in data.items()}
        )

    def load_journal_config(self, journal_id: str) -> JournalConfig:
        """Load and validate one journal's configuration.

        Args:
            journal_id: The journal identifier, matching the YAML file's
                basename under ``config/journals/`` (e.g. ``"clinical-science"``
                for ``config/journals/clinical-science.yaml``).

        Returns:
            The typed, immutable :class:`JournalConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                fails schema validation, or carries an unconfirmed
                placeholder value in a required business field (e.g. an
                acronym pending ADR-007).
        """
        relative_path = Path("journals") / f"{journal_id}.yaml"
        data = self._read_and_validate(relative_path, "journal.schema.json")
        self._reject_placeholder_values(data, context=f"journal '{journal_id}'")
        return JournalConfig(**data)

    def load_publisher_config(self, publisher_id: str) -> PublisherConfig:
        """Load and validate one publisher's configuration.

        Args:
            publisher_id: The publisher identifier, matching the YAML file's
                basename under ``config/publishers/``.

        Returns:
            The typed, immutable :class:`PublisherConfig`.

        Raises:
            ConfigurationError: If the file is missing, is not valid YAML,
                fails schema validation, or carries an unconfirmed
                placeholder value in a required business field.
        """
        relative_path = Path("publishers") / f"{publisher_id}.yaml"
        data = self._read_and_validate(relative_path, "publisher.schema.json")
        self._reject_placeholder_values(data, context=f"publisher '{publisher_id}'")
        return PublisherConfig(**data)

    def discover_journal_ids(self) -> tuple[str, ...]:
        """Enumerate every journal id configured under ``config/journals/``.

        Returns:
            A sorted tuple of journal ids (YAML file basenames), excluding
            any file whose name starts with ``_`` (a documented convention
            for template/example files that are not real journal configs).
        """
        return self._discover_ids("journals")

    def discover_publisher_ids(self) -> tuple[str, ...]:
        """Enumerate every publisher id configured under ``config/publishers/``.

        Returns:
            A sorted tuple of publisher ids (YAML file basenames), excluding
            any file whose name starts with ``_``.
        """
        return self._discover_ids("publishers")

    def load_app_config(self, environment_settings: EnvironmentSettings) -> AppConfig:
        """Load the complete application configuration for one run.

        Args:
            environment_settings: Already-resolved environment settings
                (see :func:`meca_engine.config.environment.load_environment_settings`).

        Returns:
            The fully-populated, immutable :class:`AppConfig`.

        Raises:
            ConfigurationError: If any constituent file is missing, invalid,
                or fails schema validation.
        """
        journals = {
            journal_id: self.load_journal_config(journal_id)
            for journal_id in self.discover_journal_ids()
        }
        publishers = {
            publisher_id: self.load_publisher_config(publisher_id)
            for publisher_id in self.discover_publisher_ids()
        }
        return AppConfig(
            environment_settings=environment_settings,
            runtime=self.load_runtime_config(),
            feature_flags=self.load_feature_flags(),
            journals=journals,
            publishers=publishers,
        )

    # --- internal helpers ---

    def _discover_ids(self, subdirectory: str) -> tuple[str, ...]:
        directory = self.config_dir / subdirectory
        if not directory.is_dir():
            return ()
        return tuple(
            sorted(path.stem for path in directory.glob("*.yaml") if not path.stem.startswith("_"))
        )

    def _read_and_validate(self, relative_path: Path | str, schema_filename: str) -> dict[str, Any]:
        full_path = self.config_dir / relative_path
        data = self._read_yaml(full_path)
        self._validate_against_schema(data, full_path, schema_filename)
        return data

    def _read_yaml(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise ConfigurationError(
                f"Required configuration file not found: {path}",
                stage=_STAGE,
            )
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ConfigurationError(
                f"Configuration file is not valid YAML: {path}",
                stage=_STAGE,
                inner_cause=exc,
            ) from exc
        if not isinstance(loaded, dict):
            raise ConfigurationError(
                f"Configuration file must contain a YAML mapping at the top level: {path}",
                stage=_STAGE,
            )
        return loaded

    def _validate_against_schema(
        self, data: dict[str, Any], source_path: Path, schema_filename: str
    ) -> None:
        schema_path = self.schema_dir / schema_filename
        if not schema_path.is_file():
            raise ConfigurationError(
                f"Configuration schema not found: {schema_path}",
                stage=_STAGE,
            )
        with schema_path.open("r", encoding="utf-8") as handle:
            schema = json.load(handle)
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as exc:
            raise ConfigurationError(
                f"Configuration file failed schema validation: {source_path} "
                f"(schema: {schema_filename}): {exc.message}",
                stage=_STAGE,
                inner_cause=exc,
            ) from exc

    def _reject_placeholder_values(self, data: dict[str, Any], *, context: str) -> None:
        for field_name, value in data.items():
            if isinstance(value, str) and value.startswith(_UNCONFIRMED_PLACEHOLDER_PREFIX):
                raise ConfigurationError(
                    f"Configuration for {context} carries an unconfirmed placeholder "
                    f"value in field '{field_name}': {value!r}. This value requires "
                    f"business confirmation (see 02_ARCHITECTURE_DECISION_RECORDS.md) "
                    f"before this configuration may be used.",
                    stage=_STAGE,
                )
