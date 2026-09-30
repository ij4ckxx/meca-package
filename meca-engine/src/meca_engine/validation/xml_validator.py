"""XML structural validation — DTD conformance + well-formedness.

Implements :class:`~meca_engine.generators.validation_hooks.DtdValidationHook`
against real DTD files vendored under ``schemas/dtd/`` (ADR-025 /
RISK-023, and the DTD-compliance milestone that populated them — see
``schemas/dtd/*/README.md``). Well-formedness and DTD conformance are
two distinct checks, reported separately (``well_formed_result`` /
``dtd_result`` on :class:`~meca_engine.validation.models.FileValidationReport`)
so a document that parses fine but violates its DTD is never reported
as an undifferentiated "pass". If a DTD is ever missing (a file type
with no vendored DTD, or one removed), ``dtd_result`` is ``None`` —
"not checked", never conflated with a passing result.

Runs strictly after a package is already built (see
``service/worker.py``): never raises, never stops package generation,
only ever reports findings.
"""

from __future__ import annotations

import dataclasses
from functools import cache
from pathlib import Path

from lxml import etree

from meca_engine.generators.validation_hooks import (
    DtdValidationHook,
    ValidationIssue,
    ValidationIssueSeverity,
)
from meca_engine.validation.dtd_issue_classifier import classify_dtd_issue
from meca_engine.validation.models import FileValidationReport, ValidationResult

# <repo>/schemas/dtd/ — three levels up from this file (validation/xml_validator.py
# -> meca_engine -> src -> meca-engine), matching every other DEFAULT_*_DIR
# convention in this codebase.
_SCHEMA_DTD_ROOT = Path(__file__).resolve().parents[3] / "schemas" / "dtd"

# Maps each generated filename suffix to (dtd directory name, expected
# vendored filename) — the filename mirrors each document's own DOCTYPE
# SYSTEM identifier exactly, so the moment a real DTD is vendored under
# that name, validation activates with no code change.
_DTD_BY_SUFFIX: dict[str, tuple[str, str]] = {
    "_article.xml": ("jats-archiving-1.2", "JATS-archivearticle1.dtd"),
    "_reviews.xml": ("meca-1.0", "reviews-1.0.dtd"),
    "_manifest.xml": ("meca-1.0", "manifest-1.0.dtd"),
    "_transfer.xml": ("meca-1.0", "transfer-1.0.dtd"),
}

# The 4 generated filenames Milestone 2 validates (excludes raw.xml,
# which has no DTD of its own) — exposed for
# :mod:`meca_engine.validation.package_validator`.
VALIDATED_FILENAME_SUFFIXES: tuple[str, ...] = tuple(_DTD_BY_SUFFIX)

_WELL_FORMED_CHECK = "well-formed"
_DTD_CHECK = "dtd"


@cache
def _load_dtd(dtd_path: str) -> etree.DTD:
    """Parse and cache a vendored DTD file — it never changes within a batch run.

    Re-parsing the same DTD file from disk on every one of the (up to 4
    per article) validation calls is pure repeated work at scale (up to
    ~400,000 redundant re-reads/recompiles across a 100,000-article
    batch); an ``etree.DTD`` object is read-only and safe to reuse across
    validations, which is exactly what ``.validate()`` is designed for.
    """
    return etree.DTD(dtd_path)


class LxmlDtdValidationHook(DtdValidationHook):
    """Validates an already-well-formed document against a vendored DTD."""

    def validate(self, document: bytes, *, dtd_path: str) -> tuple[ValidationIssue, ...]:
        """Validate ``document`` against the DTD at ``dtd_path``.

        Returns one ERROR-severity :class:`ValidationIssue` per DTD
        violation lxml reports, each with its line number when lxml
        provides one. Raises nothing: a malformed DTD file or an
        unparseable document is reported as a single issue, not an
        exception — validation must never stop package generation.
        """
        try:
            dtd = _load_dtd(dtd_path)
        except etree.DTDParseError as exc:
            return (
                ValidationIssue(
                    severity=ValidationIssueSeverity.ERROR,
                    message=f"Could not parse DTD {dtd_path!r}: {exc}",
                    check=_DTD_CHECK,
                ),
            )

        try:
            tree = etree.fromstring(document)
        except etree.XMLSyntaxError as exc:
            return (
                ValidationIssue(
                    severity=ValidationIssueSeverity.ERROR,
                    message=f"Document is not well-formed: {exc}",
                    line=exc.lineno,
                    check=_WELL_FORMED_CHECK,
                ),
            )

        if dtd.validate(tree):
            return ()

        return tuple(
            ValidationIssue(
                severity=ValidationIssueSeverity.ERROR,
                message=error.message,
                line=error.line or None,
                xpath=error.path,
                check=_DTD_CHECK,
            )
            for error in dtd.error_log  # type: ignore[attr-defined] # lxml-stubs gap
        )


