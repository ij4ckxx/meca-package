"""Generator Context — every dependency a generator is allowed to read.

Milestone 6A (Generator Framework). The single object
:class:`~meca_engine.generators.base.BaseGenerator.generate` passes to
every generator's implementation — the *only* way a generator reaches the
ICAM, configuration, logging, or diagnostics. A generator that needs
something not on this object has no other route to get it (no generator
may import :mod:`meca_engine.extraction` or reach into a file path/S3
client directly — see :mod:`meca_engine.generators.base`'s docstring).

**Milestone 9 exception, scoped to `raw_xml` only**: `source_xml_bytes`
carries the original source XML verbatim, for the XSLT-based raw.xml
transform (`generators.raw_xml.xslt_transform`), which needs to operate
on real source markup rather than the ICAM. This is a deliberate,
documented exception to the "ICAM is the only route to article data"
rule above — see `generators/base.py`'s own docstring note. Every other
generator must continue to ignore this field entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meca_engine.config.schema import (
        FeatureFlagsConfig,
        JournalConfig,
        PublisherConfig,
        RuntimeConfig,
    )
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.model.article import ArticleModel


@dataclass(frozen=True)
class GeneratorContext:
    """Everything one generator invocation needs, and nothing more.

    Attributes:
        model: The frozen ICAM for this article. Read-only by
            construction (every ICAM type is an immutable frozen
            dataclass) — a generator cannot modify it even by accident.
        runtime_config: Operational runtime settings (12_LLD_03 §5.7).
        journal_config: This article's journal configuration.
        publisher_config: This article's publisher configuration.
        feature_flags: Behavioral toggles (12_LLD_03 §5.8).
        logger: The structured logger every generation step logs through.
        diagnostics: The shared, per-run diagnostics collector — every
            generator invoked for this article's generation pass appends
            to the same collector, so the final diagnostics list spans
            the whole run, not just one generator.
        source_xml_bytes: The original source XML, verbatim — ``None``
            for every generator except the XSLT-based raw.xml path (see
            module docstring). Defaults to ``None`` so existing
            construction sites are unaffected.
    """

    model: ArticleModel
    runtime_config: RuntimeConfig
    journal_config: JournalConfig
    publisher_config: PublisherConfig
    feature_flags: FeatureFlagsConfig
    logger: StructuredLogger
    diagnostics: DiagnosticsCollector
    source_xml_bytes: bytes | None = None
