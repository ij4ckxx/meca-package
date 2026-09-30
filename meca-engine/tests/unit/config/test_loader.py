"""Unit tests for meca_engine.config.loader.ConfigLoader."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from meca_engine.config.loader import ConfigLoader
from meca_engine.config.schema import (
    ArticleTypeMappingConfig,
    ArticleXmlConfig,
    FeatureFlagsConfig,
    ItemTypeMappingConfig,
    JournalConfig,
    LicenseTemplatesConfig,
    ManifestXmlConfig,
    MediaTypeConfig,
    NamespaceConfig,
    PublisherAbbreviationMappingConfig,
    PublisherConfig,
    RawXmlConfig,
    ReviewsXmlConfig,
    RuntimeConfig,
    TransferXmlConfig,
)
from meca_engine.exceptions import ConfigurationError

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


@pytest.fixture
def loader(valid_config_dir: Path, schema_dir: Path) -> ConfigLoader:
    return ConfigLoader(config_dir=valid_config_dir, schema_dir=schema_dir)


def test_load_runtime_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    runtime = loader.load_runtime_config()

    assert isinstance(runtime, RuntimeConfig)
    assert runtime.concurrency.worker_count == 4
    assert runtime.concurrency.mechanism == "process_pool"
    assert runtime.retry.max_attempts == 3
    assert runtime.validation.dtd_validation_enabled is True
    assert runtime.validation.severity_block_threshold == "HIGH"
    assert runtime.staging.strategy == "full_local_staging"
    assert runtime.output.operational_bucket == "test-operational-bucket"
    assert runtime.checkpoint.backend == "postgres"
    assert runtime.doi_registry.backend == "postgres"
    assert runtime.output.provider == "LOCAL"
    assert runtime.output.local_path == "./test-generated-packages"
    assert runtime.input.provider == "LOCAL"
    assert runtime.input.local_path == "./test-input"
    assert runtime.dashboard.reports_path == "./test-reports"
    assert runtime.logging.level == "INFO"


def test_load_feature_flags_returns_typed_dataclass(loader: ConfigLoader) -> None:
    flags = loader.load_feature_flags()

    assert isinstance(flags, FeatureFlagsConfig)
    assert flags.reviews_include_duplicate_correspondence is True
    assert flags.reviews_extended_history_scope is False
    assert flags.strict_replication_mode is False


def test_load_media_type_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    media_types = loader.load_media_type_config()

    assert isinstance(media_types, MediaTypeConfig)
    assert media_types.mappings[".pdf"] == "application/pdf"
    assert media_types.unmapped_extension_policy == "warn_and_default"
    assert media_types.unmapped_extension_default == "application/octet-stream"


def test_load_article_type_mapping_returns_typed_dataclass(loader: ConfigLoader) -> None:
    mapping = loader.load_article_type_mapping()

    assert isinstance(mapping, ArticleTypeMappingConfig)
    assert mapping.mappings["Research Article"] == "Original Study"
    assert mapping.default_article_type == "Original Study"


def test_load_publisher_abbreviation_mapping_returns_typed_dataclass(loader: ConfigLoader) -> None:
    mapping = loader.load_publisher_abbreviation_mapping()

    assert isinstance(mapping, PublisherAbbreviationMappingConfig)
    assert mapping.mappings["cs"] == "CS"
    assert mapping.mappings["bcj"] == "BCJ"
    assert mapping.mappings["bst"] == "BST"
    assert mapping.mappings["bsr"] == "BSR"
    assert mapping.mappings["etls"] == "ETLS"
    assert mapping.mappings["ebc"] == "EBC"


def test_load_item_type_mapping_returns_typed_dataclass(loader: ConfigLoader) -> None:
    mapping = loader.load_item_type_mapping()

    assert isinstance(mapping, ItemTypeMappingConfig)
    assert mapping.mappings["manuscript"] == "manuscript"
    assert mapping.mappings["licencetopublishform"] == "author agreement"
    assert mapping.default_item_type == "supplemental"


def test_load_namespace_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    namespaces = loader.load_namespace_config()

    assert isinstance(namespaces, NamespaceConfig)
    assert namespaces.namespaces["xlink"] == "http://www.w3.org/1999/xlink"
    assert namespaces.namespaces["xml"] == "http://www.w3.org/XML/1998/namespace"


def test_load_raw_xml_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    config = loader.load_raw_xml_config()

    assert isinstance(config, RawXmlConfig)
    assert config.article_type == "research-article"
    assert config.dtd_version == "1.3"
    assert config.default_xml_lang == "en"
    assert config.encoding == "UTF-8"
    assert config.namespace_prefixes == ("mml", "xlink", "xsi", "ali")
    assert config.pretty_indent_spaces == 0
    assert "JATS" in config.doctype_public_id


def test_load_article_xml_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    config = loader.load_article_xml_config()

    assert isinstance(config, ArticleXmlConfig)
    assert config.dtd_version == "1.2"
    assert config.encoding == "utf-8"
    assert config.pretty_indent_spaces == 0
    assert "JATS" in config.doctype_public_id


def test_load_manifest_xml_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    config = loader.load_manifest_xml_config()

    assert isinstance(config, ManifestXmlConfig)
    assert config.manifest_version == "1"
    assert config.encoding == "UTF-8"
    assert config.pretty_indent_spaces == 2
    assert "MECA" in config.doctype_public_id
    assert "{publisher_id}" in config.item_article_description_template
    assert "{article_id}" in config.article_filename_pattern
    assert config.file_item_id_prefix == "file-"


def test_load_reviews_xml_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    config = loader.load_reviews_xml_config()

    assert isinstance(config, ReviewsXmlConfig)
    assert config.content_version == "1.0"
    assert config.encoding == "UTF-8"
    assert config.pretty_indent_spaces == 2
    assert config.blinding == "single"
    assert config.permission_to_publish == "yes"
    assert config.permission_to_transfer == "yes"
    assert "{article_id}" in config.reviews_filename_pattern
    assert "MECA" in config.doctype_public_id


def test_load_transfer_xml_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    config = loader.load_transfer_xml_config()

    assert isinstance(config, TransferXmlConfig)
    assert config.transfer_version == "1.0"
    assert config.publication_type == "journal"
    assert config.pretty_indent_spaces == 2
    assert config.authentication_code_separator == "|"
    assert config.processing_instructions == ("Validate Metadata", "Ingest Article Package")
    assert "{raw_xml_filename}" in config.processing_comments_template
    assert "{article_id}" in config.transfer_filename_pattern
    assert "MECA" in config.doctype_public_id


def test_load_license_templates_returns_typed_dataclass(loader: ConfigLoader) -> None:
    config = loader.load_license_templates()

    assert isinstance(config, LicenseTemplatesConfig)
    template = config.templates["CC-BY-4-0"]
    assert template.license_type_attr == "open-access"
    assert template.ext_link_href == "https://creativecommons.org/licenses/by/4.0/"
    assert "CC BY" in template.license_p


def test_load_journal_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    journal = loader.load_journal_config("example-journal")

    assert isinstance(journal, JournalConfig)
    assert journal.journal_id == "example-journal"
    assert journal.doi_prefix == "10.9999"
    assert journal.acronym == "EJT"
    assert journal.publisher_id == "example-publisher"


def test_load_publisher_config_returns_typed_dataclass(loader: ConfigLoader) -> None:
    publisher = loader.load_publisher_config("example-publisher")

    assert isinstance(publisher, PublisherConfig)
    assert publisher.publisher_id == "example-publisher"
    assert publisher.provider_name == "Example Publisher Limited"


def test_discover_journal_ids_finds_the_example_fixture(loader: ConfigLoader) -> None:
    assert loader.discover_journal_ids() == ("example-journal",)


def test_discover_publisher_ids_finds_the_example_fixture(loader: ConfigLoader) -> None:
    assert loader.discover_publisher_ids() == ("example-publisher",)


def test_discover_ids_returns_empty_tuple_for_missing_directory(
    schema_dir: Path, tmp_path: Path
) -> None:
    empty_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    assert empty_loader.discover_journal_ids() == ()
    assert empty_loader.discover_publisher_ids() == ()


def test_missing_file_raises_configuration_error(schema_dir: Path, tmp_path: Path) -> None:
    empty_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="not found"):
        empty_loader.load_runtime_config()


def test_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root / "tests" / "fixtures" / "config" / "invalid" / "runtime_missing_field.yaml"
    )
    (tmp_path / "runtime.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_runtime_config()


def test_article_type_mapping_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root
        / "tests"
        / "fixtures"
        / "config"
        / "invalid"
        / "article-type-mapping_missing_field.yaml"
    )
    (tmp_path / "article-type-mapping.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_article_type_mapping()


def test_item_type_mapping_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root
        / "tests"
        / "fixtures"
        / "config"
        / "invalid"
        / "item-type-mapping_missing_field.yaml"
    )
    (tmp_path / "item-type-mapping.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_item_type_mapping()


def test_namespace_config_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root / "tests" / "fixtures" / "config" / "invalid" / "namespaces_missing_field.yaml"
    )
    (tmp_path / "namespaces.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_namespace_config()


def test_raw_xml_config_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root / "tests" / "fixtures" / "config" / "invalid" / "raw-xml_missing_field.yaml"
    )
    (tmp_path / "raw-xml.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_raw_xml_config()


def test_article_xml_config_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root / "tests" / "fixtures" / "config" / "invalid" / "article-xml_missing_field.yaml"
    )
    (tmp_path / "article-xml.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_article_xml_config()


def test_manifest_xml_config_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root / "tests" / "fixtures" / "config" / "invalid" / "manifest-xml_missing_field.yaml"
    )
    (tmp_path / "manifest-xml.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_manifest_xml_config()


def test_reviews_xml_config_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root / "tests" / "fixtures" / "config" / "invalid" / "reviews-xml_missing_field.yaml"
    )
    (tmp_path / "reviews-xml.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_reviews_xml_config()


def test_transfer_xml_config_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root / "tests" / "fixtures" / "config" / "invalid" / "transfer-xml_missing_field.yaml"
    )
    (tmp_path / "transfer-xml.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_transfer_xml_config()


def test_license_templates_schema_violation_raises_configuration_error(
    schema_dir: Path, repo_root: Path, tmp_path: Path
) -> None:
    incomplete_source = (
        repo_root
        / "tests"
        / "fixtures"
        / "config"
        / "invalid"
        / "license-templates_missing_field.yaml"
    )
    (tmp_path / "license-templates.yaml").write_text(
        incomplete_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="failed schema validation"):
        invalid_loader.load_license_templates()


def test_placeholder_acronym_is_rejected(schema_dir: Path, repo_root: Path) -> None:
    invalid_dir = repo_root / "tests" / "fixtures" / "config" / "invalid"
    invalid_loader = ConfigLoader(config_dir=invalid_dir, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="unconfirmed placeholder"):
        invalid_loader.load_journal_config("placeholder-journal")


def test_non_mapping_yaml_raises_configuration_error(schema_dir: Path, tmp_path: Path) -> None:
    bad_file = tmp_path / "runtime.yaml"
    bad_file.write_text("- just\n- a\n- list\n", encoding="utf-8")
    bad_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="YAML mapping"):
        bad_loader.load_runtime_config()


def test_malformed_yaml_raises_configuration_error(schema_dir: Path, tmp_path: Path) -> None:
    bad_file = tmp_path / "runtime.yaml"
    bad_file.write_text("concurrency: [unclosed\n", encoding="utf-8")
    bad_loader = ConfigLoader(config_dir=tmp_path, schema_dir=schema_dir)

    with pytest.raises(ConfigurationError, match="not valid YAML"):
        bad_loader.load_runtime_config()


def test_missing_schema_file_raises_configuration_error(
    valid_config_dir: Path, tmp_path: Path
) -> None:
    loader_with_missing_schema = ConfigLoader(config_dir=valid_config_dir, schema_dir=tmp_path)

    with pytest.raises(ConfigurationError, match="Configuration schema not found"):
        loader_with_missing_schema.load_runtime_config()


def test_load_app_config_aggregates_everything(loader: ConfigLoader) -> None:
    from meca_engine.config.environment import load_environment_settings

    app_config = loader.load_app_config(load_environment_settings(env={}))

    assert "example-journal" in app_config.journals
    assert "example-publisher" in app_config.publishers
    assert isinstance(app_config.runtime, RuntimeConfig)
    assert isinstance(app_config.feature_flags, FeatureFlagsConfig)
