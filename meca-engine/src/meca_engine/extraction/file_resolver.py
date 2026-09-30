"""File resolution — Milestone 5B (11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.5).

Resolves each :class:`~meca_engine.model.article.FileEntry` (custom-meta's
declared file records, per BR-011/BR-014 the authoritative file manifest)
to a physical staged file, computing its checksum, size, and media type.
Takes a plain ``staged_root: str`` — never an ``input.models.StagedArticle``
— per the LLD's exact signature: `extraction`/`transform` do not depend on
`input` (10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.3's layering places
``input`` on an entirely separate branch from ``model ← extraction ←
transform``). ``staged_root`` is expected to contain one subdirectory per
round (Milestone 2's staging layout).

**Round label is resolved physically, not from the custom-meta hint —
evidence-based**: BR-016's own transformation logic already states the
declared ``path`` is "a hint only... actual file discovery is by
matching name against files physically present in the round folder."
Real reference-package data confirms why this matters here specifically:
some declared paths use a ``_temp/<uuid>/<file>`` staging-job form with
**no round segment at all** (the uuid is a per-file job id, not a round).
Trusting that hint as ``round_label`` would misreport a random uuid as a
round name. This resolver therefore searches each of ``staged_root``'s
immediate subdirectories (each one a round) for the matching physical
file and reports the *directory it was actually found under* as
:attr:`~meca_engine.model.article.ResolvedFile.round_label` — the
custom-meta-declared round (:attr:`~meca_engine.model.article.FileEntry.round_label`)
is tried first as a likely match, but every round is searched if it
doesn't resolve there.

**Filename matching tolerance, evidence-based**: BR-013 requires the
declared ``name`` field be used byte-identical as the *output* filename,
but real reference-package evidence shows the declared name does not
always exactly equal the physical file's name (an extension is
sometimes absent from the declared name, and one real sample's declared
name omits a disambiguating ``" (1)"`` suffix the actual upload carries).
Matching therefore tries, in order: an exact (case-insensitive) filename
match, a stem match (declared name equals the physical file's name minus
its extension), a prefix match (the physical file's name starts with the
declared name), then a whitespace/underscore-normalized match (collapses
runs of whitespace and treats ``"_"``/``" "`` as equivalent before
comparing — two more real-sample cases: one declared name carries a
stray extra space Kriyadocs itself introduced before the extension, and
one declared name uses underscores where the actual upload uses spaces)
— a generic, structural resolution tolerance, not a business-semantic
judgment, extending BR-016/017's existing leading-slash/path-style
tolerance to also cover this whitespace/extension/suffix variance. In
every case, the *output* filename BR-013 governs remains the declared
name, verbatim, untouched by this matching tolerance — only which
physical file's bytes/checksum/media-type get resolved is affected.

**Empty declared name is never a match (Milestone 9 correction)**: an
upstream extraction gap can leave :attr:`~meca_engine.model.article.FileEntry.original_filename`
as an empty string. None of the 4 tolerance tiers above may treat that
as "matches every file" (the prefix tier's ``str.startswith("")`` is
trivially true) — an empty declared name means the file is genuinely
unidentifiable and must raise :class:`~meca_engine.exceptions.FileReferenceMissingError`,
never silently resolve to an arbitrary physical file.

**Filename fallback from ``declared_path_hint`` (Milestone 10, ADR-032,
product decision — not a BR-013 correction)**: when ``original_filename``
is empty but ``declared_path_hint`` is not, and
``allow_filename_fallback`` is ``True`` (the default), a filename is
derived as ``Path(declared_path_hint).name`` *for generation purposes
only* and a ``BR013_FALLBACK_FILENAME_FROM_PATH`` warning is recorded.
The derived name is used solely to resolve/label the physical file for
this run's :class:`~meca_engine.model.article.ResolvedFile` output — the
``FileEntry`` the ICAM keeps (and returns to the caller unchanged) is
never mutated, so the fact that the name was originally missing is
never lost. If the derived name is itself empty (e.g. the path ends in
a separator) or ``declared_path_hint`` is also empty, or the flag is
``False``, this falls through unchanged to the empty-name rejection
above — recovery is only ever attempted when it can succeed safely.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from meca_engine.exceptions import FileReferenceMissingError
from meca_engine.model.article import ResolvedFile
from meca_engine.model.recovery_rules import (
    RR_001_FILENAME_FROM_PATH,
    RR_002_MISSING_FILE_SKIPPED,
    RR_004_TOLERANT_FILE_MATCH,
)
from meca_engine.model.warnings import (
    ConfidenceLevel,
    EngineWarning,
    FindingOrigin,
    WarningCategory,
    WarningSeverity,
)
from meca_engine.utils.hashing import compute_file_checksum
from meca_engine.utils.media_types import resolve_media_type

if TYPE_CHECKING:
    from meca_engine.config.schema import MediaTypeConfig
    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.model.article import FileEntry

_STAGE = "extraction.file_resolver"
_FALLBACK_WARNING_CODE = "BR013_FALLBACK_FILENAME_FROM_PATH"
_SKIPPED_ENTRY_WARNING_CODE = "BR011_FILE_ENTRY_SKIPPED"
_TOLERANT_MATCH_WARNING_CODE = "BR016_TOLERANT_FILE_MATCH"

# The one category whose absence makes the package meaningless — never
# skipped, always fatal (Milestone 11: "always generate whenever
# technically possible" stops short of publishing an empty shell).
_MANUSCRIPT_CATEGORY = "manuscript"


def _derive_fallback_filename(entry: FileEntry) -> str | None:
    """Derive a filename from ``declared_path_hint``, or ``None`` if none is usable."""
    if entry.original_filename or not entry.declared_path_hint:
        return None
    derived = Path(entry.declared_path_hint).name
    return derived or None


def _build_fallback_warning(
    entry: FileEntry, derived_filename: str, article_id: str | None
) -> EngineWarning:
    return EngineWarning(
        code=_FALLBACK_WARNING_CODE,
        category=WarningCategory.SPECIFICATION_FALLBACK,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id="BR-013",
        recovery_rule_id=RR_001_FILENAME_FROM_PATH.rule_id,
        confidence=ConfidenceLevel.HIGH,
        message=(
            f"Original filename missing. Filename derived from declared_path_hint "
            f"({RR_001_FILENAME_FROM_PATH.rule_id}). Package generated successfully "
            "using fallback logic."
        ),
        article_id=article_id,
        suggested_action=(
            "Confirm the derived filename is correct; source metadata should be "
            "corrected upstream so this fallback is no longer needed."
        ),
        is_recovery=True,
        affected_file=derived_filename,
        context=(
            ("round", entry.round_label),
            ("category", entry.category),
            ("derived_filename", derived_filename),
            ("declared_path", entry.declared_path_hint),
        ),
    )


def _build_skipped_entry_warning(
    entry: FileEntry, article_id: str | None, index: int
) -> EngineWarning:
    """BR-011 (Milestone 11): a non-manuscript file entry with no matching physical file.

    "Always generate whenever technically possible" — a single missing
    supplementary/administrative file is no longer allowed to discard an
    otherwise-complete package (see 07/08_Failure_Analysis in
    ``production_validation/`` for the evidence this recovery is based
    on: several such failures observed across real production packages,
    each losing 5-20 other correctly-resolved files over one gap). The
    entry is dropped from ``resolved_files``/the output package; it
    remains in ``custom_meta.file_entries`` untouched, so the fact it was
    declared — and never resolved — is never lost.

    Reporting finding (production-stabilization milestone, bst-2025-3095):
    when the source's own custom-meta record has no filename, path,
    round, or category at all, ``affected_file`` fell back to ``None``
    and this recovery silently disappeared from ``missing_files`` even
    though it genuinely fired. No filename is ever invented — but the
    entry's own position among the declared file entries is real,
    already-known data, so it is used as an honest, clearly-labeled
    identifier instead of leaving the entry unidentifiable.
    """
    identifier = (
        entry.original_filename or entry.declared_path_hint or f"(unnamed file entry #{index + 1})"
    )
    return EngineWarning(
        code=_SKIPPED_ENTRY_WARNING_CODE,
        category=WarningCategory.SOURCE_DATA_INCONSISTENCY,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id="BR-011",
        recovery_rule_id=RR_002_MISSING_FILE_SKIPPED.rule_id,
        confidence=ConfidenceLevel.MEDIUM,
        message=(
            f"No physical file found for {identifier} "
            f"(round={entry.round_label!r}, category={entry.category!r}); "
            f"entry skipped ({RR_002_MISSING_FILE_SKIPPED.rule_id}), package "
            "generated without it."
        ),
        article_id=article_id,
        suggested_action=(
            "Confirm whether this file was actually submitted; if so, source "
            "staging is missing it and should be corrected upstream."
        ),
        is_recovery=True,
        affected_file=identifier,
        context=(
            ("round", entry.round_label),
            ("category", entry.category),
            ("declared_filename", entry.original_filename),
            ("declared_path", entry.declared_path_hint),
            ("entry_index", str(index)),
        ),
    )


def _build_tolerant_match_warning(
    entry: FileEntry, physical_path: Path, match_tier: str, article_id: str | None
) -> EngineWarning:
    """BR-016/017: a file resolved via a non-exact tolerance tier, not a literal name match.

    This tolerance itself predates Milestone 11 — what's new is
    surfacing it as a structured warning rather than resolving silently
    (Milestone 11 requirement: "never recover silently").
    """
    return EngineWarning(
        code=_TOLERANT_MATCH_WARNING_CODE,
        category=WarningCategory.SPECIFICATION_FALLBACK,
        severity=WarningSeverity.INFO,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id="BR-016",
        recovery_rule_id=RR_004_TOLERANT_FILE_MATCH.rule_id,
        confidence=ConfidenceLevel.LOW,
        message=(
            f"File {entry.original_filename!r} matched physical file "
            f"{physical_path.name!r} via {match_tier!r} tolerance "
            f"({RR_004_TOLERANT_FILE_MATCH.rule_id}), not an exact name match."
        ),
        article_id=article_id,
        suggested_action="No action needed; verify the matched file is the intended one.",
        is_recovery=True,
        affected_file=physical_path.name,
        context=(
            ("round", entry.round_label),
            ("category", entry.category),
            ("declared_filename", entry.original_filename),
            ("matched_filename", physical_path.name),
            ("match_tier", match_tier),
        ),
    )


def resolve_files(
    file_entries: tuple[FileEntry, ...],
    staged_root: str,
    media_type_config: MediaTypeConfig,
    *,
    article_id: str | None = None,
    logger: StructuredLogger | None = None,
    allow_filename_fallback: bool = True,
) -> tuple[tuple[ResolvedFile, ...], tuple[EngineWarning, ...], tuple[int, ...]]:
    """Resolve every file entry to its physical staged file.

    Args:
        file_entries: The custom-meta-derived file entries to resolve
            (:attr:`~meca_engine.model.article.CustomMetaStore.file_entries`).
        staged_root: The root directory of this article's staged working
            folder (Milestone 2's staging output), expected to contain
            one subdirectory per round.
        media_type_config: Extension-to-MIME-type mapping (ADR-008/009).
        article_id: The article this resolution is for, attached to any
            raised :class:`FileReferenceMissingError` for context.
        logger: Optional structured logger; logs one WARNING per
            unreferenced physical file found (ADR-016) and a completion
            event carrying the resolved count.
        allow_filename_fallback: ADR-032 (Milestone 10) — when ``True``
            (the default), derive a missing filename from
            ``declared_path_hint`` and warn instead of raising, whenever
            that can be done safely. ``False`` restores the pre-Milestone-10
            strict behavior unconditionally.

    Returns:
        A ``(resolved_files, warnings, skipped_indices)`` triple.
        ``resolved_files`` has one
        :class:`~meca_engine.model.article.ResolvedFile` per
        *successfully resolved* input entry, in the same relative order
        (Milestone 11: no longer strictly one-per-input — see
        ``skipped_indices``); ``round_label`` reflects the staged
        subdirectory the file was actually found under, which may differ
        from the entry's declared, hint-only round label — see module
        docstring. ``warnings`` carries one
        :class:`~meca_engine.model.warnings.EngineWarning` per filename
        recovered via fallback, per entry skipped (BR-011, Milestone 11),
        and per file matched via a non-exact tolerance tier (BR-016).
        ``skipped_indices`` holds the position (into ``file_entries``) of
        every entry that could not be resolved and was skipped rather
        than raised — callers reconciling positional data (e.g.
        :mod:`meca_engine.transform.coordinator`) use this to know which
        original entries have no corresponding ``ResolvedFile``.

    Raises:
        FileReferenceMissingError: If the ``manuscript``-category entry
            has no matching physical file anywhere under ``staged_root``
            (BR-011) — the one category Milestone 11 still treats as
            fatal, since a package with no manuscript is not "the best
            possible package," it is an empty shell. Every other
            category is skipped with a warning instead (see
            ``skipped_indices`` above).
    """
    root = Path(staged_root)
    matched_physical_paths: set[Path] = set()
    resolved: list[ResolvedFile] = []
    warnings: list[EngineWarning] = []
    skipped_indices: list[int] = []

    for index, entry in enumerate(file_entries):
        effective_entry = entry
        if allow_filename_fallback:
            derived_filename = _derive_fallback_filename(entry)
            if derived_filename is not None:
                effective_entry = replace(entry, original_filename=derived_filename)
                warnings.append(_build_fallback_warning(entry, derived_filename, article_id))

        match = _find_physical_file(root, effective_entry)
        if match is None:
            if effective_entry.category == _MANUSCRIPT_CATEGORY:
                raise FileReferenceMissingError(
                    f"No physical file found for {entry.original_filename!r} "
                    f"(round={entry.round_label!r}, category={entry.category!r})",
                    article_id=article_id,
                    stage=_STAGE,
                    rule_id="BR-011",
                )
            skipped_indices.append(index)
            warnings.append(_build_skipped_entry_warning(entry, article_id, index))
            continue

        physical_path, resolved_round_label, match_tier = match
        matched_physical_paths.add(physical_path)
        if match_tier != "exact":
            warnings.append(
                _build_tolerant_match_warning(entry, physical_path, match_tier, article_id)
            )
        resolved.append(
            ResolvedFile(
                round_label=resolved_round_label,
                category=effective_entry.category,
                original_filename=effective_entry.original_filename,
                staged_physical_path=str(physical_path),
                checksum=compute_file_checksum(physical_path),
                size_bytes=physical_path.stat().st_size,
                media_type=resolve_media_type(physical_path.name, media_type_config)[0],
            )
        )

    if logger is not None:
        _log_unreferenced_physical_files(root, matched_physical_paths, article_id, logger)
        logger.info(
            "File resolution complete",
            stage=_STAGE,
            context={"article_id": article_id, "resolved_count": len(resolved)},
        )

    return tuple(resolved), tuple(warnings), tuple(skipped_indices)


def _round_directories(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        return ()
    return tuple(sorted((path for path in root.iterdir() if path.is_dir()), key=lambda p: p.name))


def _normalize_for_matching(text: str) -> str:
    return " ".join(text.replace("_", " ").split())


def _safe_declared_stem(declared_name: str) -> str:
    """``Path(declared_name).stem``, but only trust the split when the tail looks real.

    A free-text declared label that happens to contain one embedded,
    non-trailing ``.`` is not necessarily a real ``<name>.<ext>`` pair —
    ``Path.stem``'s naive last-dot split would otherwise truncate it to a
    near-meaningless stem, which the "prefix" tolerance tier below would
    then match against any physical file sharing that (now too-short or
    too-generic) prefix. Two confirmed real cases, not hypothetical:
    ``"1.manuscript highlight yellow 1"`` (stem "1", would prefix-match
    almost anything) and ``"Fig.3a-f"`` (stem "fig" once ".3a-f" was
    wrongly accepted as a plausible extension, which then prefix-matched
    the unrelated "Fig.2.tif" — silently packaging the wrong figure's
    bytes under the "Fig.3a-f" declaration, confirmed in a real generated
    package). A real extension is short, has no space, and — critically —
    is alphabetic (``.docx``, ``.tif``, ``.pdf``); ``.3a-f`` is not.
    Anything that doesn't look like a real extension is treated as having
    none at all, and the whole label is used as the stem.
    """
    suffix = Path(declared_name).suffix
    tail = suffix[1:]
    if suffix and tail and " " not in suffix and len(suffix) <= 6 and tail.isalpha():
        return Path(declared_name).stem
    return declared_name


def _match_in_directory(directory: Path, declared_name: str) -> tuple[Path, str] | None:
    if not declared_name:
        # An empty declared name (e.g. a custom-meta entry whose name
        # field could not be read at all) must never match — every one
        # of the tiers below would otherwise match unconditionally
        # (`str.startswith("")` is trivially true), silently resolving
        # to an arbitrary file. See FileEntry.original_filename's own
        # contract: an empty value means "unknown," never "any file."
        return None
    candidates = [path for path in directory.rglob("*") if path.is_file()]
    declared_stem = _safe_declared_stem(declared_name)

    for path in candidates:
        if path.name.lower() == declared_name:
            return path, "exact"
    for path in candidates:
        if path.stem.lower() == declared_name:
            return path, "stem"
    for path in candidates:
        # Milestone 11 fix: compare against the declared *stem*, not the
        # full declared name (which still carries its extension) — the
        # previous comparison could never match a physical file carrying
        # a disambiguating suffix (e.g. "Cover Letter (2).pdf" vs.
        # declared "Cover Letter.pdf"), the exact real-world case this
        # tier's own docstring above already claimed to cover. Confirmed
        # against 2 real production packages (see
        # production_validation/08_Failure_Analysis.md).
        if path.stem.lower().startswith(declared_stem):
            return path, "prefix"
    normalized_declared_stem = _normalize_for_matching(declared_stem)
    for path in candidates:
        if _normalize_for_matching(path.stem.lower()) == normalized_declared_stem:
            return path, "normalized"
    return None


def _find_physical_file(root: Path, entry: FileEntry) -> tuple[Path, str, str] | None:
    declared_name = entry.original_filename.lower()
    round_directories = _round_directories(root)

    ordered_directories = sorted(round_directories, key=lambda d: d.name != entry.round_label)
    for directory in ordered_directories:
        match = _match_in_directory(directory, declared_name)
        if match is not None:
            physical_path, tier = match
            return physical_path, directory.name, tier

    if root.is_dir():
        match = _match_in_directory(root, declared_name)
        if match is not None:
            physical_path, tier = match
            return physical_path, entry.round_label, tier
    return None


def _log_unreferenced_physical_files(
    root: Path,
    matched_physical_paths: set[Path],
    article_id: str | None,
    logger: StructuredLogger,
) -> None:
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        if path.is_file() and path not in matched_physical_paths:
            logger.warn(
                "Physical file has no matching custom-meta file entry",
                stage=_STAGE,
                context={"article_id": article_id, "path": str(path)},
            )
