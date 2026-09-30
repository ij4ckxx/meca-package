"""Unit tests for meca_engine.container (ServiceContainer, bootstrap_application)."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from meca_engine.checkpoint.store import CheckpointStore
from meca_engine.config.registry import ConfigRegistry
from meca_engine.container import ServiceContainer, bootstrap_application, build_run_controller
from meca_engine.input.models import LocalBatchSource
from meca_engine.input.readers.local_reader import LocalFolderReader
from meca_engine.logging_.structured_logger import StructuredLogger
from meca_engine.orchestrator.run_controller import RunController

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


class _ServiceA:
    pass


class _ServiceB:
    pass


def test_register_and_resolve_round_trip() -> None:
    container = ServiceContainer()
    instance = _ServiceA()

    container.register(_ServiceA, instance)

    assert container.resolve(_ServiceA) is instance


def test_resolve_unregistered_type_raises_key_error() -> None:
    container = ServiceContainer()

    with pytest.raises(KeyError):
        container.resolve(_ServiceB)


def test_register_twice_raises_value_error() -> None:
    container = ServiceContainer()
    container.register(_ServiceA, _ServiceA())

    with pytest.raises(ValueError, match="already registered"):
        container.register(_ServiceA, _ServiceA())


def test_replace_overrides_an_existing_registration() -> None:
    container = ServiceContainer()
    first = _ServiceA()
    second = _ServiceA()
    container.register(_ServiceA, first)

    container.replace(_ServiceA, second)

    assert container.resolve(_ServiceA) is second


def test_is_registered_reflects_registration_state() -> None:
    container = ServiceContainer()

    assert container.is_registered(_ServiceA) is False

    container.register(_ServiceA, _ServiceA())

    assert container.is_registered(_ServiceA) is True


def test_bootstrap_application_registers_foundation_services(
    valid_config_dir: Path, schema_dir: Path
) -> None:
    container = bootstrap_application(config_dir=valid_config_dir, schema_dir=schema_dir)

    logger = container.resolve(StructuredLogger)
    registry = container.resolve(ConfigRegistry)

    assert isinstance(logger, StructuredLogger)
    assert isinstance(registry, ConfigRegistry)
    assert registry.get_journal_config("example-journal").journal_id == "example-journal"


def test_bootstrap_application_registers_an_in_memory_checkpoint_store(
    valid_config_dir: Path, schema_dir: Path
) -> None:
    from meca_engine.checkpoint.backends.in_memory import InMemoryCheckpointStore

    container = bootstrap_application(config_dir=valid_config_dir, schema_dir=schema_dir)

    checkpoint_store = container.resolve(CheckpointStore)  # type: ignore[type-abstract]

    assert isinstance(checkpoint_store, InMemoryCheckpointStore)


def test_bootstrap_application_propagates_configuration_errors(
    schema_dir: Path, tmp_path: Path
) -> None:
    from meca_engine.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        bootstrap_application(config_dir=tmp_path, schema_dir=schema_dir)


def test_build_run_controller_wires_a_functional_run_controller(
    valid_config_dir: Path, schema_dir: Path, valid_batch_root: Path
) -> None:
    container = bootstrap_application(config_dir=valid_config_dir, schema_dir=schema_dir)
    reader = LocalFolderReader()

    run_controller = build_run_controller(container, reader, run_id="container-test-run")

    assert isinstance(run_controller, RunController)
    try:
        summary = run_controller.run(
            LocalBatchSource(root_path=valid_batch_root), batch_id="container-test-batch"
        )
        assert summary.succeeded_count == 2
    finally:
        stager = run_controller._stager  # noqa: SLF001 - test-only introspection
        shutil.rmtree(stager.working_dir_root / stager.run_id, ignore_errors=True)
