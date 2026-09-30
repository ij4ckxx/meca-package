"""Command-line entry point for the MECA Package Generation Engine.

Registered as the ``meca-engine`` console script (see ``pyproject.toml``'s
``[project.scripts]``). Milestone 1 (Foundation) implemented
``validate-config`` and ``version`` fully. **As of Milestone 2**, ``run``
is functional against a local folder source
(``--source-dir``) — S3 (``--source-prefix``) remains a placeholder,
since the concrete AWS credentials/wiring strategy is still an open
infrastructure decision (16_LLD_07_READINESS_ASSESSMENT.md §15.2 TQ-04).
Every other command remains a documented placeholder that reports which
future milestone implements it.

The ``scripts/`` directory (10_LLD_01_STRUCTURE_AND_PACKAGES.md §1) provides
thin operator-facing wrapper scripts that each invoke one of these
subcommands — this module is the single real implementation both the
``meca-engine`` console script and those wrapper scripts share.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from meca_engine import __version__
from meca_engine.constants import APP_NAME
from meca_engine.container import ServiceContainer, bootstrap_application, build_run_controller
from meca_engine.exceptions import MecaEngineError
from meca_engine.input.models import LocalBatchSource
from meca_engine.input.readers.local_reader import LocalFolderReader
from meca_engine.logging_ import StructuredLogger


def _bootstrap_or_exit(config_dir: Path | None, schema_dir: Path | None) -> ServiceContainer:
    """Bootstrap the application, converting a fatal config error into a clean CLI exit.

    Args:
        config_dir: Optional override for the configuration directory.
        schema_dir: Optional override for the config-schema directory.

    Returns:
        A populated :class:`~meca_engine.container.ServiceContainer`.
    """
    try:
        return bootstrap_application(config_dir=config_dir, schema_dir=schema_dir)
    except MecaEngineError as exc:
        click.echo(f"error: {exc.message}", err=True)
        sys.exit(1)


@click.group(name="meca-engine")
@click.version_option(version=__version__, prog_name=APP_NAME)
def cli() -> None:
    """MECA Package Generation Engine command-line interface."""


@cli.command(name="validate-config")
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=None,
    help="Override the configuration directory (defaults to MECA_ENGINE_CONFIG_DIR).",
)
@click.option(
    "--schema-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=None,
    help="Override the config-schema directory (defaults to schemas/config-schema).",
)
def validate_config(config_dir: Path | None, schema_dir: Path | None) -> None:
    """Validate the configuration tree without processing any articles.

    Loads and schema-validates every configuration file under the resolved
    configuration directory (runtime settings, feature flags, and every
    discoverable journal/publisher config), exiting non-zero on the first
    validation failure encountered — see
    12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §5.9.
    """
    container = _bootstrap_or_exit(config_dir, schema_dir)
    logger = container.resolve(StructuredLogger)
    logger.info("Configuration validated successfully", stage=__name__)
    click.echo("Configuration is valid.")


@cli.command(name="run")
@click.option(
    "--source-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=None,
    help="Local directory containing one subfolder per article (discovery + staging only).",
)
@click.option(
    "--source-prefix",
    type=str,
    default=None,
    help="S3 prefix identifying the batch of articles to process (not yet wired — TQ-04).",
)
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=None,
    help="Override the configuration directory (defaults to MECA_ENGINE_CONFIG_DIR).",
)
@click.option(
    "--schema-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=None,
    help="Override the config-schema directory (defaults to schemas/config-schema).",
)
def run(
    source_dir: Path | None,
    source_prefix: str | None,
    config_dir: Path | None,
    schema_dir: Path | None,
) -> None:
    """Discover and stage a batch of articles (Milestone 2: input & staging only).

    No XML parsing, metadata extraction, transformation, generation,
    validation, or packaging occurs — this command only proves out
    discovery, staging, integrity verification, and checkpoint-based
    resume support, per Milestone 2's scope. The full pipeline (from
    metadata loading onward) is deferred to later milestones
    (`08_IMPLEMENTATION_ROADMAP.md` Phases 2-6).
    """
    if source_dir is None:
        click.echo(
            "The 'run' command's S3 path (--source-prefix) is a placeholder "
            "pending an infrastructure decision (16_LLD_07_READINESS_ASSESSMENT.md "
            "§15.2 TQ-04). Pass --source-dir to run discovery+staging against a "
            "local folder instead."
        )
        return

    container = _bootstrap_or_exit(config_dir, schema_dir)
    reader = LocalFolderReader()
    run_controller = build_run_controller(container, reader)
    summary = run_controller.run(LocalBatchSource(root_path=source_dir), batch_id=source_dir.name)

    click.echo(
        f"Run {summary.run_id} complete: "
        f"{summary.succeeded_count} succeeded, "
        f"{summary.failed_count} failed, "
        f"{summary.skipped_count} skipped "
        f"(discovery failures: {summary.total_discovery_failures})."
    )
    if summary.failed_count > 0:
        sys.exit(1)


@cli.command(name="seed-doi-registry")
@click.option(
    "--source-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help="File containing historically-issued DOIs to import.",
)
def seed_doi_registry(source_file: Path | None) -> None:
    """Perform a one-time import of historically-issued DOIs into the registry.

    Not yet implemented — deferred until :mod:`meca_engine.registry` exists
    (08_IMPLEMENTATION_ROADMAP.md Phase 4, ADR-015).
    """
    del source_file
    click.echo(
        "The 'seed-doi-registry' command is a placeholder in Milestone 1 "
        "(Foundation). It will be implemented once meca_engine.registry "
        "exists — see 08_IMPLEMENTATION_ROADMAP.md Phase 4."
    )


@cli.command(name="rebuild-golden-baseline")
@click.option(
    "--confirm", is_flag=True, default=False, help="Required to actually run this command."
)
def rebuild_golden_baseline(confirm: bool) -> None:
    """Regenerate the golden-file regression baseline from the 3 real samples.

    Not yet implemented — deferred until the full generation pipeline
    exists. Per 14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §11.3, this
    command must only ever be run after an explicit reviewer sign-off on
    the resulting diff — the ``--confirm`` flag is reserved for that
    future safeguard.
    """
    del confirm
    click.echo(
        "The 'rebuild-golden-baseline' command is a placeholder in "
        "Milestone 1 (Foundation). It will be implemented once the full "
        "generation pipeline exists — see 14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §11.3."
    )


if __name__ == "__main__":
    cli()
