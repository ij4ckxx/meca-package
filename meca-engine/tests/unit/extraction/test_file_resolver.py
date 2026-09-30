"""Unit tests for meca_engine.extraction.file_resolver."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from meca_engine.config.schema import MediaTypeConfig
from meca_engine.exceptions import FileReferenceMissingError
from meca_engine.extraction.file_resolver import resolve_files
from meca_engine.logging_.structured_logger import StructuredLogger
from meca_engine.model.article import FileEntry
from meca_engine.model.warnings import WarningCategory, WarningSeverity

pytestmark = pytest.mark.unit

_MEDIA_TYPE_CONFIG = MediaTypeConfig(
    mappings={".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    unmapped_extension_policy="warn_and_default",
    unmapped_extension_default="application/octet-stream",
)


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def captured_logger(request: pytest.FixtureRequest) -> tuple[StructuredLogger, _ListHandler]:
    name = f"test.{request.node.name}"
    underlying = logging.getLogger(f"meca_engine.{name}")
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False
    return StructuredLogger(name), handler


def _entry(
    *,
    filename: str = "manuscript.docx",
    round_label: str = "Original",
    category: str = "manuscript",
    declared_path_hint: str | None = None,
) -> FileEntry:
    return FileEntry(
        round_label=round_label,
        category=category,
        original_filename=filename,
        declared_path_hint=(
            declared_path_hint
            if declared_path_hint is not None
            else f"/ppl/x/inputs/{round_label}/{filename}"
        ),
    )


def test_resolves_exact_filename_match(tmp_path: Path) -> None:
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "manuscript.docx").write_bytes(b"content")

    resolved, _, _ = resolve_files((_entry(),), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert len(resolved) == 1
    assert resolved[0].round_label == "Original"
    assert resolved[0].size_bytes == len(b"content")
    assert resolved[0].checksum


def test_resolves_media_type_from_config(tmp_path: Path) -> None:
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "manuscript.docx").write_bytes(b"x")

    resolved, _, _ = resolve_files((_entry(),), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert resolved[0].media_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_unmapped_extension_falls_back_to_default(tmp_path: Path) -> None:
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "data.xyz").write_bytes(b"x")

    resolved, _, _ = resolve_files(
        (_entry(filename="data.xyz"),), str(tmp_path), _MEDIA_TYPE_CONFIG
    )

    assert resolved[0].media_type == "application/octet-stream"


def test_stem_match_when_declared_name_lacks_extension(tmp_path: Path) -> None:
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "Cover letter.docx").write_bytes(b"x")

    resolved, _, _ = resolve_files(
        (_entry(filename="Cover letter", round_label="R1"),), str(tmp_path), _MEDIA_TYPE_CONFIG
    )

    assert resolved[0].staged_physical_path.endswith("Cover letter.docx")


def test_prefix_match_when_declared_name_omits_suffix(tmp_path: Path) -> None:
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "Authorship Form (1).pdf").write_bytes(b"x")

    resolved, _, _ = resolve_files(
        (_entry(filename="Authorship Form", round_label="R1"),), str(tmp_path), _MEDIA_TYPE_CONFIG
    )

    assert resolved[0].staged_physical_path.endswith("Authorship Form (1).pdf")


def test_prefix_tier_never_substitutes_an_unrelated_file_for_a_free_text_label(
    tmp_path: Path,
) -> None:
    """Regression (CS-2025-6808): a free-text declared label with an embedded, non-trailing
    "." (not a real "<name>.<ext>" pair) must not be misread as a 1-character stem that
    then prefix-matches an unrelated physical file."""
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "1.manuscript2.docx").write_bytes(b"unrelated file")

    resolved, warnings, skipped_indices = resolve_files(
        (
            _entry(
                filename="1.manuscript highlight yellow 1",
                round_label="Original",
                category="supplement",
            ),
        ),
        str(tmp_path),
        _MEDIA_TYPE_CONFIG,
    )

    assert resolved == ()
    assert skipped_indices == (0,)
    assert warnings[0].code == "BR011_FILE_ENTRY_SKIPPED"


def test_pseudo_extension_never_causes_a_wrong_figure_substitution(tmp_path: Path) -> None:
    """Regression (bsr-2025-3821, real production data): "Fig.3a-f" was wrongly resolved
    to the unrelated "Fig.2.tif" because ".3a-f" was accepted as a plausible extension,
    truncating the stem to "fig" — a false prefix match. The real "Fig.3a-f.tif" is
    genuinely absent from source; this must surface as skipped, not a wrong file."""
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "Fig.1a-f.tif").write_bytes(b"fig1")
    (round_dir / "Fig.2.tif").write_bytes(b"fig2")
    (round_dir / "Fig.3g-l.tif").write_bytes(b"fig3gl")

    resolved, warnings, skipped_indices = resolve_files(
        (_entry(filename="Fig.3a-f", round_label="Original", category="figure"),),
        str(tmp_path),
        _MEDIA_TYPE_CONFIG,
    )

    assert resolved == ()
    assert skipped_indices == (0,)
    assert warnings[0].code == "BR011_FILE_ENTRY_SKIPPED"


def test_prefix_match_still_works_for_a_genuinely_short_declared_stem(tmp_path: Path) -> None:
    """A real (non-degenerate) short declared name must still resolve via the prefix tier."""
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "Fig1_final.tiff").write_bytes(b"x")

    resolved, _, _ = resolve_files(
        (_entry(filename="Fig1", round_label="Original"),), str(tmp_path), _MEDIA_TYPE_CONFIG
    )

    assert resolved[0].staged_physical_path.endswith("Fig1_final.tiff")


def test_normalized_match_when_underscores_replace_spaces(tmp_path: Path) -> None:
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "Supplementary RNA sequencing data.xlsx").write_bytes(b"x")

    resolved, _, _ = resolve_files(
        (_entry(filename="Supplementary_RNA_sequencing_data.xlsx"),),
        str(tmp_path),
        _MEDIA_TYPE_CONFIG,
    )

    assert resolved[0].staged_physical_path.endswith("Supplementary RNA sequencing data.xlsx")


def test_normalized_match_when_declared_name_has_stray_whitespace(tmp_path: Path) -> None:
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "manuscript_clean.docx").write_bytes(b"x")

    resolved, _, _ = resolve_files(
        (_entry(filename="manuscript_clean .docx", round_label="R1"),),
        str(tmp_path),
        _MEDIA_TYPE_CONFIG,
    )

    assert resolved[0].staged_physical_path.endswith("manuscript_clean.docx")


def test_normalized_match_skips_non_matching_candidates_first(tmp_path: Path) -> None:
    """Covers the tier-4 loop continuing past a non-matching candidate to a later match."""
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "unrelated_file.txt").write_bytes(b"x")
    (round_dir / "manuscript_clean.docx").write_bytes(b"x")

    resolved, _, _ = resolve_files(
        (_entry(filename="manuscript_clean .docx", round_label="R1"),),
        str(tmp_path),
        _MEDIA_TYPE_CONFIG,
    )

    assert resolved[0].staged_physical_path.endswith("manuscript_clean.docx")


def test_falls_back_to_other_round_when_declared_round_hint_is_wrong(tmp_path: Path) -> None:
    # Real reference-package evidence: some declared paths use a
    # `_temp/<uuid>/<file>` staging form with no round segment at all —
    # the "round_label" ends up being a uuid, not a real round.
    actual_round_dir = tmp_path / "R1"
    actual_round_dir.mkdir()
    (actual_round_dir / "fig1.jpg").write_bytes(b"x")

    entry = _entry(filename="fig1.jpg", round_label="5862df88-uuid-not-a-round")

    resolved, _, _ = resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert resolved[0].round_label == "R1"


def test_missing_file_raises_file_reference_missing_error(tmp_path: Path) -> None:
    with pytest.raises(FileReferenceMissingError) as exc_info:
        resolve_files((_entry(),), str(tmp_path), _MEDIA_TYPE_CONFIG, article_id="cs-2025-0001")

    assert exc_info.value.article_id == "cs-2025-0001"


def test_empty_declared_name_never_matches_any_file_in_strict_mode(tmp_path: Path) -> None:
    """Milestone 9 correction: with fallback disabled, an empty declared
    name (an upstream extraction gap) must raise, never silently resolve
    to an arbitrary physical file — the prefix-match tier's
    `str.startswith("")` would otherwise match the first candidate
    found, regardless of round. Explicitly strict here to isolate this
    from the Milestone 10 fallback (see test_file_resolver_fallback.py)."""
    (tmp_path / "Original").mkdir()
    (tmp_path / "Original" / "manuscript.docx").write_bytes(b"x")

    with pytest.raises(FileReferenceMissingError):
        resolve_files(
            (_entry(filename=""),),
            str(tmp_path),
            _MEDIA_TYPE_CONFIG,
            allow_filename_fallback=False,
        )


def test_nonexistent_staged_root_raises_file_reference_missing_error(tmp_path: Path) -> None:
    with pytest.raises(FileReferenceMissingError):
        resolve_files((_entry(),), str(tmp_path / "does-not-exist"), _MEDIA_TYPE_CONFIG)


def test_empty_file_entries_returns_empty_tuple(tmp_path: Path) -> None:
    assert resolve_files((), str(tmp_path), _MEDIA_TYPE_CONFIG) == ((), (), ())


def test_logs_warning_per_unreferenced_physical_file(
    tmp_path: Path, captured_logger: tuple[StructuredLogger, _ListHandler]
) -> None:
    logger, handler = captured_logger
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "manuscript.docx").write_bytes(b"x")
    (round_dir / "unreferenced.docx").write_bytes(b"x")

    resolve_files((_entry(),), str(tmp_path), _MEDIA_TYPE_CONFIG, logger=logger)

    warnings = [r for r in handler.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1


def test_logs_completion_event(
    tmp_path: Path, captured_logger: tuple[StructuredLogger, _ListHandler]
) -> None:
    logger, handler = captured_logger
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "manuscript.docx").write_bytes(b"x")

    resolve_files((_entry(),), str(tmp_path), _MEDIA_TYPE_CONFIG, logger=logger)

    info_messages = [r.getMessage() for r in handler.records if r.levelno == logging.INFO]
    assert any("complete" in m for m in info_messages)


def test_matches_file_directly_under_staged_root_with_no_round_subdirectory(
    tmp_path: Path,
) -> None:
    (tmp_path / "manuscript.docx").write_bytes(b"x")

    resolved, _, _ = resolve_files((_entry(),), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert resolved[0].staged_physical_path.endswith("manuscript.docx")
    assert resolved[0].round_label == "Original"


def test_empty_entries_with_nonexistent_root_and_logger_does_not_raise(
    tmp_path: Path, captured_logger: tuple[StructuredLogger, _ListHandler]
) -> None:
    logger, _ = captured_logger

    resolved, _, _ = resolve_files((), str(tmp_path / "missing"), _MEDIA_TYPE_CONFIG, logger=logger)

    assert resolved == ()


# --- Milestone 10 (ADR-032): filename fallback from declared_path_hint -------


def test_missing_name_with_valid_path_derives_filename_and_resolves(tmp_path: Path) -> None:
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "A2B_Tables 1 and 2_revised.docx").write_bytes(b"x")
    entry = _entry(
        filename="",
        round_label="R1",
        category="tables",
        declared_path_hint="/ppl/cs/cs-2024-5238/inputs/R1/A2B_Tables 1 and 2_revised.docx",
    )

    resolved, warnings, _ = resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert len(resolved) == 1
    assert resolved[0].original_filename == "A2B_Tables 1 and 2_revised.docx"
    assert resolved[0].round_label == "R1"
    assert len(warnings) == 1


def test_derived_filename_matches_path_basename_exactly(tmp_path: Path) -> None:
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "report.pdf").write_bytes(b"x")
    entry = _entry(filename="", declared_path_hint="/_temp/uuid-1/report.pdf")

    resolved, _, _ = resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert resolved[0].original_filename == Path("/_temp/uuid-1/report.pdf").name == "report.pdf"


def test_missing_name_with_invalid_path_still_raises(tmp_path: Path) -> None:
    """A path with no usable basename (trailing separator) yields nothing to fall back to."""
    entry = _entry(filename="", declared_path_hint="/_temp/uuid-1/")

    with pytest.raises(FileReferenceMissingError):
        resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG)


def test_missing_name_with_no_path_still_raises(tmp_path: Path) -> None:
    entry = _entry(filename="", declared_path_hint="")

    with pytest.raises(FileReferenceMissingError):
        resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG)


def test_fallback_warning_has_expected_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "A2B_Tables 1 and 2_revised.docx").write_bytes(b"x")
    entry = _entry(
        filename="",
        round_label="R1",
        category="tables",
        declared_path_hint="/ppl/cs/cs-2024-5238/inputs/R1/A2B_Tables 1 and 2_revised.docx",
    )

    _, warnings, _ = resolve_files(
        (entry,), str(tmp_path), _MEDIA_TYPE_CONFIG, article_id="cs-2024-5238"
    )

    assert len(warnings) == 1
    warning = warnings[0]
    assert warning.code == "BR013_FALLBACK_FILENAME_FROM_PATH"
    assert warning.category is WarningCategory.SPECIFICATION_FALLBACK
    assert warning.severity is WarningSeverity.WARNING
    assert warning.rule_id == "BR-013"
    assert warning.article_id == "cs-2024-5238"
    context = warning.context_dict()
    assert context["round"] == "R1"
    assert context["category"] == "tables"
    assert context["derived_filename"] == "A2B_Tables 1 and 2_revised.docx"
    assert context["declared_path"] == entry.declared_path_hint


def test_original_file_entry_is_never_mutated_by_fallback(tmp_path: Path) -> None:
    """The ICAM's FileEntry keeps showing the name as missing — fallback is generation-only."""
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "report.pdf").write_bytes(b"x")
    entry = _entry(filename="", round_label="R1", declared_path_hint="/_temp/uuid-1/report.pdf")

    resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert entry.original_filename == ""