def _check_well_formedness(document: bytes) -> tuple[ValidationIssue, ...]:
    """XML well-formedness only — always possible, no DTD required."""
    try:
        etree.fromstring(document)
    except etree.XMLSyntaxError as exc:
        return (
            ValidationIssue(
                severity=ValidationIssueSeverity.ERROR,
                message=f"Document is not well-formed: {exc}",
                line=exc.lineno,
                check=_WELL_FORMED_CHECK,
            ),
        )
    return ()


def validate_generated_file(filename: str, document: bytes) -> FileValidationReport:
    """Validate one generated XML file's bytes, by its own filename convention.

    Well-formedness is always checked first. DTD conformance is checked
    only when the document is well-formed *and* a real DTD is vendored
    for this file type — an unparseable document can't meaningfully be
    checked against a DTD, and a missing DTD means conformance is
    simply unknown, not passing.

    Args:
        filename: The file's name as packaged (e.g. ``"<id>_article.xml"``) —
            used only to look up which DTD it should conform to.
        document: The file's complete, already-serialized bytes.

    Returns:
        A :class:`FileValidationReport` with well-formedness and DTD
        conformance reported as two distinct results.
    """
    suffix_entry = next(
        (v for suffix, v in _DTD_BY_SUFFIX.items() if filename.endswith(suffix)), None
    )
    dtd_name = suffix_entry[0] if suffix_entry else None

    well_formed_issues = _check_well_formedness(document)
    if well_formed_issues:
        return _build_report(
            filename,
            dtd_name=dtd_name,
            dtd_available=False,
            well_formed_issues=well_formed_issues,
            dtd_issues=None,
        )

    if suffix_entry is None:
        return _build_report(
            filename, dtd_name=None, dtd_available=False, well_formed_issues=(), dtd_issues=None
        )

    dtd_dir_name, dtd_filename = suffix_entry
    dtd_path = _SCHEMA_DTD_ROOT / dtd_dir_name / dtd_filename

    if not dtd_path.is_file():
        return _build_report(
            filename,
            dtd_name=dtd_dir_name,
            dtd_available=False,
            well_formed_issues=(),
            dtd_issues=None,
        )

    hook = LxmlDtdValidationHook()
    dtd_issues = tuple(
        dataclasses.replace(issue, category=classify_dtd_issue(issue.message).value)
        for issue in hook.validate(document, dtd_path=str(dtd_path))
    )
    return _build_report(
        filename,
        dtd_name=dtd_dir_name,
        dtd_available=True,
        well_formed_issues=(),
        dtd_issues=dtd_issues,
    )


def _result_from_issues(issues: tuple[ValidationIssue, ...]) -> ValidationResult:
    if any(i.severity is ValidationIssueSeverity.ERROR for i in issues):
        return ValidationResult.ERROR
    if any(i.severity is ValidationIssueSeverity.WARNING for i in issues):
        return ValidationResult.WARNING
    return ValidationResult.PASS


def _build_report(
    filename: str,
    *,
    dtd_name: str | None,
    dtd_available: bool,
    well_formed_issues: tuple[ValidationIssue, ...],
    dtd_issues: tuple[ValidationIssue, ...] | None,
) -> FileValidationReport:
    well_formed_result = _result_from_issues(well_formed_issues)
    dtd_result = _result_from_issues(dtd_issues) if dtd_issues is not None else None
    issues = well_formed_issues + (dtd_issues or ())
    error_count = sum(1 for i in issues if i.severity is ValidationIssueSeverity.ERROR)
    warning_count = sum(1 for i in issues if i.severity is ValidationIssueSeverity.WARNING)
    result = (
        ValidationResult.ERROR
        if well_formed_result is ValidationResult.ERROR or dtd_result is ValidationResult.ERROR
        else ValidationResult.WARNING
        if dtd_result is ValidationResult.WARNING
        else ValidationResult.PASS
    )
    return FileValidationReport(
        filename=filename,
        dtd_name=dtd_name,
        dtd_available=dtd_available,
        result=result,
        well_formed_result=well_formed_result,
        dtd_result=dtd_result,
        error_count=error_count,
        warning_count=warning_count,
        issues=issues,
    )
