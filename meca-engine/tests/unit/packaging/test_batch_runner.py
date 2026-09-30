"""Unit tests for meca_engine.packaging.batch_runner.PackageBatchRunner."""

from __future__ import annotations

import threading
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from meca_engine.checkpoint.backends.in_memory import InMemoryCheckpointStore
from meca_engine.checkpoint.models import ArticleStage
from meca_engine.exceptions.article_errors import PackageAssemblyError
from meca_engine.logging_ import get_logger
from meca_engine.packaging.batch_runner import PackageBatchRunner, PackageOutcomeStatus
from meca_engine.packaging.models import StagedPackage

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.generators.context import GeneratorContext

pytestmark = pytest.mark.unit


class _ClaimAlwaysLosesCheckpointStore(InMemoryCheckpointStore):
    """Deterministically simulates a lost claim race (a genuine, real
    concurrent worker having already claimed the article between this
    runner's read and its own claim attempt), without depending on real
    thread-scheduling timing.
    """

    def transition(
        self,
        article_id: str,
        *,
        expected_current: ArticleStage | None,
        new_stage: ArticleStage,
        failure_reason: str | None = None,
    ) -> bool:
        if new_stage is ArticleStage.GENERATED:
            return False
        return super().transition(
            article_id,
            expected_current=expected_current,
            new_stage=new_stage,
            failure_reason=failure_reason,
        )


class _FakePackageBuilder:
    def __init__(self) -> None:
        self.build_calls: list[str] = []
        self.fail_article_ids: set[str] = set()

    def build(self, context: GeneratorContext, *, output_root: Path) -> StagedPackage:
        article_id = context.model.identity.article_id
        self.build_calls.append(article_id)
        if article_id in self.fail_article_ids:
            raise PackageAssemblyError(f"synthetic failure for {article_id}", retryable=False)
        return StagedPackage(
            article_id=article_id,
            zip_path=output_root / f"MECA_{article_id}.zip",
            doi=f"10.1042/{article_id.lower()}",
            packaged_files=(),
            xml_filenames=(),
        )


@pytest.fixture
def checkpoint_store() -> InMemoryCheckpointStore:
    return InMemoryCheckpointStore()


def _context(article_id: str, generator_context: GeneratorContext) -> GeneratorContext:
    return replace(
        generator_context,
        model=replace(
            generator_context.model,
            identity=replace(generator_context.model.identity, article_id=article_id),
        ),
    )


def test_run_processes_every_context_and_reports_success(
    checkpoint_store: InMemoryCheckpointStore, generator_context: GeneratorContext, tmp_path: Path
) -> None:
    builder = _FakePackageBuilder()
    runner = PackageBatchRunner(
        package_builder=builder,  # type: ignore[arg-type]
        checkpoint_store=checkpoint_store,
        logger=get_logger("test.batch"),
    )
    contexts = [_context("ART-1", generator_context), _context("ART-2", generator_context)]

    outcomes = runner.run(contexts, output_root=tmp_path)

    assert [o.status for o in outcomes] == [PackageOutcomeStatus.SUCCEEDED] * 2
    assert builder.build_calls == ["ART-1", "ART-2"]
    assert checkpoint_store.get_record("ART-1").stage is ArticleStage.PACKAGED  # type: ignore[union-attr]


def test_run_skips_an_article_already_packaged(
    checkpoint_store: InMemoryCheckpointStore, generator_context: GeneratorContext, tmp_path: Path
) -> None:
    checkpoint_store.transition("ART-1", expected_current=None, new_stage=ArticleStage.PACKAGED)
    builder = _FakePackageBuilder()
    runner = PackageBatchRunner(
        package_builder=builder,  # type: ignore[arg-type]
        checkpoint_store=checkpoint_store,
        logger=get_logger("test.batch"),
    )

    outcomes = runner.run([_context("ART-1", generator_context)], output_root=tmp_path)

    assert outcomes[0].status is PackageOutcomeStatus.SKIPPED
    assert builder.build_calls == []