def test_allow_filename_fallback_false_restores_strict_behavior(tmp_path: Path) -> None:
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "report.pdf").write_bytes(b"x")
    entry = _entry(filename="", round_label="R1", declared_path_hint="/_temp/uuid-1/report.pdf")

    with pytest.raises(FileReferenceMissingError):
        resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG, allow_filename_fallback=False)


def test_entries_with_a_real_name_never_produce_fallback_warnings(tmp_path: Path) -> None:
    """The fallback must never activate for entries that already resolve normally."""
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "manuscript.docx").write_bytes(b"content")

    _, warnings, _ = resolve_files((_entry(),), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert warnings == ()


def test_no_logger_produces_no_error(tmp_path: Path) -> None:
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "manuscript.docx").write_bytes(b"x")

    resolve_files((_entry(),), str(tmp_path), _MEDIA_TYPE_CONFIG)


# --- Milestone 11 (ADR-033): skip-and-continue recovery for non-manuscript entries ---


def test_missing_non_manuscript_file_is_skipped_not_raised(tmp_path: Path) -> None:
    """A missing supplementary file no longer discards the whole package (BR-011)."""
    entry = _entry(filename="Supp Fig 1.pdf", category="supplement", round_label="R1")

    resolved, warnings, skipped_indices = resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert resolved == ()
    assert skipped_indices == (0,)
    assert len(warnings) == 1
    assert warnings[0].code == "BR011_FILE_ENTRY_SKIPPED"
    assert warnings[0].is_recovery is True


