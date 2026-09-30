"""Unit tests for meca_engine.exceptions.article_errors.

Verifies the retryable/non-retryable classification from
12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.1-7.2 for every concrete
exception class.
"""

from __future__ import annotations

import pytest

from meca_engine.exceptions.article_errors import (
    ArticleLevelError,
    ArticleTransientError,
    ArticleTypeMappingError,
    CheckpointStoreUnavailableError,
    DoiCollisionError,
    DoiRegistryUnavailableError,
    FileReferenceMissingError,
    GeneratorError,
    GeneratorInvariantError,
    LicenseMappingError,
    MissingDoiError,
    ModelBuildError,
    PackageAssemblyError,
    PostWriteIntegrityError,
    ReviewDataIntegrityError,
    RoundResolutionError,
    S3ReadTransientError,
    S3WriteTransientError,
    SourceXmlMalformedError,
    XmlSerializationError,
)

pytestmark = pytest.mark.unit

NON_RETRYABLE_CLASSES = (
    SourceXmlMalformedError,
    ModelBuildError,
    RoundResolutionError,
    FileReferenceMissingError,
    ArticleTypeMappingError,
    LicenseMappingError,
    MissingDoiError,
    DoiCollisionError,
    ReviewDataIntegrityError,
    GeneratorInvariantError,
    XmlSerializationError,
)

RETRYABLE_CLASSES = (
    S3ReadTransientError,
    S3WriteTransientError,
    PostWriteIntegrityError,
    DoiRegistryUnavailableError,
    CheckpointStoreUnavailableError,
)


@pytest.mark.parametrize("error_class", NON_RETRYABLE_CLASSES)
def test_non_retryable_classes_default_to_not_retryable(
    error_class: type[ArticleLevelError],
) -> None:
    error = error_class("failure", article_id="cs-2025-8827")

    assert error.retryable is False
    assert isinstance(error, ArticleLevelError)


@pytest.mark.parametrize("error_class", RETRYABLE_CLASSES)
def test_transient_classes_default_to_retryable(
    error_class: type[ArticleTransientError],
) -> None:
    error = error_class("transient failure", article_id="cs-2025-8827")

    assert error.retryable is True
    assert isinstance(error, ArticleTransientError)
    assert isinstance(error, ArticleLevelError)


@pytest.mark.parametrize("error_class", [GeneratorInvariantError, XmlSerializationError])
def test_generator_framework_errors_are_generator_errors(
    error_class: type[GeneratorError],
) -> None:
    error = error_class("generation failed", article_id="cs-2025-8827")

    assert isinstance(error, GeneratorError)
    assert isinstance(error, ArticleLevelError)


def test_every_article_level_error_requires_no_mandatory_article_id_argument() -> None:
    # article_id is optional at the type level for flexibility, but every
    # real call site is expected to supply it — this test documents the
    # class-level contract, not a runtime enforcement (12_LLD_03 §7.3).
    error = SourceXmlMalformedError("malformed")
    assert error.article_id is None


def test_package_assembly_error_requires_explicit_retryable_flag() -> None:
    with pytest.raises(TypeError):
        PackageAssemblyError("assembly failed")  # type: ignore[call-arg]


def test_package_assembly_error_retryable_true_for_transient_cause() -> None:
    disk_full = OSError("No space left on device")

    error = PackageAssemblyError(
        "could not stage package",
        retryable=True,
        article_id="cs-2025-8827",
        inner_cause=disk_full,
    )

    assert error.retryable is True
    assert error.inner_cause is disk_full


def test_package_assembly_error_retryable_false_for_permanent_cause() -> None:
    collision = ValueError("filename collision")

    error = PackageAssemblyError(
        "could not stage package",
        retryable=False,
        article_id="cs-2025-8827",
        inner_cause=collision,
    )

    assert error.retryable is False
