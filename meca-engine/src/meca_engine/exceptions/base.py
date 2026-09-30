"""Root of the engine's custom exception hierarchy.

See 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7 for the full hierarchy diagram
and the retryable/non-retryable and article-level/batch-level classification
rationale. Every exception raised anywhere in the engine must be a subclass
of :class:`MecaEngineError` — never a bare stdlib exception — so that
:mod:`meca_engine.retry` and :mod:`meca_engine.recovery` can classify and
route failures without inspecting exception messages.
"""

from __future__ import annotations


class MecaEngineError(Exception):
    """Base class for every exception raised by the MECA engine.

    Never raised directly — always raise a specific subclass from
    :mod:`meca_engine.exceptions.article_errors` or
    :mod:`meca_engine.exceptions.batch_errors`.

    Every instance carries the fields specified in
    12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.4, so that the exception itself
    is sufficient to log, classify, and route the failure without any
    further inspection of its message text.

    Attributes:
        retryable: Class-level default indicating whether this error class
            is, in general, safe to automatically retry
            (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.2). Individual
            subclasses override this at the class level; ``PackageAssemblyError``
            is the sole exception requiring a per-instance override, since its
            retryability depends on its inner cause rather than its class.
            Deliberately a plain (non-``ClassVar``) attribute so that
            per-instance overrides remain a normal, type-checked assignment
            rather than a ``ClassVar`` violation.
    """

    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        article_id: str | None = None,
        stage: str = "",
        rule_id: str | None = None,
        inner_cause: Exception | None = None,
        retryable: bool | None = None,
    ) -> None:
        """Initialize a MecaEngineError.

        Args:
            message: Human-readable description of the failure.
            article_id: The article this failure pertains to, or ``None``
                for a batch-level failure that is not tied to one article.
            stage: Dotted package.module path of the component that raised
                this error (12_LLD_03 §6.2's ``stage`` field convention).
            rule_id: The Business Rule Book identifier (e.g. ``"BR-058"``)
                this failure relates to, when applicable.
            inner_cause: The original underlying exception, if this error
                wraps one, preserved for logging (never swallowed silently).
            retryable: Per-instance override of the class-level
                :attr:`retryable` default. Reserved for exception classes
                whose retryability cannot be determined statically (see
                ``PackageAssemblyError``); every other subclass should leave
                this as ``None`` and rely on the class default.
        """
        super().__init__(message)
        self.message = message
        self.article_id = article_id
        self.stage = stage
        self.rule_id = rule_id
        self.inner_cause = inner_cause
        if retryable is not None:
            self.retryable = retryable

    def __repr__(self) -> str:
        """Return an unambiguous, log-friendly representation."""
        return (
            f"{type(self).__name__}(message={self.message!r}, "
            f"article_id={self.article_id!r}, stage={self.stage!r}, "
            f"rule_id={self.rule_id!r}, retryable={self.retryable!r})"
        )
