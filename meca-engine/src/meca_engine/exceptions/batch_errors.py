"""Batch-level exceptions — each halts the entire run, not just one article.

Per 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.3, a failure belongs in this
module only if its root cause would apply identically to every remaining
article in the batch (e.g. invalid AWS credentials, a missing vendored DTD,
a config file that fails schema validation) — never for a failure specific
to one article's data.
"""

from __future__ import annotations

from meca_engine.exceptions.base import MecaEngineError


class BatchLevelError(MecaEngineError):
    """Base class for every exception that halts the entire batch run.

    Never raised directly — always raise one of the specific subclasses
    below. :class:`meca_engine.orchestrator.run_controller.RunController`
    must halt the run immediately on any subclass of this error, rather
    than allowing every remaining article to fail one-by-one with an
    identical, misleading per-article error.
    """

    retryable = False


class ConfigurationError(BatchLevelError):
    """Configuration failed schema validation, or required config is missing.

    Raised by :mod:`meca_engine.config.loader` at process startup
    (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §5.9). The engine must never
    begin processing articles against configuration it cannot fully trust.
    """


class ProviderNotConfiguredError(ConfigurationError):
    """A selected Input/Output Provider has no working implementation yet.

    Archive Migration Platform Phase 1 (ADR-030): the ``S3``/``SFTP``
    provider values are valid, schema-accepted configuration choices, but
    their concrete providers (:class:`~meca_engine.providers.input.S3InputProvider`,
    :class:`~meca_engine.providers.output.SftpOutputProvider`) are
    placeholders — raised the moment either is actually used, never at
    factory-selection time, so a batch never begins against a promise it
    cannot keep. A leaf of :class:`ConfigurationError` (not a standalone
    exception) so it flows through the same startup-failure handling as
    every other untrustworthy-configuration case.
    """


class DtdFilesMissingError(BatchLevelError):
    """A vendored DTD file required for validation is absent or corrupted.

    Raised during validation-engine startup (ADR-025; Risk Register
    RISK-023). Every article's DTD validation would be meaningless without
    the correct, version-pinned DTD files present.
    """


class CredentialsRevokedError(BatchLevelError):
    """AWS or database credentials were rejected as invalid or revoked mid-run.

    Every remaining article would fail identically, so the run halts
    rather than exhausting retry budgets article-by-article
    (Test Specification TC-174).
    """


class CheckpointStoreFatalError(BatchLevelError):
    """The Checkpoint Store backend has been unreachable beyond its grace period.

    Distinct from the per-article, retryable
    :class:`meca_engine.exceptions.article_errors.CheckpointStoreUnavailableError`:
    this is raised only after :mod:`meca_engine.recovery` determines the
    outage is sustained, not a one-off blip (12_LLD_03 §7.3).
    """


class SystemicDependencyOutageError(BatchLevelError):
    """A shared dependency outage is affecting many articles, not one.

    Raised by :mod:`meca_engine.recovery` when it observes the same
    transient dependency failure (DOI Registry or Checkpoint Store)
    recurring across many concurrently-processed articles within a short
    window, escalating what would otherwise be independent per-article
    retries into a single batch-wide pause
    (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.3).
    """


class InsufficientDiskSpaceError(BatchLevelError):
    """Available disk space is insufficient to safely continue staging.

    Raised by :mod:`meca_engine.input.staging` (Milestone 2 addition).
    Per 13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §9.4, disk space is
    deliberately treated as a batch-level, not per-article, concern: "a
    pre-flight disk-space check runs at worker startup... escalating to
    batch-pause behavior if free space drops below a safety threshold,
    rather than letting individual articles start failing with a
    confusing generic 'disk full' error one by one."
    """
