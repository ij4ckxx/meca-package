"""Validation report data model — DTD/well-formedness validation.

Built on the existing :class:`~meca_engine.generators.validation_hooks.ValidationIssue`/
:class:`~meca_engine.generators.validation_hooks.ValidationIssueSeverity`
types rather than introducing a second issue model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meca_engine.generators.validation_hooks import ValidationIssue


@unique
class ValidationResult(str, Enum):
    """One file's overall validation outcome."""

    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class FileValidationReport:
    """Validation findings for one generated XML file.

    Attributes:
        filename: The file's name within the package (e.g. ``"<id>_article.xml"``).
        dtd_name: The DTD this file is expected to conform to (e.g.
            ``"jats-archiving-1.2"``), or ``None`` if this file type has
            no associated DTD.
        dtd_available: Whether a real, vendored DTD file was found at
            the expected path. ``False`` means DTD conformance could not
            be checked at all — never conflated with a passing result.
        result: The overall PASS/WARNING/ERROR outcome for this file —
            the worse of ``well_formed_result`` and ``dtd_result``.
        well_formed_result: Whether the document parses as XML at all.
            Always checked, independent of DTD availability.
        dtd_result: Whether the document conforms to ``dtd_name``.
            ``None`` when DTD conformance was not checked at all (no
            vendored DTD, or the document isn't even well-formed) —
            kept distinct from ``ValidationResult.PASS`` so a report
            never implies "DTD-valid" for a file that was never
            actually checked against one.
        error_count: Number of ERROR-severity issues.
        warning_count: Number of WARNING-severity issues.
        issues: Every individual finding.
    """

    filename: str
    dtd_name: str | None
    dtd_available: bool
    result: ValidationResult
    well_formed_result: ValidationResult
    dtd_result: ValidationResult | None
    error_count: int
    warning_count: int
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "filename": self.filename,
            "dtd_name": self.dtd_name,
            "dtd_available": self.dtd_available,
            "result": self.result.value,
            "well_formed_result": self.well_formed_result.value,
            "dtd_result": self.dtd_result.value if self.dtd_result else None,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                {
                    "severity": i.severity.value,
                    "message": i.message,
                    "line": i.line,
                    "xpath": i.xpath,
                    "check": i.check,
                    "category": i.category,
                }
                for i in self.issues
            ],
        }


@dataclass(frozen=True)
class PackageValidationReport:
    """Validation findings for every generated XML file in one package."""

    article_id: str
    files: tuple[FileValidationReport, ...] = field(default_factory=tuple)

    @property
    def overall_result(self) -> ValidationResult:
        """The worst individual file result, ERROR > WARNING > PASS."""
        if any(f.result is ValidationResult.ERROR for f in self.files):
            return ValidationResult.ERROR
        if any(f.result is ValidationResult.WARNING for f in self.files):
            return ValidationResult.WARNING
        return ValidationResult.PASS

    @property
    def overall_dtd_result(self) -> ValidationResult | None:
        """The worst ``dtd_result`` among files actually DTD-checked; ``None`` if none were."""
        checked = [f.dtd_result for f in self.files if f.dtd_result is not None]
        if not checked:
            return None
        if ValidationResult.ERROR in checked:
            return ValidationResult.ERROR
        if ValidationResult.WARNING in checked:
            return ValidationResult.WARNING
        return ValidationResult.PASS

    @property
    def total_errors(self) -> int:
        """Sum of every file's error count."""
        return sum(f.error_count for f in self.files)

    @property
    def total_warnings(self) -> int:
        """Sum of every file's warning count."""
        return sum(f.warning_count for f in self.files)

    @property
    def category_counts(self) -> dict[str, int]:
        """Count of remaining DTD findings per spec-alignment category.

        See :mod:`meca_engine.validation.dtd_issue_classifier`. Counted
        across every file in this package. Well-formedness findings
        (``category is None``) are not counted here — this is
        specifically about classified, remaining DTD violations.
        """
        counts: dict[str, int] = {}
        for f in self.files:
            for issue in f.issues:
                if issue.category is None:
                    continue
                counts[issue.category] = counts.get(issue.category, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        overall_dtd = self.overall_dtd_result
        return {
            "article_id": self.article_id,
            "overall_result": self.overall_result.value,
            "overall_dtd_result": overall_dtd.value if overall_dtd else None,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "category_counts": self.category_counts,
            "files": [f.to_dict() for f in self.files],
        }
