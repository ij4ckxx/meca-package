"""Unit tests for meca_engine.providers.output."""

from __future__ import annotations

import pytest

from meca_engine.config.schema import OutputSettings
from meca_engine.exceptions import ProviderNotConfiguredError
from meca_engine.providers.output import (
    LocalOutputProvider,
    OutputProvider,
    SftpOutputProvider,
    create_output_provider,
)

pytestmark = pytest.mark.unit


def test_local_output_provider_creates_root_and_article_dir(tmp_path) -> None:
    root = tmp_path / "generated_packages"
    provider: OutputProvider = LocalOutputProvider(str(root))

    assert root.is_dir()

    article_dir = provider.article_output_root("cs-2025-0001")

    assert article_dir == root / "cs-2025-0001"
    assert article_dir.is_dir()


def test_sftp_output_provider_raises_provider_not_configured() -> None:
    provider = SftpOutputProvider()

    with pytest.raises(ProviderNotConfiguredError):
        provider.article_output_root("cs-2025-0001")


def test_create_output_provider_selects_local(tmp_path) -> None:
    provider = create_output_provider(
        OutputSettings(operational_bucket="x", archival_bucket="x", local_path=str(tmp_path))
    )

    assert isinstance(provider, LocalOutputProvider)


def test_create_output_provider_selects_sftp() -> None:
    provider = create_output_provider(
        OutputSettings(operational_bucket="x", archival_bucket="x", provider="SFTP")
    )

    assert isinstance(provider, SftpOutputProvider)


def test_create_output_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ProviderNotConfiguredError):
        create_output_provider(
            OutputSettings(operational_bucket="x", archival_bucket="x", provider="FTP")
        )


def test_local_output_provider_category_root_creates_sibling_of_article_roots(
    tmp_path,
) -> None:
    root = tmp_path / "generated_packages"
    provider: OutputProvider = LocalOutputProvider(str(root))

    uploaded = provider.category_root("uploaded")

    assert uploaded == root / "uploaded"
    assert uploaded.is_dir()


def test_sftp_output_provider_category_root_raises_provider_not_configured() -> None:
    provider = SftpOutputProvider()

    with pytest.raises(ProviderNotConfiguredError):
        provider.category_root("uploaded")


def test_output_settings_defaults_never_point_to_output_folder() -> None:
    """Safety regression: the default must never be the real `Output/` folder."""
    settings = OutputSettings(operational_bucket="x", archival_bucket="x")

    assert settings.local_path != "./Output"
    assert settings.local_path == "./archive_migration_validation/generated_packages"


def test_sftp_output_provider_upload_package(tmp_path, monkeypatch) -> None:
    article_dir = tmp_path / "CS20240001"
    article_dir.mkdir(parents=True)
    zip_file = article_dir / "MECA_CS20240001.zip"
    zip_file.write_text("dummy zip content")

    provider = SftpOutputProvider(
        local_path=str(tmp_path),
        host="test.sftp.com",
        user="testuser",
        remote_dir="/sftp/meca",
    )

    uploaded_files = []

    class FakeSftp:
        def stat(self, path):
            return True

        def put(self, local, remote):
            uploaded_files.append((local, remote))

        def posix_rename(self, src, dst):
            pass

    monkeypatch.setattr(provider, "_get_sftp", lambda: FakeSftp())

    remote_path = provider.upload_package("CS20240001", article_dir)

    assert remote_path == "/sftp/meca/MECA_CS20240001.zip"
    assert len(uploaded_files) == 1
    assert uploaded_files[0][1] == "/sftp/meca/.MECA_CS20240001.zip.tmp"

