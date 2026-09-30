"""Base Generator — Generator Framework (Milestone 6A).

Every one of the 5 future XML generators
(`raw_xml`/`article_xml`/`manifest_xml`/`reviews_xml`/`transfer_xml`)
inherits from :class:`BaseGenerator`. Extends
11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7's minimal
``generators.base.Generator[T]`` interface (``generate(model, config) ->
T``) with the lifecycle infrastructure the current milestone's task asks
for — logging, timing, diagnostics, and uniform error handling — while
keeping the one contract every generator must satisfy exactly as small
as before: implement :meth:`_generate`, nothing else.

**One-way dependency, enforced by what this module imports**: this
module (and everything under :mod:`meca_engine.generators`) imports only
from :mod:`meca_engine.model` (the ICAM), :mod:`meca_engine.config`, and
:mod:`meca_engine.logging_`/:mod:`meca_engine.exceptions` — never from
:mod:`meca_engine.extraction` or :mod:`meca_engine.transform`. A concrete
generator subclass must follow the same rule: the ICAM
(:class:`~meca_engine.model.article.ArticleModel`, reached only through
:class:`~meca_engine.generators.context.GeneratorContext`) is the *only*
route to article data. No generator may parse XML, read a staged file
path, or call an S3 client directly.

**Milestone 9 exception, scoped to `raw_xml` only**: the XSLT-based
raw.xml transform (`generators.raw_xml.xslt_transform`) reads
`GeneratorContext.source_xml_bytes` (the original source XML, verbatim)
instead of the ICAM, because the transform it applies is a structural
XSLT cleanup of real source markup, not a field-by-field ICAM mapping.
This is a deliberate, narrow, documented exception — every other
generator (`article_xml`, `manifest_xml`, `reviews_xml`, `transfer_xml`)
still follows the ICAM-only rule unchanged.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from meca_engine.exceptions import GeneratorInvariantError, MecaEngineError
from meca_engine.generators.result import GenerationResult

if TYPE_CHECKING:
    from meca_engine.generators.context import GeneratorContext

T = TypeVar("T")

_STAGE_PREFIX = "generators"


class BaseGenerator(ABC, Generic[T]):  # noqa: UP046 — PEP 695 syntax needs Python 3.12 at runtime
    """Shared lifecycle every XML generator inherits.

    Stateless by contract: a concrete subclass must hold no mutable
    instance state (the ICAM is frozen and configuration is read-only, so
    nothing about a single instance should ever need to change between
    calls) — this is what makes one instance safely reusable across many
    articles, including under future parallel execution (item 12).

    Concrete subclasses implement :meth:`_generate` only;
    :meth:`generate` (this class's one public method) wraps it with
    logging, timing, and error classification identically for every
    generator, so no generator can silently skip a lifecycle step.
    """

    @property
    @abstractmethod
    def generator_name(self) -> str:
        """This generator's short, stable name (e.g. ``"raw_xml"``).

        Used as the logging ``stage`` value, the diagnostics
        ``generator_name`` field, and the result's own
        :attr:`~meca_engine.generators.result.GenerationResult.generator_name`
        — one name, one source of truth, never re-derived differently in
        three places.
        """

    @abstractmethod
    def _generate(self, context: GeneratorContext) -> T:
        """Build and return this generator's output document.

        Subclasses implement business-rule/XML-mapping logic here —
        deliberately out of this milestone's scope, so every concrete
        generator's body is still a stub (``raise NotImplementedError``)
        until its own approved milestone. Must not catch
        :class:`~meca_engine.exceptions.MecaEngineError`; let it
        propagate to :meth:`generate`, which classifies it once, in one
        place.

        Args:
            context: Every dependency this generation needs.

        Returns:
            The generator-specific output-document value.
        """

    def generate(self, context: GeneratorContext) -> GenerationResult[T]:
        """Run this generator's full lifecycle for one article.

        Logs a start and completion event, times the call, and
        classifies any unexpected exception into
        :class:`~meca_engine.exceptions.GeneratorInvariantError` — the
        one public entry point every caller (eventually, the
        Orchestrator) uses; a concrete generator is never called any
        other way.

        Args:
            context: Every dependency this generation needs.

        Returns:
            The completed :class:`~meca_engine.generators.result.GenerationResult`.

        Raises:
            GeneratorError: Propagated unchanged if :meth:`_generate`
                itself raised one (already correctly classified).
            MecaEngineError: Propagated unchanged if :meth:`_generate`
                raised any other already-classified engine exception
                (e.g. a lower-layer :class:`~meca_engine.exceptions.ModelBuildError`
                surfacing through a generator that happened to trigger it).
            GeneratorInvariantError: Raised (wrapping the original as
                ``inner_cause``) if :meth:`_generate` raised anything
                else — an unclassified failure indicates a code defect,
                not a data-quality issue, since the ICAM is already
                validated by the time any generator runs.
        """
        name = self.generator_name
        stage = f"{_STAGE_PREFIX}.{name}"
        article_id = context.model.identity.article_id
        logger = context.logger

        logger.info(f"Generator '{name}' started", stage=stage, context={"article_id": article_id})
        start = time.perf_counter()
        try:
            document = self._generate(context)
        except MecaEngineError:
            raise
        except Exception as exc:
            raise GeneratorInvariantError(
                f"Generator '{name}' failed with an unexpected error: {exc}",
                article_id=article_id,
                stage=stage,
                inner_cause=exc,
            ) from exc
        duration_ms = (time.perf_counter() - start) * 1000.0

        logger.performance(
            f"Generator '{name}' completed in {duration_ms:.2f}ms",
            duration_ms=duration_ms,
            stage=stage,
            context={"article_id": article_id},
        )
        logger.info(
            f"Generator '{name}' completed", stage=stage, context={"article_id": article_id}
        )
        return GenerationResult(
            document=document,
            generator_name=name,
            article_id=article_id,
            duration_ms=duration_ms,
            diagnostics=context.diagnostics.diagnostics,
        )
