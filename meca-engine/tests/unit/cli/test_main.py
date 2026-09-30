"""Unit tests for meca_engine.cli.main."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from meca_engine import __version__
from meca_engine.cli.main import cli

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_version_option_reports_the_package_version(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output


def test_validate_config_succeeds_against_the_fixture_config(
    runner: CliRunner, valid_config_dir: Path, schema_dir: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "validate-config",
            "--config-dir",
            str(valid_config_dir),
            "--schema-dir",
            str(schema_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Configuration is valid." in result.output


def test_validate_config_fails_cleanly_against_an_empty_config_dir(
    runner: CliRunner, schema_dir: Path, tmp_path: Path
) -> None:
    result = runner.invoke(
        cli,
        ["validate-config", "--config-dir", str(tmp_path), "--schema-dir", str(schema_dir)],
    )

    assert result.exit_code == 1
    assert "error:" in result.output


def test_run_command_reports_s3_is_a_placeholder_when_no_source_dir_given(
    runner: CliRunner,
) -> None:
    result = runner.invoke(cli, ["run"])

    assert result.exit_code == 0
    assert "placeholder" in result.output


def test_run_command_stages_a_local_batch_end_to_end(
    runner: CliRunner, valid_config_dir: Path, schema_dir: Path, valid_batch_root: Path
) -> None:
    try:
        result = runner.invoke(
            cli,
            [
                "run",
                "--source-dir",
                str(valid_batch_root),
                "--config-dir",
                str(valid_config_dir),
                "--schema-dir",
                str(schema_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        assert "2 succeeded" in result.output
        assert "0 failed" in result.output
    finally:
        shutil.rmtree("/tmp/meca-engine-test-work", ignore_errors=True)


def test_run_command_exits_non_zero_when_an_article_fails(
    runner: CliRunner, valid_config_dir: Path, schema_dir: Path, tmp_path: Path
) -> None:
    bad_root = tmp_path / "bad-batch"
    (bad_root / "ART-BAD").mkdir(parents=True)  # no xml, no rounds -> discovery failure

    try:
        result = runner.invoke(
            cli,
            [
                "run",
                "--source-dir",
                str(bad_root),
                "--config-dir",
                str(valid_config_dir),
                "--schema-dir",
                str(schema_dir),
            ],
        )

        assert result.exit_code == 1
        assert "1 failed" in result.output
    finally:
        shutil.rmtree("/tmp/meca-engine-test-work", ignore_errors=True)


def test_seed_doi_registry_command_reports_it_is_a_placeholder(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["seed-doi-registry"])

    assert result.exit_code == 0
    assert "placeholder" in result.output


def test_rebuild_golden_baseline_command_reports_it_is_a_placeholder(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["rebuild-golden-baseline"])

    assert result.exit_code == 0
    assert "placeholder" in result.output


def test_cli_group_lists_all_expected_commands(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    for command_name in (
        "validate-config",
        "run",
        "seed-doi-registry",
        "rebuild-golden-baseline",
    ):
        assert command_name in result.output
