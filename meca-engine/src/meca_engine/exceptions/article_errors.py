"""Article-level exceptions — each stops only the article that raised it.

Per 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.3: "if the failure's root
cause would apply identically to every remaining article in the batch, it
is a BatchLevelError; if it is specific to one article's data or one
article's individual S3 object, it is an ArticleLevelError." Every
exception in this module must therefore always carry ``article_id``.

The retryable/non-retryable split within this module mirrors
12_LLD_03 §7.1-7.2 exactly:

- :class:`ArticleTransientError` and its subclasses are retryable
  (infrastructure-attributable failures).
- Every other class in this module is non-retryable by class default
  (data-quality/business-rule failures that would never succeed on a
  second attempt), with the sole documented exception of
  :class:`PackageAssemblyError`, whose retryability must be determined at
  the raise site from its inner cause.
"""

from __future__ import annotations

from meca_engine.exceptions.base import MecaEngineError


class ArticleLevelError(MecaEngineError):
    """Base class for every exception that stops only one article.

    Never raised directly — always raise one of the specific subclasses
    below. Batch processing must continue for every other article when
    a subclass of this error is raised for a given ``article_id``.
    """

    retryable = False


# --- Non-retryable: data-quality / business-rule failures ---


class SourceXmlMalformedError(ArticleLevelError):
    """An XML file is not well-formed, or safe parsing rejected its content.

    Raised by :mod:`meca_engine.extraction.xml_loader` (Milestone 3 — any
    XML file it is asked to load) and, later, by
    :mod:`meca_engine.extraction.kriyadocs_parser`
    (11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.2, Milestone 4) for
    Kriyadocs-specific content-shape failures on top of an
    already-well-formed document. Never retryable: the same bytes will
    fail to parse identically on every attempt.
    """


class ModelBuildError(ArticleLevelError):
    """The Internal Canonical Article Model could not be assembled.

    Raised by :class:`meca_engine.model.article.ArticleModelBuilder`
    (11_LLD_02... §4.1) when ``freeze()`` is called before every required
    field has been set, or when a field is set more than once. Indicates
    an extractor code defect, not a data-quality issue in the source.
    """


class RoundResolutionError(ArticleLevelError):
    """Submission-round ordering could not be resolved unambiguously.

    Raised by :mod:`meca_engine.extraction.round_resolver`
    (11_LLD_02... §4.4) when ``article-version/@vocab-identifier`` values
    are missing or conflicting. Per ADR-013, this must never be guessed.
    """


class FileReferenceMissingError(ArticleLevelError):
    """A custom-meta file entry has no matching physical file.

    Raised by :mod:`meca_engine.extraction.file_resolver`
    (11_LLD_02... §4.5; Business Rule Book BR-011).
    """


class ArticleTypeMappingError(ArticleLevelError):
    """A source ``display-channel`` value has no configured article-type mapping.

    Raised by :mod:`meca_engine.generators.article_xml.generator`
    (ADR-001). Never falls back to a guessed default silently.
    """


class LicenseMappingError(ArticleLevelError):
    """A source ``License Type`` value has no configured license template.

    Raised by :mod:`meca_engine.generators.article_xml.license_builder`
    (ADR-002). Never fabricates license text for an unmapped value.
    """


class MissingDoiError(ArticleLevelError):
    """The source ``article-id[@pub-id-type=doi]`` field is absent or empty.

    Raised by :mod:`meca_engine.generators.article_xml.doi_builder`
    (Business Rule Book BR-049/050).
    """


class DoiCollisionError(ArticleLevelError):
    """The generated DOI already exists in the DOI Registry.

    Raised when :class:`meca_engine.registry.doi_registry.DoiRegistry`
    returns a duplicate reservation result (ADR-015) — never silently
    skipped or auto-resolved. Classified as a ``FATAL_FAILURE`` (a
    source-data conflict, not an engine defect) and routed to the same
    ``failed/`` category every other fatal failure is
    (:mod:`meca_engine.service.router`); :mod:`meca_engine.recovery` is
    an unimplemented stub (no dedicated human-review queue exists today),
    so this is not separately escalated beyond that.
    """


