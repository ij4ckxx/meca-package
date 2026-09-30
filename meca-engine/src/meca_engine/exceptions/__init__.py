"""The engine's custom exception hierarchy (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7).

Re-exports every exception class so callers can do::

    from meca_engine.exceptions import SourceXmlMalformedError

rather than reaching into the ``article_errors`` / ``batch_errors``
submodules directly.
"""

from __future__ import annotations

from meca_engine.exceptions.article_errors import (
    ArticleLevelError,
    ArticleTransientError,
    ArticleTypeMappingError,
    CheckpointStoreUnavailableError,
    DoiCollisionError,
    DoiRegistryUnavailableError,
    DuplicateArticleError,
    DuplicateFileError,
    FileReferenceMissingError,
    GeneratorError,
    GeneratorInvariantError,
    InvalidArticlePackageError,
    LicenseMappingError,
    MissingDoiError,
    ModelBuildError,
    PackageAssemblyError,
    PostWriteIntegrityError,
    ReviewDataIntegrityError,
    RoundResolutionError,
    S3ReadTransientError,
    S3WriteTransientError,
    SourceUnavailableError,
    SourceXmlMalformedError,
    StagingIntegrityError,
    XmlSerializationError,
)
from meca_engine.exceptions.base import MecaEngineError
from meca_engine.exceptions.batch_errors import (
    BatchLevelError,
    CheckpointStoreFatalError,
    ConfigurationError,
    CredentialsRevokedError,
    DtdFilesMissingError,
    InsufficientDiskSpaceError,
    ProviderNotConfiguredError,
    SystemicDependencyOutageError,
)

__all__ = [
    "ArticleLevelError",
    "ArticleTransientError",
    "ArticleTypeMappingError",
    "BatchLevelError",
    "CheckpointStoreFatalError",
    "CheckpointStoreUnavailableError",
    "ConfigurationError",
    "CredentialsRevokedError",
    "DoiCollisionError",
    "DoiRegistryUnavailableError",
    "DtdFilesMissingError",
    "DuplicateArticleError",
    "DuplicateFileError",
    "FileReferenceMissingError",
    "GeneratorError",
    "GeneratorInvariantError",
    "InsufficientDiskSpaceError",
    "InvalidArticlePackageError",
    "LicenseMappingError",
    "MecaEngineError",
    "MissingDoiError",
    "ModelBuildError",
    "PackageAssemblyError",
    "PostWriteIntegrityError",
    "ProviderNotConfiguredError",
    "ReviewDataIntegrityError",
    "RoundResolutionError",
    "S3ReadTransientError",
    "S3WriteTransientError",
    "SourceUnavailableError",
    "SourceXmlMalformedError",
    "StagingIntegrityError",
    "SystemicDependencyOutageError",
    "XmlSerializationError",
]
