"""Unit tests for meca_engine.model.warnings."""

from __future__ import annotations

import pytest

from meca_engine.model.warnings import (
    ConfidenceLevel,
    EngineWarning,
    FindingOrigin,
    WarningCategory,
    WarningSeverity,
)

pytestmark = pytest.mark.unit


def test_engine_warning_construction_and_field_access() -> None:
    warning = EngineWarning(
        code="BR013_FALLBACK_FILENAME_FROM_PATH",
        category=WarningCategory.SPECIFICATION_FALLBACK,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id="BR-013",
        recovery_rule_id="RR-001",
        confidence=ConfidenceLevel.HIGH,
        message="Original filename missing.",
        article_id="cs-2024-5238",
        suggested_action="Confirm the derived filename is correct.",
        is_recovery=True,
        affected_file="A2B_Tables 1 and 2_revised.docx",
        context=(("round", "R1"), ("category", "tables")),
    )

    assert warning.code == "BR013_FALLBACK_FILENAME_FROM_PATH"
    assert warning.category is WarningCategory.SPECIFICATION_FALLBACK
    assert warning.severity is WarningSeverity.WARNING
    assert warning.origin is FindingOrigin.SOURCE_DATA_ISSUE
    assert warning.rule_id == "BR-013"
    assert warning.recovery_rule_id == "RR-001"
    assert warning.confidence is ConfidenceLevel.HIGH
    assert warning.article_id == "cs-2024-5238"
    assert warning.suggested_action == "Confirm the derived filename is correct."
    assert warning.is_recovery is True
    assert warning.affected_file == "A2B_Tables 1 and 2_revised.docx"
    assert warning.context == (("round", "R1"), ("category", "tables"))
    assert warning.context_dict() == {"round": "R1", "category": "tables"}


def _minimal_warning(**overrides: object) -> EngineWarning:
    defaults: dict[str, object] = dict(
        code="X",
        category=WarningCategory.BUSINESS_RULE_WARNING,
        severity=WarningSeverity.INFO,
        origin=FindingOrigin.INFORMATIONAL,
        rule_id=None,
        recovery_rule_id=None,
        confidence=ConfidenceLevel.MEDIUM,
        message="m",
        article_id=None,
        suggested_action=None,
    )
    defaults.update(overrides)
    return EngineWarning(**defaults)  # type: ignore[arg-type]


def test_engine_warning_context_defaults_to_empty_tuple() -> None:
    warning = _minimal_warning()

    assert warning.context == ()
    assert warning.context_dict() == {}


def test_engine_warning_is_recovery_defaults_to_false() -> None:
    warning = _minimal_warning()

    assert warning.is_recovery is False


def test_engine_warning_affected_file_defaults_to_none() -> None:
    warning = _minimal_warning()

    assert warning.affected_file is None


def test_engine_warning_is_hashable_with_a_populated_context() -> None:
    """`ArticleModel` (which carries these) must stay hashable — a dict-valued
    context field would silently break that whenever a warning existed."""
    warning = _minimal_warning(context=(("k", "v"),))

    hash(warning)  # must not raise


def test_engine_warning_is_frozen() -> None:
    warning = _minimal_warning(category=WarningCategory.SOURCE_DATA_INCONSISTENCY)

    with pytest.raises(AttributeError):
        warning.code = "Y"  # type: ignore[misc]


@pytest.mark.parametrize(
    "category",
    [
        WarningCategory.MISSING_REQUIRED_METADATA,
        WarningCategory.SPECIFICATION_FALLBACK,
        WarningCategory.SOURCE_DATA_INCONSISTENCY,
        WarningCategory.BUSINESS_RULE_WARNING,
    ],
)
def test_every_warning_category_is_a_string_enum_member(category: WarningCategory) -> None:
    assert isinstance(category.value, str)


@pytest.mark.parametrize(
    "severity", [WarningSeverity.INFO, WarningSeverity.WARNING, WarningSeverity.ERROR]
)
def test_every_warning_severity_is_a_string_enum_member(severity: WarningSeverity) -> None:
    assert isinstance(severity.value, str)


@pytest.mark.parametrize(
    "origin",
    [
        FindingOrigin.ENGINE_DEFECT,
        FindingOrigin.SOURCE_DATA_ISSUE,
        FindingOrigin.BUSINESS_RULE_VIOLATION,
        FindingOrigin.CONFIGURATION_ISSUE,
        FindingOrigin.INFORMATIONAL,
    ],
)
def test_every_finding_origin_is_a_string_enum_member(origin: FindingOrigin) -> None:
    assert isinstance(origin.value, str)


@pytest.mark.parametrize(
    "confidence", [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]
)
def test_every_confidence_level_is_a_string_enum_member(confidence: ConfidenceLevel) -> None:
    assert isinstance(confidence.value, str)
