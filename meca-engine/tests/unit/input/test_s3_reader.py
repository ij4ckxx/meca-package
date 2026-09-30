"""Unit tests for meca_engine.input.readers.s3_reader.S3Reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.exceptions import ConfigurationError, S3ReadTransientError, SourceUnavailableError
from meca_engine.input.models import S3BatchSource
from meca_engine.input.readers.s3_reader import Boto3S3Client, S3Reader
from mocks.fake_s3_client import FakeS3Client

pytestmark = pytest.mark.unit

BUCKET = "test-bucket"
PREFIX = "batch/"


@pytest.fixture
def fake_client() -> FakeS3Client:
    client = FakeS3Client()
    client.put_object(BUCKET, f"{PREFIX}ART-0001/ART-0001.xml", b"<article/>")
    client.put_object(BUCKET, f"{PREFIX}ART-0001/Original/manuscript.txt", b"manuscript content")
    client.put_object(BUCKET, f"{PREFIX}ART-0001/Original/fig1.txt", b"figure content")
    client.put_object(BUCKET, f"{PREFIX}ART-0001/R1/manuscript.txt", b"revised content")
    client.put_object(BUCKET, f"{PREFIX}ART-0002/ART-0002.xml", b"<article/>")
    client.put_object(BUCKET, f"{PREFIX}ART-0002/Original/manuscript.txt", b"another manuscript")
    return client


@pytest.fixture
def reader(fake_client: FakeS3Client) -> S3Reader:
    return S3Reader(client=fake_client)


@pytest.fixture
def source() -> S3BatchSource:
    return S3BatchSource(bucket=BUCKET, prefix=PREFIX)


def test_list_batch_article_ids(reader: S3Reader, source: S3BatchSource) -> None:
    ids = reader.list_batch_article_ids(source)

    assert ids == ("ART-0001", "ART-0002")


def test_list_batch_article_ids_raises_for_missing_bucket(reader: S3Reader) -> None:
    missing_source = S3BatchSource(bucket="no-such-bucket", prefix="x/")

    with pytest.raises(SourceUnavailableError):
        reader.list_batch_article_ids(missing_source)


def test_list_article_top_level_distinguishes_files_and_directories(
    reader: S3Reader, source: S3BatchSource
) -> None:
    entries = reader.list_article_top_level("ART-0001", source)

    names_and_dirs = {(e.name, e.is_directory) for e in entries}
    assert ("ART-0001.xml", False) in names_and_dirs
    assert ("Original", True) in names_and_dirs
    assert ("R1", True) in names_and_dirs


def test_list_round_files(reader: S3Reader, source: S3BatchSource) -> None:
    files = reader.list_round_files("ART-0001", "Original", source)

    by_path = {f.relative_path: f for f in files}
    assert set(by_path) == {"manuscript.txt", "fig1.txt"}
    assert by_path["manuscript.txt"].size_bytes == len(b"manuscript content")
    assert by_path["manuscript.txt"].checksum is None


def test_list_round_files_raises_for_missing_round(reader: S3Reader, source: S3BatchSource) -> None:
    with pytest.raises(SourceUnavailableError):
        reader.list_round_files("ART-0001", "R2-does-not-exist", source)


def test_fetch_file_downloads_and_computes_checksum(
    reader: S3Reader, source: S3BatchSource, tmp_path: Path
) -> None:
    destination = tmp_path / "manuscript.txt"

    checksum, size = reader.fetch_file(
        "ART-0001", "Original", "manuscript.txt", source, destination
    )

    assert destination.read_bytes() == b"manuscript content"
    assert size == len(b"manuscript content")

    import hashlib

    assert checksum == hashlib.sha256(b"manuscript content").hexdigest()


def test_fetch_file_raises_source_unavailable_for_missing_object(
    reader: S3Reader, source: S3BatchSource, tmp_path: Path
) -> None:
    destination = tmp_path / "missing.txt"

    with pytest.raises(SourceUnavailableError):
        reader.fetch_file("ART-0001", "Original", "does-not-exist.txt", source, destination)


def test_fetch_file_raises_transient_error_and_recovers_on_retry(
    reader: S3Reader, fake_client: FakeS3Client, source: S3BatchSource, tmp_path: Path
) -> None:
    key = f"{PREFIX}ART-0001/Original/manuscript.txt"
    fake_client.fail_next_read(BUCKET, key, times=1)
    destination = tmp_path / "manuscript.txt"

    with pytest.raises(S3ReadTransientError):
        reader.fetch_file("ART-0001", "Original", "manuscript.txt", source, destination)

    # A second attempt (simulating a caller's retry) succeeds.
    checksum, size = reader.fetch_file(
        "ART-0001", "Original", "manuscript.txt", source, destination
    )
    assert size == len(b"manuscript content")
    assert checksum


def test_list_round_files_raises_transient_error_on_transient_list_failure(
    reader: S3Reader, fake_client: FakeS3Client, source: S3BatchSource
) -> None:
    fake_client.fail_next_list(BUCKET, f"{PREFIX}ART-0001/Original/", times=1)

    with pytest.raises(S3ReadTransientError):
        reader.list_round_files("ART-0001", "Original", source)

    # Recovers on a subsequent attempt.
    files = reader.list_round_files("ART-0001", "Original", source)
    assert len(files) == 2


def test_list_batch_article_ids_raises_transient_error_on_transient_list_failure(
    reader: S3Reader, fake_client: FakeS3Client, source: S3BatchSource
) -> None:
    fake_client.fail_next_list(BUCKET, PREFIX, times=1)

    with pytest.raises(S3ReadTransientError):
        reader.list_batch_article_ids(source)

    assert reader.list_batch_article_ids(source) == ("ART-0001", "ART-0002")


def test_list_article_top_level_raises_transient_error_on_transient_list_failure(
    reader: S3Reader, fake_client: FakeS3Client, source: S3BatchSource
) -> None:
    fake_client.fail_next_list(BUCKET, f"{PREFIX}ART-0001/", times=1)

    with pytest.raises(S3ReadTransientError):
        reader.list_article_top_level("ART-0001", source)


def test_wrong_source_type_raises_type_error(reader: S3Reader) -> None:
    from meca_engine.input.models import LocalBatchSource

    wrong_source = LocalBatchSource(root_path=Path("/tmp"))

    with pytest.raises(TypeError):
        reader.list_batch_article_ids(wrong_source)  # type: ignore[arg-type]


def test_boto3_s3_client_raises_configuration_error_when_boto3_not_installed() -> None:
    # This test environment deliberately does not install boto3 (an
    # optional "aws" dependency group, per the current task's allowance
    # that "concrete AWS integration may be mocked"), so this exercises
    # the real, intended failure path rather than a simulated one.
    with pytest.raises(ConfigurationError, match="boto3"):
        Boto3S3Client()
