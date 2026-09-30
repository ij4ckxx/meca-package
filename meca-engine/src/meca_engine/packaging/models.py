"""Package Assembly data types — Milestone 7.

Named directly per the signatures in 05_SYSTEM_MODULE_BREAKDOWN.md Module 9
("Package Builder") and 13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §8.2
(``packaging.builder.build(...) -> StagedPackage``): none of these types
existed anywhere in the codebase before this milestone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.generators.article_xml.document import ArticleXmlDocument
    from meca_engine.generators.diagnostics import GeneratorDiagnostic
    from meca_engine.generators.manifest_xml.document import ManifestXmlDocument
    from meca_engine.generators.raw_xml.document import RawXmlDocument
    from meca_engine.generators.result import GenerationResult
    from meca_engine.generators.reviews_xml.document import ReviewsXmlDocument
    from meca_engine.generators.transfer_xml.document import TransferXmlDocument
    from meca_engine.model.warnings import EngineWarning


@unique
class PackageStatus(str, Enum):
    """The certification outcome of one assembled package (Milestone 12, ADR-034).

    Archive Migration Engine philosophy: "generate the MECA package
    whenever technically possible; never fabricate data." Only
    ``ENGINE_FAILURE``/``FATAL_FAILURE`` mean no package was produced at
    all; every other value is a successfully assembled package, with
    increasing amounts of engine intervention or remaining source
    deficiency:

    - ``CERTIFIED``: generated cleanly, nothing to report.
    - ``CERTIFIED_WITH_WARNINGS``: generated cleanly; advisory findings
      exist (e.g. a generator-layer observation) but the engine changed
      nothing to produce this package.
    - ``CERTIFIED_WITH_RECOVERY``: the engine applied one or more
      deterministic Recovery Rules (`model/recovery_rules.py`) — derived,
      matched, or deduplicated something — to make generation possible,
      without losing any declared content. Always accompanied by at
      least one warning with ``is_recovery=True``
      (:attr:`~meca_engine.model.warnings.EngineWarning.is_recovery`).
    - ``PARTIAL_CERTIFICATION``: the package was generated, but at least
      one declared file could not be recovered and was skipped (Recovery
      Rule RR-002) — real, declared content is absent from the package,
      even though what *was* generated is technically valid.
    - ``ENGINE_FAILURE``: generation did not complete because of a defect
      or incompleteness in the engine/its configuration (e.g. a missing
      namespace registration, a `ModelBuildError` invariant violation) —
      not the submitted data's fault.
    - ``FATAL_FAILURE``: generation did not complete because the source
      data itself made safe recovery impossible (e.g. unreadable/malformed
      XML, no manuscript file, no DOI available, a genuine round-ordering
      ambiguity) — continuing would produce a technically invalid package.

    :meth:`~meca_engine.packaging.builder.PackageBuilder.build` itself
    only ever assigns ``CERTIFIED``/``CERTIFIED_WITH_WARNINGS``/
    ``CERTIFIED_WITH_RECOVERY``/``PARTIAL_CERTIFICATION`` — a package that
    couldn't be assembled at all has no ``StagedPackage`` to hold a
    status; it raised an exception instead. A caller (e.g. the batch
    runner building a
    :class:`~meca_engine.packaging.conversion_report.ConversionReport`)
    classifies that raised exception into ``ENGINE_FAILURE``/``FATAL_FAILURE``.
    """

    CERTIFIED = "certified"
    CERTIFIED_WITH_WARNINGS = "certified_with_warnings"
    CERTIFIED_WITH_RECOVERY = "certified_with_recovery"
    PARTIAL_CERTIFICATION = "partial_certification"
    ENGINE_FAILURE = "engine_failure"
    FATAL_FAILURE = "fatal_failure"


@dataclass(frozen=True)
class GeneratedDocumentSet:
    """The 5 generation results produced by one complete generation pass.

    Every field is required: per BR-160 (Business Rule Book §J), a
    package must never be assembled from a partial set of documents — see
    :func:`meca_engine.packaging.builder.PackageBuilder.build`, which
    only constructs this type once all 5 generators have succeeded.
    """

    raw: GenerationResult[RawXmlDocument]
    article: GenerationResult[ArticleXmlDocument]
    manifest: GenerationResult[ManifestXmlDocument]
    reviews: GenerationResult[ReviewsXmlDocument]
    transfer: GenerationResult[TransferXmlDocument]


@dataclass(frozen=True)
class PackagedFile:
    """One physical asset to copy into the package, per manifest.xml's own href.

    Attributes:
        href: The relative path manifest.xml itself declares for this
            file (``files/<round_label>/<filename>``, per BR-082) — the
            authoritative destination path inside the package.
        source_path: Where to copy the file's bytes from
            (``ResolvedFile.staged_physical_path``).
        checksum: The already-computed SHA-256 checksum
            (``ResolvedFile.checksum``), reused rather than recomputed at
            generation time, and verified again after copying.
        size_bytes: The expected file size, for pre-copy sanity checks.
    """

    href: str
    source_path: Path
    checksum: str
    size_bytes: int


@dataclass(frozen=True)
class AssetCopyReport:
    """Summary of one :class:`~meca_engine.packaging.asset_copy.AssetCopyService` run.

    Attributes:
        copied: Every file successfully copied and checksum-verified.
        skipped: Files not copied because a destination already existed
            and ``overwrite_policy`` was ``"skip"``.
        duplicate_hrefs: Hrefs that appeared more than once in the
            requested copy plan (a manifest-generation-time defect, not
            an asset-copy-time one — surfaced here rather than silently
            overwritten).
    """

    copied: tuple[PackagedFile, ...]
    skipped: tuple[PackagedFile, ...]
    duplicate_hrefs: tuple[str, ...]


@dataclass(frozen=True)
class StagedPackage:
    """The complete, successfully assembled MECA package for one article.

    The return type of :meth:`meca_engine.packaging.builder.PackageBuilder.build`
    (13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §8.2, step 5) — the exact
    seam a future ``output.writer.publish(staged_package)`` (Module 10)
    consumes to publish to the operational/archival locations. Its
    existence at ``zip_path`` is the single source of truth that
    assembly succeeded: per ADR-017, this type is only ever constructed
    after every step (generation, DOI reservation, asset copy, zip
    write) has completed without error.

    Attributes:
        article_id: The article this package was assembled for.
        zip_path: Absolute path to the final, complete
            ``MECA_<ArticleID>.zip`` file.
        doi: The DOI reserved for this article (BR-154), or ``None`` if
            no DOI Registry was configured for this build.
        packaged_files: Every physical asset included in the package.
        xml_filenames: The 5 generated XML documents' filenames, as
            written at the package root.
        status: This package's certification outcome (Milestone 12,
            ADR-034) — computed from ``model.warnings`` and
            ``generator_diagnostics`` at build time; see
            :class:`PackageStatus` for the full decision order.
            Available without re-running validation.
        warnings: Every specification deviation the engine recovered
            from or flagged while building this package (e.g. a
            ``BR013_FALLBACK_FILENAME_FROM_PATH`` filename fallback) —
            copied verbatim from :attr:`~meca_engine.model.article.ArticleModel.warnings`
            so a batch runner/dashboard/JSON export can read them
            straight off this object.
        generator_diagnostics: Every non-fatal observation recorded by
            any of the 5 generators during this build (Milestone 6A) —
            copied from the :class:`~meca_engine.generators.diagnostics.DiagnosticsCollector`
            this build used, for the same reason ``warnings`` is copied
            here: a caller building a
            :class:`~meca_engine.packaging.conversion_report.ConversionReport`
            needs both without re-running generation.
    """

    article_id: str
    zip_path: Path
    doi: str | None
    packaged_files: tuple[PackagedFile, ...]
    xml_filenames: tuple[str, ...]
    status: PackageStatus = PackageStatus.CERTIFIED
    warnings: tuple[EngineWarning, ...] = field(default_factory=tuple)
    generator_diagnostics: tuple[GeneratorDiagnostic, ...] = field(default_factory=tuple)
