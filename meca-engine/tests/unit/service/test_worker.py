"""Unit tests for meca_engine.service.worker.Worker.

Scoped to the Worker's own new logic — retry-wrapping and PackageOutcome
interpretation — using a real sample article for staging/extraction/
transformation (already covered elsewhere) and a fake PackageBatchRunner to
control the outcome without needing a real PackageBuilder/zip file. The
full happy path (a real generated package) is covered by this phase's
end-to-end verification runs, not a unit test, per the "keep verification
lightweight, reuse existing tests" scope.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest

from meca_engine.config.schema import (
    FeatureFlagsConfig,
    MediaTypeConfig,
    PublisherConfig,
    RetrySettings,
)
from meca_engine.exceptions.article_errors import (
    DoiRegistryUnavailableError,
    FileReferenceMissingError,
    GeneratorInvariantError,
    InvalidArticlePackageError,
    PackageAssemblyError,
    SourceUnavailableError,
)
from meca_engine.packaging.batch_runner import PackageOutcome, PackageOutcomeStatus
from meca_engine.packaging.models import PackageStatus
from meca_engine.providers.input import StagedArticle
from meca_engine.service.job import Job, JobStatus
from meca_engine.service.router import OutputRouter
from meca_engine.service.worker import Worker, _classify_failure, _journal_config_for_prefix
from tests.golden.conftest import extract_sample

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from meca_engine.generators.context import GeneratorContext

pytestmark = pytest.mark.unit

_MEDIA_TYPE_CONFIG = MediaTypeConfig(
    mappings={".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    unmapped_extension_policy="warn_and_default",
    unmapped_extension_default="application/octet-stream",
)
_FEATURE_FLAGS = FeatureFlagsConfig(
    reviews_include_duplicate_correspondence=True,
    reviews_extended_history_scope=False,
    strict_replication_mode=False,
    allow_filename_fallback=True,
)
_PUBLISHER_CONFIG = PublisherConfig(
    publisher_id="portland-press",
    provider_name="Portland Press Limited",
    destination_provider_name="Silverchair",
    default_contact_policy="corresponding_author_email",
)
_FAST_RETRY = RetrySettings(
    max_attempts=3, backoff_base_seconds=0.0, backoff_multiplier=1.0, backoff_max_seconds=0.0
)


class _FakeInputProvider:
    def __init__(self, staged: StagedArticle, *, fail_times: int = 0, exc: Exception | None = None):
        self._staged = staged
        self._fail_times = fail_times
        self._exc = exc
        self.calls = 0

    def list_articles(self) -> tuple[str, ...]:
        return (self._staged.article_id,)

    def stage_article(self, article_id: str) -> StagedArticle:
        self.calls += 1
        if self.calls <= self._fail_times:
            assert self._exc is not None
            raise self._exc
        return self._staged


class _FakeOutputProvider:
    def __init__(self, root: Path) -> None:
        self._root = root

    def article_output_root(self, article_id: str) -> Path:
        path = self._root / article_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def category_root(self, category: str) -> Path:
        path = self._root / category
        path.mkdir(parents=True, exist_ok=True)
        return path


class _FakePackageBatchRunner:
    def __init__(self, outcome: PackageOutcome) -> None:
        self._outcome = outcome

    def run(
        self, contexts: Sequence[GeneratorContext], *, output_root: Path
    ) -> tuple[PackageOutcome, ...]:
        return (self._outcome,)


def _build_worker(input_provider: object, output_provider: object, batch_runner: object) -> Worker:
    return Worker(
        input_provider=input_provider,  # type: ignore[arg-type]
        output_provider=output_provider,  # type: ignore[arg-type]
        output_router=OutputRouter(output_provider),  # type: ignore[arg-type]
        package_batch_runner=batch_runner,  # type: ignore[arg-type]
        runtime_config=None,  # type: ignore[arg-type]
        media_type_config=_MEDIA_TYPE_CONFIG,
        feature_flags=_FEATURE_FLAGS,
        publisher_config=_PUBLISHER_CONFIG,
        retry_settings=_FAST_RETRY,
    )


@pytest.fixture
def staged_article(tmp_path: Path) -> StagedArticle:
    sample = extract_sample(
        "cs-2025-0001", "CS-2025-6808.zip", "CS-2025-6808/cs-2025-6808.xml", tmp_path
    )
    return StagedArticle(
        article_id="cs-2025-0001",
        staged_root=sample.staged_root,
        source_xml_path=sample.xml_path,
    )


def test_journal_config_lookup_is_case_insensitive() -> None:
    """Regression: uppercase article-id prefixes (BCJ-, BST-, ...) must not KeyError."""
    assert _journal_config_for_prefix("BCJ") == _journal_config_for_prefix("bcj")
    assert _journal_config_for_prefix("BST")["acronym"] == "BST"
    assert _journal_config_for_prefix("CS")["acronym"] == "CLINSCI"


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (GeneratorInvariantError("bad state", stage="test"), PackageStatus.ENGINE_FAILURE),
        (
            PackageAssemblyError("collision", retryable=False, stage="test"),
            PackageStatus.ENGINE_FAILURE,
        ),
        (FileReferenceMissingError("missing file", stage="test"), PackageStatus.FATAL_FAILURE),
        (SourceUnavailableError("corrupt zip", stage="test"), PackageStatus.FATAL_FAILURE),
        (InvalidArticlePackageError("no source xml", stage="test"), PackageStatus.FATAL_FAILURE),
        (
            DoiRegistryUnavailableError("registry down", stage="test"),
            PackageStatus.ENGINE_FAILURE,
        ),
    ],
)
def test_classify_failure_distinguishes_source_data_from_engine_defects(
    exc: Exception, expected_status: PackageStatus
) -> None:
    """Regression: source-data problems (corrupt/empty archive, missing file) must not
    be reported as engine failures — only genuine engine defects should be."""
    assert _classify_failure(exc) is expected_status


def test_removes_extraction_root_even_when_skipped(
    staged_article: StagedArticle, tmp_path: Path
) -> None:
    """Regression: a leaked extraction directory is a disk-space risk across a large batch."""
    extraction_root = tmp_path / "am_cs-2025-0001_extraction"
    extraction_root.mkdir()
    staged_with_root = dataclasses.replace(staged_article, extraction_root=extraction_root)
    input_provider = _FakeInputProvider(staged_with_root)
    batch_runner = _FakePackageBatchRunner(
        PackageOutcome(article_id="cs-2025-0001", status=PackageOutcomeStatus.SKIPPED)
    )
    worker = _build_worker(input_provider, _FakeOutputProvider(tmp_path / "out"), batch_runner)
    job = Job(article_id="cs-2025-0001")

    worker.process(job)

    assert not extraction_root.exists()


def test_removes_extraction_root_even_on_failure(
    staged_article: StagedArticle, tmp_path: Path
) -> None:
    extraction_root = tmp_path / "am_cs-2025-0001_extraction"
    extraction_root.mkdir()
    staged_with_root = dataclasses.replace(staged_article, extraction_root=extraction_root)
    input_provider = _FakeInputProvider(staged_with_root)
    failure = PackageAssemblyError("collision", retryable=False, stage="test")
    batch_runner = _FakePackageBatchRunner(
        PackageOutcome(
            article_id="cs-2025-0001",
            status=PackageOutcomeStatus.FAILED,
            error_message=str(failure),
            exception=failure,
        )
    )
    worker = _build_worker(input_provider, _FakeOutputProvider(tmp_path / "out"), batch_runner)
    job = Job(article_id="cs-2025-0001")

    worker.process(job)

    assert not extraction_root.exists()


def test_retries_transient_staging_failure_then_succeeds_to_skip(
    staged_article: StagedArticle, tmp_path: Path
) -> None:
    input_provider = _FakeInputProvider(
        staged_article, fail_times=1, exc=DoiRegistryUnavailableError("unreachable", stage="test")
    )
    batch_runner = _FakePackageBatchRunner(
        PackageOutcome(article_id="cs-2025-0001", status=PackageOutcomeStatus.SKIPPED)
    )
    worker = _build_worker(input_provider, _FakeOutputProvider(tmp_path / "out"), batch_runner)
    job = Job(article_id="cs-2025-0001")

    report = worker.process(job)

    assert report is None
    assert job.status is JobStatus.SKIPPED
    assert job.retry_count == 1
    assert input_provider.calls == 2


def test_never_retries_deterministic_staging_failure(
    staged_article: StagedArticle, tmp_path: Path
) -> None:
    input_provider = _FakeInputProvider(
        staged_article, fail_times=99, exc=FileReferenceMissingError("missing", stage="test")
    )
    batch_runner = _FakePackageBatchRunner(
        PackageOutcome(article_id="cs-2025-0001", status=PackageOutcomeStatus.SKIPPED)
    )
    worker = _build_worker(input_provider, _FakeOutputProvider(tmp_path / "out"), batch_runner)
    job = Job(article_id="cs-2025-0001")

    report = worker.process(job)

    assert report is not None
    assert job.status is JobStatus.FAILED
    assert job.retry_count == 0
    assert input_provider.calls == 1


def test_reraises_batch_runner_failure_for_classification(
    staged_article: StagedArticle, tmp_path: Path
) -> None:
    input_provider = _FakeInputProvider(staged_article)
    failure = PackageAssemblyError("collision", retryable=False, stage="test")
    batch_runner = _FakePackageBatchRunner(
        PackageOutcome(
            article_id="cs-2025-0001",
            status=PackageOutcomeStatus.FAILED,
            error_message=str(failure),
            exception=failure,
        )
    )
    worker = _build_worker(input_provider, _FakeOutputProvider(tmp_path / "out"), batch_runner)
    job = Job(article_id="cs-2025-0001")

    report = worker.process(job)

    assert report is not None
    assert report.status is PackageStatus.ENGINE_FAILURE
    assert job.status is JobStatus.FAILED
    assert "failed" in job.output_location
    assert (tmp_path / "out" / "failed" / "cs-2025-0001" / "conversion-report.json").is_file()