def test_skipped_entry_with_no_identifying_fields_still_populates_affected_file(
    tmp_path: Path,
) -> None:
    """Regression (bst-2025-3095): a skip with no filename/path/round/category must
    still surface a real, non-fabricated identifier instead of `affected_file=None`."""
    entry = _entry(filename="", category="", round_label="", declared_path_hint="")

    _resolved, warnings, _skipped_indices = resolve_files(
        (entry,), str(tmp_path), _MEDIA_TYPE_CONFIG
    )

    assert len(warnings) == 1
    assert warnings[0].affected_file == "(unnamed file entry #1)"
    assert warnings[0].context_dict()["entry_index"] == "0"


def test_missing_manuscript_file_still_raises(tmp_path: Path) -> None:
    """The one category Milestone 11 keeps fatal: no manuscript, no package."""
    entry = _entry(filename="manuscript.docx", category="manuscript")

    with pytest.raises(FileReferenceMissingError):
        resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG)


def test_skipped_entry_alongside_a_resolved_entry_preserves_order(tmp_path: Path) -> None:
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "manuscript.docx").write_bytes(b"x")
    manuscript_entry = _entry(filename="manuscript.docx", category="manuscript")
    missing_entry = _entry(filename="missing.pdf", category="supplement")

    resolved, warnings, skipped_indices = resolve_files(
        (manuscript_entry, missing_entry), str(tmp_path), _MEDIA_TYPE_CONFIG
    )

    assert len(resolved) == 1
    assert resolved[0].original_filename == "manuscript.docx"
    assert skipped_indices == (1,)
    assert len(warnings) == 1