class GeneratorError(ArticleLevelError):
    """Base class for every exception raised by the Generator Framework itself.

    Milestone 6A addition: groups framework-level generation failures
    (as opposed to the business-rule-specific leaf classes above, e.g.
    :class:`ArticleTypeMappingError`), the same way
    :class:`ArticleTransientError` groups retryable failures — so
    higher-layer code can catch "a generator framework failure" broadly
    without needing to know every current or future business-rule leaf
    class. Never raised directly.
    """

    retryable = False


class GeneratorInvariantError(GeneratorError):
    """A generator's invariant was violated by input that should already be valid.

    Named in 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7 (the
    ``RawXmlGenerator`` description) but not implemented until this
    milestone. Raised by :class:`meca_engine.generators.base.BaseGenerator`
    when a subclass's generation step raises an exception the framework
    does not otherwise recognize — since generator input (the ICAM) is
    already validated upstream, an unexpected failure here indicates a
    code defect in the generator itself, not a data-quality issue. Never
    retryable — the same defect will reproduce identically on any retry.
    """


class XmlSerializationError(GeneratorError):
    """An XML document could not be serialized to its final text/byte form.

    Raised by :mod:`meca_engine.generators.xml.builder` when document
    assembly succeeds but serialization fails (e.g. a value that cannot
    be encoded in the requested output encoding). Never retryable — the
    same document will fail identically on any retry.
    """


class ReviewDataIntegrityError(ArticleLevelError):
    """Reviewer/decision data extracted from the source is internally inconsistent.

    Raised by :mod:`meca_engine.generators.reviews_xml.generator`
    (11_LLD_02... §4.7), e.g. a recommendation with no reviewer identity.
    Typically Medium severity — may warn rather than block, per the
    Validation Engine's severity tiering (ADR-024).
    """


# --- Milestone 2 additions: Input & Staging Layer, discovery-time failures ---
# Justification for each new leaf class (per the current task's "do not
# introduce new exception categories without justification"): none of the
# Milestone 1 leaf classes above fit a purely structural/filesystem-level
# failure detected before any XML parsing occurs — every existing class is
# either about XML *content* (SourceXmlMalformedError), the ICAM
# (ModelBuildError/RoundResolutionError), or generation-time concerns that
# don't yet exist in this milestone. Each class below is a new *leaf*
# under the existing, unmodified ArticleLevelError/BatchLevelError
# categories — no new category is introduced.


class InvalidArticlePackageError(ArticleLevelError):
    """An article's folder structure does not match the expected shape.

    Raised by :mod:`meca_engine.input.discovery` when, e.g., zero or more
    than one root-level XML-named file is present, or no round subfolder
    exists at all (Business Rule Book BR-001/BR-002's structural half —
    NOT the content well-formedness check, which remains
    :class:`SourceXmlMalformedError`'s responsibility in
    :mod:`meca_engine.extraction`, deferred beyond this milestone). Never
    retryable: detected purely from directory/file listing, without
    opening any file, so a repeat attempt sees the identical structure.
    """


class DuplicateArticleError(ArticleLevelError):
    """The same article_id was discovered more than once in one batch scan.

    Raised by :mod:`meca_engine.input.discovery` (batch-scanner duplicate
    detection). Never retryable — the duplication is a property of the
    source listing itself, not a transient condition.
    """


class DuplicateFileError(ArticleLevelError):
    """Two files within the same submission round normalize to the same name.

    Raised by :mod:`meca_engine.input.discovery` /
    :mod:`meca_engine.input.staging` (Test Specification TC-047: "Duplicate
    filenames within the same round... flagged as a conflict, not silently
    overwritten"). Never retryable.
    """


