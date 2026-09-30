"""Unit tests for meca_engine.validation.xml_validator.

Runs against the real, vendored DTDs (DTD-compliance milestone) —
`tests/fixtures/dtd_examples/` holds the official NISO MECA example
files (https://github.com/niso-standards/meca/tree/main/examples),
known-good against those exact DTDs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.validation import ValidationResult, validate_generated_file

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dtd_examples"

_MALFORMED = b"<article><unclosed></article>"
_MANIFEST_MISSING_REQUIRED_INSTANCE = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<manifest xmlns="https://manuscriptexchange.org/schema/manifest" manifest-version="1">'
    b'<item id="x" item-type="article-metadata"/>'
    b"</manifest>"
)


def _fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def test_well_formed_document_with_no_dtd_reports_dtd_not_checked() -> None:
    report = validate_generated_file("x_raw.xml", b"<article><front /></article>")

    assert report.result is ValidationResult.PASS
    assert report.well_formed_result is ValidationResult.PASS
    assert report.dtd_name is None
    assert report.dtd_available is False
    assert report.dtd_result is None
    assert report.error_count == 0


def test_malformed_document_is_reported_as_error_and_skips_dtd_check() -> None:
    report = validate_generated_file("x-2025-0001_article.xml", _MALFORMED)

    assert report.result is ValidationResult.ERROR
    assert report.well_formed_result is ValidationResult.ERROR
    assert report.dtd_result is None
    assert report.error_count == 1
    assert report.issues[0].line == 1
    assert report.issues[0].check == "well-formed"


@pytest.mark.parametrize(
    ("filename", "expected_dtd_name", "example_file"),
    [
        ("x_article.xml", "jats-archiving-1.2", "article.xml"),
        ("x_reviews.xml", "meca-1.0", "reviews.xml"),
        ("x_manifest.xml", "meca-1.0", "manifest.xml"),
        ("x_transfer.xml", "meca-1.0", "transfer.xml"),
    ],
)
def test_official_meca_example_is_dtd_valid(
    filename: str, expected_dtd_name: str, example_file: str
) -> None:
    """Each NISO MECA reference example must validate cleanly against its own vendored DTD."""
    report = validate_generated_file(filename, _fixture(example_file))

    assert report.dtd_name == expected_dtd_name
    assert report.dtd_available is True
    assert report.well_formed_result is ValidationResult.PASS
    assert report.dtd_result is ValidationResult.PASS
    assert report.result is ValidationResult.PASS
    assert report.error_count == 0


def test_dtd_invalid_document_is_well_formed_but_fails_dtd_separately() -> None:
    """A document missing a DTD-required element fails dtd_result, not well_formed_result."""
    report = validate_generated_file("x_manifest.xml", _MANIFEST_MISSING_REQUIRED_INSTANCE)

    assert report.well_formed_result is ValidationResult.PASS
    assert report.dtd_available is True
    assert report.dtd_result is ValidationResult.ERROR
    assert report.result is ValidationResult.ERROR
    assert report.error_count >= 1
    assert all(i.check == "dtd" for i in report.issues)


def test_unknown_file_type_has_no_dtd_but_still_checks_well_formedness() -> None:
    report = validate_generated_file("x_raw.xml", b"<article><front /></article>")

    assert report.dtd_name is None
    assert report.dtd_available is False
    assert report.result is ValidationResult.PASS

    malformed_report = validate_generated_file("x_raw.xml", _MALFORMED)
    assert malformed_report.result is ValidationResult.ERROR