# --- Milestone 11 (ADR-033): tolerant-match tier fix + surfaced warning ---


def test_suffix_variant_with_extension_now_resolves(tmp_path: Path) -> None:
    """Regression test for the tier-3 bug fix (declared_stem, not declared_name).

    Real production evidence (bst-2025-3127, cs-2025-6619): a declared
    name *with* an extension failed to match a physical file carrying a
    disambiguating "(N)" suffix, because the old comparison checked the
    physical stem against the full declared name (still bearing its
    extension) instead of the declared stem.
    """
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "Cover Letter (2).pdf").write_bytes(b"x")
    entry = _entry(filename="Cover Letter.pdf", category="coverletter", round_label="R1")

    resolved, warnings, skipped_indices = resolve_files((entry,), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert skipped_indices == ()
    assert resolved[0].staged_physical_path.endswith("Cover Letter (2).pdf")
    assert any(w.code == "BR016_TOLERANT_FILE_MATCH" for w in warnings)


def test_exact_match_produces_no_tolerant_match_warning(tmp_path: Path) -> None:
    round_dir = tmp_path / "Original"
    round_dir.mkdir()
    (round_dir / "manuscript.docx").write_bytes(b"x")

    _, warnings, _ = resolve_files((_entry(),), str(tmp_path), _MEDIA_TYPE_CONFIG)

    assert not any(w.code == "BR016_TOLERANT_FILE_MATCH" for w in warnings)