class SourceUnavailableError(ArticleLevelError):
    """A source location or file could not be accessed at all.

    Raised by :mod:`meca_engine.input.readers` when a local path does not
    exist / is not accessible, or a remote (S3) key/prefix definitively
    does not exist (Test Specification TC-171: "Clean, specific 'source
    not found' error, article FAILED, no crash"); also raised by
    :mod:`meca_engine.extraction.xml_loader` (Milestone 3) when an
    already-staged XML file has gone missing or cannot be read. Distinct
    from :class:`S3ReadTransientError`: this class is for a definitive
    not-found/access-denied condition, where retrying the identical
    location will not help; a transient API failure (throttling, timeout)
    while reading a location that *does* exist is
    :class:`S3ReadTransientError` instead.
    """


# --- Retryable: infrastructure-attributable transient failures ---


class ArticleTransientError(ArticleLevelError):
    """Base class for retryable, infrastructure-attributable article failures.

    :mod:`meca_engine.retry` automatically retries subclasses of this
    error with exponential backoff up to the configured maximum
    (ADR-023). Never raise this base class directly — raise one of the
    specific subclasses below.
    """

    retryable = True


class S3ReadTransientError(ArticleTransientError):
    """A transient failure occurred reading an article's input from S3."""


class S3WriteTransientError(ArticleTransientError):
    """A transient failure occurred writing an article's output to S3."""


class PostWriteIntegrityError(ArticleTransientError):
    """A post-write checksum comparison did not match.

    Raised by :mod:`meca_engine.output.writer` (Test Specification TC-182).
    Treated as transient: triggers a re-write rather than a permanent
    failure, since the most common cause is transient corruption in
    transit, not a genuine data problem.
    """


class StagingIntegrityError(ArticleTransientError):
    """A checksum/size mismatch was detected while staging a file.

    Raised by :mod:`meca_engine.input.staging` when a file copied/
    downloaded from its source into the local staging workspace does not
    match on size, or its as-transferred checksum does not match the
    checksum re-computed by reading the file back off disk. The staging
    (input-side) sibling of :class:`PostWriteIntegrityError` (output
    side) — same reasoning: the most common cause is transient corruption
    in transit, so a re-copy/re-download is attempted rather than treating
    this as a permanent failure.
    """


class DoiRegistryUnavailableError(ArticleTransientError):
    """The DOI Registry backend was unreachable for this article's check.

    Escalated to :class:`meca_engine.exceptions.batch_errors.SystemicDependencyOutageError`
    by :mod:`meca_engine.recovery` if this recurs across many concurrently
    processed articles within a short window (12_LLD_03 §7.3).
    """


class CheckpointStoreUnavailableError(ArticleTransientError):
    """The Checkpoint Store backend was unreachable for this article's transition.

    Escalated to :class:`meca_engine.exceptions.batch_errors.SystemicDependencyOutageError`
    under the same recurrence policy as :class:`DoiRegistryUnavailableError`.
    """


# --- Dual-natured: retryability determined at the raise site ---


class PackageAssemblyError(ArticleLevelError):
    """Package assembly failed; retryability depends on the inner cause.

    Per 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.2, this is the one
    exception in the hierarchy that is not statically transient or
    permanent by class: a disk-full condition is transient, while a
    genuine filename collision (Test Specification TC-047/TC-179) is not.
    Callers MUST always pass ``retryable`` explicitly — there is no class
    default — so that this classification decision is never accidentally
    skipped.
    """

    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        article_id: str | None = None,
        stage: str = "",
        rule_id: str | None = None,
        inner_cause: Exception | None = None,
    ) -> None:
        """Initialize a PackageAssemblyError with a mandatory retryable flag.

        Args:
            message: Human-readable description of the failure.
            retryable: Whether this specific failure instance should be
                automatically retried. Mandatory — see class docstring.
            article_id: The article this failure pertains to.
            stage: Dotted package.module path of the raising component.
            rule_id: The Business Rule Book identifier, when applicable.
            inner_cause: The original underlying exception.
        """
        super().__init__(
            message,
            article_id=article_id,
            stage=stage,
            rule_id=rule_id,
            inner_cause=inner_cause,
            retryable=retryable,
        )