def test_run_redoes_an_article_that_previously_failed(
    checkpoint_store: InMemoryCheckpointStore, generator_context: GeneratorContext, tmp_path: Path
) -> None:
    checkpoint_store.transition("ART-1", expected_current=None, new_stage=ArticleStage.GENERATED)
    checkpoint_store.transition(
        "ART-1",
        expected_current=ArticleStage.GENERATED,
        new_stage=ArticleStage.FAILED,
        failure_reason="prior crash",
    )
    builder = _FakePackageBuilder()
    runner = PackageBatchRunner(
        package_builder=builder,  # type: ignore[arg-type]
        checkpoint_store=checkpoint_store,
        logger=get_logger("test.batch"),
    )

    outcomes = runner.run([_context("ART-1", generator_context)], output_root=tmp_path)

    assert outcomes[0].status is PackageOutcomeStatus.SUCCEEDED
    assert builder.build_calls == ["ART-1"]
    assert checkpoint_store.get_record("ART-1").stage is ArticleStage.PACKAGED  # type: ignore[union-attr]


def test_run_continues_the_batch_after_one_article_fails(
    checkpoint_store: InMemoryCheckpointStore, generator_context: GeneratorContext, tmp_path: Path
) -> None:
    builder = _FakePackageBuilder()
    builder.fail_article_ids = {"ART-1"}
    runner = PackageBatchRunner(
        package_builder=builder,  # type: ignore[arg-type]
        checkpoint_store=checkpoint_store,
        logger=get_logger("test.batch"),
    )
    contexts = [_context("ART-1", generator_context), _context("ART-2", generator_context)]

    outcomes = runner.run(contexts, output_root=tmp_path)

    assert outcomes[0].status is PackageOutcomeStatus.FAILED
    assert outcomes[0].error_message is not None
    assert isinstance(outcomes[0].exception, PackageAssemblyError)
    assert outcomes[1].status is PackageOutcomeStatus.SUCCEEDED
    assert checkpoint_store.get_record("ART-1").stage is ArticleStage.FAILED  # type: ignore[union-attr]
    assert checkpoint_store.get_record("ART-2").stage is ArticleStage.PACKAGED  # type: ignore[union-attr]


def test_concurrent_runs_on_the_same_article_process_it_at_most_once(
    checkpoint_store: InMemoryCheckpointStore, generator_context: GeneratorContext, tmp_path: Path
) -> None:
    builder = _FakePackageBuilder()
    runner = PackageBatchRunner(
        package_builder=builder,  # type: ignore[arg-type]
        checkpoint_store=checkpoint_store,
        logger=get_logger("test.batch"),
    )
    context = _context("ART-1", generator_context)
    outcomes: list[PackageOutcomeStatus] = []
    lock = threading.Lock()

    def attempt() -> None:
        result = runner.run([context], output_root=tmp_path)
        with lock:
            outcomes.append(result[0].status)

    threads = [threading.Thread(target=attempt) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count(PackageOutcomeStatus.SUCCEEDED) == 1
    assert outcomes.count(PackageOutcomeStatus.SKIPPED) == 4
    assert builder.build_calls == ["ART-1"]


def test_run_skips_when_the_claim_transition_loses_the_race(
    generator_context: GeneratorContext, tmp_path: Path
) -> None:
    checkpoint_store = _ClaimAlwaysLosesCheckpointStore()
    builder = _FakePackageBuilder()
    runner = PackageBatchRunner(
        package_builder=builder,  # type: ignore[arg-type]
        checkpoint_store=checkpoint_store,
        logger=get_logger("test.batch"),
    )

    outcomes = runner.run([_context("ART-1", generator_context)], output_root=tmp_path)

    assert outcomes[0].status is PackageOutcomeStatus.SKIPPED
    assert builder.build_calls == []
