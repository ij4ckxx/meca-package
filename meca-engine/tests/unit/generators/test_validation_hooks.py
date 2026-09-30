"""Unit tests for meca_engine.generators.validation_hooks."""

from __future__ import annotations

import pytest

from meca_engine.generators.validation_hooks import (
    BusinessRuleValidationHook,
    DtdValidationHook,
    SchemaValidationHook,
    ValidationIssue,
    ValidationIssueSeverity,
)

pytestmark = pytest.mark.unit


class _AlwaysValidDtdHook(DtdValidationHook):
    def validate(self, document: bytes, *, dtd_path: str) -> tuple[ValidationIssue, ...]:
        return ()


class _AlwaysFindsIssueSchemaHook(SchemaValidationHook):
    def validate(self, document: bytes, *, schema_path: str) -> tuple[ValidationIssue, ...]:
        return (ValidationIssue(severity=ValidationIssueSeverity.ERROR, message="schema issue"),)


class _AlwaysValidBusinessRuleHook(BusinessRuleValidationHook):
    def validate(self, document: bytes, *, generator_name: str) -> tuple[ValidationIssue, ...]:
        return ()


def test_dtd_validation_hook_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        DtdValidationHook()  # type: ignore[abstract]


def test_schema_validation_hook_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        SchemaValidationHook()  # type: ignore[abstract]


def test_business_rule_validation_hook_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BusinessRuleValidationHook()  # type: ignore[abstract]


def test_concrete_dtd_hook_returns_no_issues() -> None:
    hook = _AlwaysValidDtdHook()

    assert hook.validate(b"<article/>", dtd_path="/dtds/jats.dtd") == ()


def test_concrete_schema_hook_returns_an_issue() -> None:
    hook = _AlwaysFindsIssueSchemaHook()

    issues = hook.validate(b"<manifest/>", schema_path="/schemas/manifest.xsd")

    assert len(issues) == 1
    assert issues[0].severity is ValidationIssueSeverity.ERROR
    assert issues[0].message == "schema issue"


def test_concrete_business_rule_hook_returns_no_issues() -> None:
    hook = _AlwaysValidBusinessRuleHook()

    assert hook.validate(b"<article/>", generator_name="article_xml") == ()


def test_validation_issue_defaults_location_to_none() -> None:
    issue = ValidationIssue(severity=ValidationIssueSeverity.WARNING, message="a warning")

    assert issue.location is None


def test_validation_issue_holds_a_location_when_given() -> None:
    issue = ValidationIssue(
        severity=ValidationIssueSeverity.INFO, message="a note", location="/article/front"
    )

    assert issue.location == "/article/front"
