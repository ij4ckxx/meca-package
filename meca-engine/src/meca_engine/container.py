"""Application bootstrap and service registration.

Milestone 1 (Foundation) note: 10_LLD_01_STRUCTURE_AND_PACKAGES.md does not
enumerate a dedicated "container" module because, at LLD-authoring time, no
milestone-1-scoped deliverable required one. The current implementation
task explicitly requires "the application bootstrap and service
registration mechanism" as a Foundation deliverable; this module satisfies
that requirement without altering any package boundary, import-direction
rule, or module responsibility defined in the LLD — it only *wires together*
the foundation-layer services (:mod:`meca_engine.config`,
:mod:`meca_engine.logging_`) that the LLD already specifies, in the order
the LLD's own dependency diagram requires (10_LLD_01 §2.3: ``config`` and
``exceptions`` before everything else; ``logging_`` alongside them).

**As of Milestone 2**: also constructs and registers an in-memory
:class:`~meca_engine.checkpoint.store.CheckpointStore` (per the current
task's "provide an in-memory implementation suitable for testing"
requirement — a durable backend remains TQ-03), and
:func:`build_run_controller` wires the Input & Staging Layer (a chosen
:class:`~meca_engine.input.readers.base.InputReader`, discovery, staging,
checkpoint, and a deterministic scheduler) into a
:class:`~meca_engine.orchestrator.run_controller.RunController`. The DOI
Registry, S3 credentials/client wiring, and every later-pipeline service
remain deferred to the milestones that implement them.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from meca_engine.checkpoint.backends.in_memory import InMemoryCheckpointStore
from meca_engine.checkpoint.store import CheckpointStore
from meca_engine.config.environment import load_environment_settings
from meca_engine.config.loader import ConfigLoader
from meca_engine.config.registry import ConfigRegistry
from meca_engine.constants import APP_NAME, DEFAULT_CONFIG_SCHEMA_DIR
from meca_engine.exceptions import MecaEngineError
from meca_engine.input.discovery import BatchDiscovery
from meca_engine.input.staging import Stager
from meca_engine.logging_ import StructuredLogger, configure_root_logging, get_logger
from meca_engine.orchestrator.run_controller import RunController
from meca_engine.orchestrator.scheduler import SequentialWorkerScheduler

if TYPE_CHECKING:
    from meca_engine.input.readers.base import InputReader

T = TypeVar("T")


class ServiceContainer:
    """A minimal, explicit service registry.

    Deliberately not a "magic" auto-wiring dependency-injection framework:
    every registration is explicit, and every resolution fails loudly
    (``KeyError``-derived) if the requested service type was never
    registered. This keeps the wiring fully traceable in
    :func:`bootstrap_application` rather than hidden behind reflection or
    decorators, consistent with 14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md's
    general preference for explicitness over convenience-through-magic.
    """

    def __init__(self) -> None:
        """Initialize an empty service container."""
        self._services: dict[type, object] = {}

    def register(self, service_type: type[T], instance: T) -> None:
        """Register a service instance under its type.

        Args:
            service_type: The type (typically a class) other components
                will use to resolve this service.
            instance: The concrete instance to register.

        Raises:
            ValueError: If a service of this exact type is already
                registered — re-registration must be explicit
                (:meth:`replace`), never accidental.
        """
        if service_type in self._services:
            raise ValueError(
                f"A service of type {service_type!r} is already registered. "
                f"Use replace() to intentionally override it."
            )
        self._services[service_type] = instance

    def replace(self, service_type: type[T], instance: T) -> None:
        """Register a service instance, explicitly overriding any existing registration.

        Args:
            service_type: The type to register the instance under.
            instance: The concrete instance to register.
        """
        self._services[service_type] = instance

    def resolve(self, service_type: type[T]) -> T:
        """Resolve a previously-registered service instance.

        Args:
            service_type: The type to resolve.

        Returns:
            The registered instance.

        Raises:
            KeyError: If no service of this type has been registered.
        """
        try:
            return self._services[service_type]  # type: ignore[return-value]
        except KeyError as exc:
            raise KeyError(
                f"No service of type {service_type!r} has been registered "
                f"with this ServiceContainer."
            ) from exc

    def is_registered(self, service_type: type[T]) -> bool:
        """Return whether a service of the given type is currently registered.

        Args:
            service_type: The type to check.

        Returns:
            ``True`` if a service of this type is registered.
        """
        return service_type in self._services


def bootstrap_application(
    *,
    config_dir: Path | None = None,
    schema_dir: Path | None = None,
) -> ServiceContainer:
    """Wire up the Foundation-layer services and return a populated container.

    This is the single entry point every CLI command and every future
    orchestrator uses to obtain a fully-configured application. It performs,
    in order:

    1. Resolve environment settings (:mod:`meca_engine.config.environment`).
    2. Configure the root structured logger
       (:mod:`meca_engine.logging_.structured_logger`) — must happen before
       any other component logs anything.
    3. Load and validate all configuration
       (:mod:`meca_engine.config.loader`) into a :class:`ConfigRegistry`.
    4. Register both the logger and the config registry into a
       :class:`ServiceContainer`.

    Args:
        config_dir: Override for the configuration directory; defaults to
            the ``MECA_ENGINE_CONFIG_DIR`` environment variable's value.
        schema_dir: Override for the config-schema directory; defaults to
            ``schemas/config-schema`` relative to the current working
            directory.

    Returns:
        A :class:`ServiceContainer` with the Foundation-layer services
        registered under their concrete types (:class:`StructuredLogger`,
        :class:`ConfigRegistry`).

    Raises:
        ConfigurationError: If configuration fails to load or validate —
            propagated unchanged from :mod:`meca_engine.config.loader`,
            since this is a batch-level failure the caller must not
            swallow (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.3).
    """
    environment_settings = load_environment_settings()

    configure_root_logging(debug_enabled=environment_settings.debug_logging_enabled)
    logger = get_logger(__name__, debug_enabled=environment_settings.debug_logging_enabled)
    logger.info(
        f"{APP_NAME} bootstrap starting",
        stage=__name__,
        context={"environment": environment_settings.environment.value},
    )

    resolved_config_dir = config_dir if config_dir is not None else environment_settings.config_dir
    resolved_schema_dir = schema_dir if schema_dir is not None else Path(DEFAULT_CONFIG_SCHEMA_DIR)

    loader = ConfigLoader(config_dir=resolved_config_dir, schema_dir=resolved_schema_dir)

    try:
        app_config = loader.load_app_config(environment_settings)
    except MecaEngineError as exc:
        logger.log_exception(
            exc, message="Application bootstrap failed while loading configuration"
        )
        raise

    config_registry = ConfigRegistry(app_config)
    checkpoint_store = InMemoryCheckpointStore()

    container = ServiceContainer()
    container.register(StructuredLogger, logger)
    container.register(ConfigRegistry, config_registry)
    # Registered under the abstract CheckpointStore type deliberately —
    # callers resolve the interface, not a concrete backend (10_LLD_01 §2.3).
    # mypy's type-abstract check assumes a Type[T] key must itself be
    # instantiable; that assumption doesn't hold for this registry pattern.
    container.register(CheckpointStore, checkpoint_store)  # type: ignore[type-abstract]

    logger.audit(
        f"{APP_NAME} bootstrap completed",
        context={
            "environment": environment_settings.environment.value,
            "configured_journals": sorted(app_config.journals),
            "configured_publishers": sorted(app_config.publishers),
        },
    )
    return container


def build_run_controller(
    container: ServiceContainer,
    reader: InputReader,
    *,
    run_id: str | None = None,
) -> RunController:
    """Wire the Input & Staging Layer into a ready-to-run :class:`RunController`.

    Args:
        container: A container already populated by
            :func:`bootstrap_application`.
        reader: The concrete
            :class:`~meca_engine.input.readers.base.InputReader` to use
            (e.g. a :class:`~meca_engine.input.readers.local_reader.LocalFolderReader`
            or :class:`~meca_engine.input.readers.s3_reader.S3Reader`) —
            chosen by the caller based on the batch source's kind.
        run_id: A unique id for this run; auto-generated if omitted.

    Returns:
        A :class:`~meca_engine.orchestrator.run_controller.RunController`
        ready to process a batch via :meth:`RunController.run`.
    """
    logger = container.resolve(StructuredLogger)
    checkpoint_store = container.resolve(CheckpointStore)  # type: ignore[type-abstract]
    config_registry = container.resolve(ConfigRegistry)

    working_dir_root = Path(config_registry.app_config.runtime.staging.working_dir_root)
    discovery = BatchDiscovery(reader, logger)
    stager = Stager(reader, working_dir_root, logger, run_id=run_id)
    scheduler = SequentialWorkerScheduler()

    return RunController(discovery, stager, checkpoint_store, scheduler, logger, run_id=run_id)
