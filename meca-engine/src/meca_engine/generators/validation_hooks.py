"""Validation extension points — Generator Framework (Milestone 6A).

Interfaces only, per this milestone's explicit scope: no DTD parsing, no
XML Schema checking, and no business-rule evaluation is implemented here
or anywhere in this framework. `11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md
§4.8`'s `validation.engine.ValidationEngine` (a future milestone) is the
concrete consumer that will register real implementations of these
hooks — this module exists only so :class:`~meca_engine.generators.base.BaseGenerator`
has a stable extension point to call into, decided now so the framework
never needs to change shape once validation is actually implemented.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, unique


@unique
class ValidationIssueSeverity(str, Enum):
    """Severity of one validation hook finding."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ValidationIssue:
    """One finding reported by a validation hook.

    Attributes:
        severity: How serious this finding is.
        message: A human-readable description.
        location: Where the issue was found (an XPath, line number, or
            similar), when the hook can determine one. Kept for any
            existing caller that only wants one free-form location
            string; ``line``/``xpath`` below are the same information,
            split out for structured reporting.
        line: The 1-based source line the issue was found at, when the
            underlying parser/validator reports one.
        xpath: An XPath to the offending element, when determinable.
        check: Which check produced this finding — ``"well-formed"`` or
            ``"dtd"`` — so a report can show the two results separately
            instead of one merged pass/fail. ``None`` for any hook that
            predates this distinction.
        category: For a ``"dtd"`` finding, its spec-alignment
            classification (see
            :mod:`meca_engine.validation.dtd_issue_classifier` —
            not imported here to keep this module's interfaces generic)
            — one of ``"source_data_issue"``, ``"business_rule_candidate"``,
            ``"recovery_rule_candidate"``, ``"validation_only"``. ``None``
            for well-formedness findings, which this classification
            doesn't apply to.
    """

    severity: ValidationIssueSeverity
    message: str
    location: str | None = None
    line: int | None = None
    xpath: str | None = None
    check: str | None = None
    category: str | None = None


class DtdValidationHook(ABC):
    """Extension point for DTD-based structural validation.

    A future :mod:`meca_engine.validation` implementation validates a
    generated document's bytes against a vendored DTD file and returns
    every finding — this class defines only the contract.
    """

    @abstractmethod
    def validate(self, document: bytes, *, dtd_path: str) -> tuple[ValidationIssue, ...]:
        """Validate ``document`` against the DTD at ``dtd_path``.

        Args:
            document: The complete, already-serialized document bytes.
            dtd_path: Filesystem path to the vendored DTD file to
                validate against.

        Returns:
            Every finding, empty if the document is fully DTD-valid.
        """


class SchemaValidationHook(ABC):
    """Extension point for XML Schema (XSD)-based structural validation."""

    @abstractmethod
    def validate(self, document: bytes, *, schema_path: str) -> tuple[ValidationIssue, ...]:
        """Validate ``document`` against the XML Schema at ``schema_path``.

        Args:
            document: The complete, already-serialized document bytes.
            schema_path: Filesystem path to the XML Schema file to
                validate against.

        Returns:
            Every finding, empty if the document is fully schema-valid.
        """


class BusinessRuleValidationHook(ABC):
    """Extension point for Business Rule Book-driven content validation.

    Distinct from :class:`DtdValidationHook`/:class:`SchemaValidationHook`:
    a document can be perfectly well-formed and DTD/schema-valid while
    still violating a Business Rule Book rule (e.g. a required field left
    empty) — 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.8's
    ``ValidationEngine`` runs this category of rule separately.
    """

    @abstractmethod
    def validate(self, document: bytes, *, generator_name: str) -> tuple[ValidationIssue, ...]:
        """Validate ``document`` against registered business rules.

        Args:
            document: The complete, already-serialized document bytes.
            generator_name: Which generator produced ``document`` — a
                business-rule hook typically only applies to one
                document type.

        Returns:
            Every finding, empty if no configured rule was violated.
        """
