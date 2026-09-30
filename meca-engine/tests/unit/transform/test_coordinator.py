"""Unit tests for meca_engine.transform.coordinator."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import pytest

from meca_engine.config.schema import MediaTypeConfig
from meca_engine.exceptions import FileReferenceMissingError, RoundResolutionError
from meca_engine.extraction.metadata_models import (
    ArticleIdentifier,
    ArticleMetadata,
    AssetMetadata,
    ContributorMetadata,
    CrossReferenceMap,
    CustomMetadata,
    CustomMetaEntry,
    ExtractionBundle,
    JournalMetadata,
    WorkflowMetadata,
)
from meca_engine.extraction.parsed_model import (
    EncodingInfo,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
)
from meca_engine.logging_.structured_logger import StructuredLogger
from meca_engine.transform.coordinator import TransformationCoordinator

pytestmark = pytest.mark.unit

_ENCODING = EncodingInfo(declared_encoding=None, bom_encoding=None, effective_encoding="utf-8")
_MEDIA_TYPE_CONFIG = MediaTypeConfig(
    mappings={".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    unmapped_extension_policy="warn_and_default",
    unmapped_extension_default="application/octet-stream",
)

_VALID_ARTICLE_VERSION = ParsedElement(
    tag="article-version",
    namespace_uri=None,
    attributes=(
        ParsedAttribute("vocab-identifier", None, "snapshots/1_original/x.xml"),
        ParsedAttribute("article-version-type", None, "Original"),
    ),
)

_MALFORMED_ARTICLE_VERSION = ParsedElement(
    tag="article-version",
    namespace_uri=None,
    attributes=(ParsedAttribute("vocab-identifier", None, "not-a-valid-format"),),
)


def _document(*extra_children: ParsedElement) -> ParsedDocument:
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(ParsedElement(tag="p", namespace_uri=None, text="Body text"),),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(*extra_children, body))
    return ParsedDocument(source_path=Path("test.xml"), encoding=_ENCODING, doctype=None, root=root)


def _empty_bundle() -> ExtractionBundle:
    return ExtractionBundle(
        article=ArticleMetadata(
            identifiers=(ArticleIdentifier(id_type="doi", value="10.1/x"),),
            title="A Title",
        ),
        contributors=ContributorMetadata(),
        journal=JournalMetadata(journal_title="J", journal_id="EX"),
        workflow=WorkflowMetadata(),
        custom=CustomMetadata(),
        assets=AssetMetadata(),
        cross_references=CrossReferenceMap(),
    )


def test_builds_a_complete_model_without_a_logger(tmp_path: Path) -> None:
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="cs-2025-0001",
        source_object_key="cs-2025-0001/cs-2025-0001.xml",
        staged_root=str(tmp_path),
        parsed_document=_document(_VALID_ARTICLE_VERSION),
        extraction_bundle=_empty_bundle(),
    )

    assert model.identity.article_id == "cs-2025-0001"
    assert model.identity.doi_article_id_value == "10.1/x"
    assert model.journal_meta.journal_title == "J"
    assert model.article_meta.article_title == "A Title"
    assert len(model.rounds) == 1
    assert model.rounds[0].is_latest is True
    assert model.resolved_files == ()
    assert model.body_fragment.raw_xml_fragment.startswith("<body>")


def test_history_dates_and_counts_are_converted(tmp_path: Path) -> None:
    from meca_engine.extraction.metadata_models import DateRecord

    bundle = replace(
        _empty_bundle(),
        article=replace(
            _empty_bundle().article,
            history_dates=(
                DateRecord(date_type="received", year="2025", month="01", day="10"),
                DateRecord(date_type="accepted", year="2025", month="02", day=None),
            ),
            word_count="5000",
            ref_count="42",
            fig_count="3",
        ),
    )
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="x",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=bundle,
    )

    assert model.article_meta.history_dates.received is not None
    assert model.article_meta.history_dates.received.day == 10
    assert model.article_meta.history_dates.accepted is not None
    assert model.article_meta.history_dates.accepted.day == 1
    assert model.article_meta.history_dates.revision is None
    assert model.article_meta.counts.word_count == 5000
    assert model.article_meta.counts.ref_count == 42
    assert model.article_meta.counts.fig_count == 3


@pytest.mark.parametrize("observed_date_type", ["rev-recd", "revision", "revised"])
def test_revision_date_matches_every_observed_date_type(
    tmp_path: Path, observed_date_type: str
) -> None:
    """Corrective-milestone fix: real samples use "rev-recd"/"revision", never "revised" alone."""
    from meca_engine.extraction.metadata_models import DateRecord

    bundle = replace(
        _empty_bundle(),
        article=replace(
            _empty_bundle().article,
            history_dates=(
                DateRecord(date_type="received", year="2025", month="01", day="10"),
                DateRecord(date_type=observed_date_type, year="2025", month="02", day="15"),
                DateRecord(date_type="accepted", year="2025", month="03", day="01"),
            ),
        ),
    )
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="x",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=bundle,
    )

    assert model.article_meta.history_dates.revision is not None
    assert model.article_meta.history_dates.revision.day == 15


def test_unrecognized_revision_date_type_leaves_revision_none(tmp_path: Path) -> None:
    from meca_engine.extraction.metadata_models import DateRecord

    bundle = replace(
        _empty_bundle(),
        article=replace(
            _empty_bundle().article,
            history_dates=(
                DateRecord(date_type="some-other-type", year="2025", month="02", day="15"),
            ),
        ),
    )
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="x",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=bundle,
    )

    assert model.article_meta.history_dates.revision is None


def test_unparseable_date_component_leaves_date_none(tmp_path: Path) -> None:
    from meca_engine.extraction.metadata_models import DateRecord

    bundle = replace(
        _empty_bundle(),
        article=replace(
            _empty_bundle().article,
            history_dates=(
                DateRecord(date_type="received", year="not-a-year", month=None, day=None),
            ),
        ),
    )
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="x",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=bundle,
    )

    assert model.article_meta.history_dates.received is None


def test_out_of_range_date_component_leaves_date_none(tmp_path: Path) -> None:
    from meca_engine.extraction.metadata_models import DateRecord

    bundle = replace(
        _empty_bundle(),
        article=replace(
            _empty_bundle().article,
            history_dates=(DateRecord(date_type="received", year="2025", month="02", day="99"),),
        ),
    )
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="x",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=bundle,
    )

    assert model.article_meta.history_dates.received is None


def test_document_without_article_version_produces_empty_round_index(tmp_path: Path) -> None:
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="cs-2025-0001",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=_empty_bundle(),
    )

    assert model.rounds == ()


def test_malformed_article_version_recovers_instead_of_raising(tmp_path: Path) -> None:
    """Milestone 11: a single malformed <article-version> is skipped with a
    warning, not raised — only a genuine label conflict still raises."""
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="cs-2025-0001",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(_MALFORMED_ARTICLE_VERSION),
        extraction_bundle=_empty_bundle(),
    )

    assert model.rounds == ()
    assert any(w.code == "BR010_MALFORMED_ARTICLE_VERSION_SKIPPED" for w in model.warnings)


def test_raises_round_resolution_error_for_a_genuine_label_conflict(tmp_path: Path) -> None:
    conflicting_version = ParsedElement(
        tag="article-version",
        namespace_uri=None,
        attributes=(
            ParsedAttribute("vocab-identifier", None, "snapshots/1_x/a.xml"),
            ParsedAttribute("article-version-type", None, "R1"),
        ),
    )
    root = ParsedElement(
        tag="article", namespace_uri=None, children=(_VALID_ARTICLE_VERSION, conflicting_version)
    )
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    with pytest.raises(RoundResolutionError):
        coordinator.build_model(
            article_id="cs-2025-0001",
            source_object_key="x",
            staged_root=str(tmp_path),
            parsed_document=ParsedDocument(
                source_path=Path("test.xml"), encoding=_ENCODING, doctype=None, root=root
            ),
            extraction_bundle=_empty_bundle(),
        )


def test_raises_file_reference_missing_error_unchanged(tmp_path: Path) -> None:
    """The one category Milestone 11 keeps fatal: a manuscript that cannot be resolved."""
    from meca_engine.extraction.metadata_models import NamedContentField

    bundle = replace(
        _empty_bundle(),
        custom=CustomMetadata(
            entries=(
                CustomMetaEntry(
                    name=None,
                    value_text="",
                    attributes=(("specific-use", "form-files"),),
                    named_content=(NamedContentField(content_type="type", text="manuscript"),),
                ),
            )
        ),
    )
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    with pytest.raises(FileReferenceMissingError):
        coordinator.build_model(
            article_id="cs-2025-0001",
            source_object_key="x",
            staged_root=str(tmp_path),
            parsed_document=_document(_VALID_ARTICLE_VERSION),
            extraction_bundle=bundle,
        )


def test_non_manuscript_file_reference_missing_is_recovered(tmp_path: Path) -> None:
    """Milestone 11: a missing non-manuscript file entry no longer raises."""
    bundle = replace(
        _empty_bundle(),
        custom=CustomMetadata(
            entries=(
                CustomMetaEntry(
                    name=None,
                    value_text="",
                    attributes=(("specific-use", "form-files"),),
                ),
            )
        ),
    )
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="cs-2025-0001",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(_VALID_ARTICLE_VERSION),
        extraction_bundle=bundle,
    )

    assert model.resolved_files == ()
    assert any(w.code == "BR011_FILE_ENTRY_SKIPPED" for w in model.warnings)


def _missing_name_bundle() -> ExtractionBundle:
    from meca_engine.extraction.metadata_models import NamedContentField

    return replace(
        _empty_bundle(),
        custom=CustomMetadata(
            entries=(
                CustomMetaEntry(
                    name=None,
                    value_text="",
                    attributes=(("specific-use", "form-files"),),
                    named_content=(
                        NamedContentField(content_type="type", text="tables"),
                        NamedContentField(
                            content_type="path",
                            text="/ppl/cs/cs-2024-5238/inputs/R1/A2B_Tables 1 and 2_revised.docx",
                        ),
                    ),
                ),
            )
        ),
    )


def test_filename_fallback_warnings_land_on_article_model_warnings(tmp_path: Path) -> None:
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "A2B_Tables 1 and 2_revised.docx").write_bytes(b"content")
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="cs-2024-5238",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(_VALID_ARTICLE_VERSION),
        extraction_bundle=_missing_name_bundle(),
    )

    assert len(model.warnings) == 1
    assert model.warnings[0].code == "BR013_FALLBACK_FILENAME_FROM_PATH"
    assert model.resolved_files[0].original_filename == "A2B_Tables 1 and 2_revised.docx"


def test_feature_flags_none_defaults_to_lenient_fallback(tmp_path: Path) -> None:
    """Every existing call site (no `feature_flags` passed) keeps working, now leniently."""
    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "A2B_Tables 1 and 2_revised.docx").write_bytes(b"content")
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="cs-2024-5238",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(_VALID_ARTICLE_VERSION),
        extraction_bundle=_missing_name_bundle(),
    )

    assert len(model.warnings) == 1


def _missing_name_manuscript_bundle() -> ExtractionBundle:
    """Like `_missing_name_bundle` but category="manuscript" — the one
    category Milestone 11 keeps fatal, needed to test that strict mode
    (`allow_filename_fallback=False`) still raises rather than recovering."""
    from meca_engine.extraction.metadata_models import NamedContentField

    return replace(
        _empty_bundle(),
        custom=CustomMetadata(
            entries=(
                CustomMetaEntry(
                    name=None,
                    value_text="",
                    attributes=(("specific-use", "form-files"),),
                    named_content=(
                        NamedContentField(content_type="type", text="manuscript"),
                        NamedContentField(
                            content_type="path",
                            text="/ppl/cs/cs-2024-5238/inputs/R1/A2B_Tables 1 and 2_revised.docx",
                        ),
                    ),
                ),
            )
        ),
    )


def test_feature_flags_strict_mode_restores_exception(tmp_path: Path) -> None:
    from meca_engine.config.schema import FeatureFlagsConfig

    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "A2B_Tables 1 and 2_revised.docx").write_bytes(b"content")
    coordinator = TransformationCoordinator(
        media_type_config=_MEDIA_TYPE_CONFIG,
        feature_flags=FeatureFlagsConfig(
            reviews_include_duplicate_correspondence=True,
            reviews_extended_history_scope=True,
            strict_replication_mode=False,
            allow_filename_fallback=False,
        ),
    )

    with pytest.raises(FileReferenceMissingError):
        coordinator.build_model(
            article_id="cs-2024-5238",
            source_object_key="x",
            staged_root=str(tmp_path),
            parsed_document=_document(_VALID_ARTICLE_VERSION),
            extraction_bundle=_missing_name_manuscript_bundle(),
        )


def test_no_warnings_when_nothing_needs_recovering(tmp_path: Path) -> None:
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="cs-2025-0001",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(_VALID_ARTICLE_VERSION),
        extraction_bundle=_empty_bundle(),
    )

    assert model.warnings == ()


def test_file_entry_round_label_is_reconciled_with_the_resolved_physical_round(
    tmp_path: Path,
) -> None:
    """Corrective-milestone fix: a `_temp/<uuid>/<file>` declared path has no round
    segment (BR-016) — `custom_meta_classifier`'s naive positional parse used to
    leave the per-file staging-job uuid as `FileEntry.round_label`. The coordinator
    now overwrites it with the physically-resolved round, matching `resolved_files`.
    """
    from meca_engine.extraction.metadata_models import NamedContentField

    round_dir = tmp_path / "R1"
    round_dir.mkdir()
    (round_dir / "manuscript.docx").write_bytes(b"content")

    bundle = replace(
        _empty_bundle(),
        custom=CustomMetadata(
            entries=(
                CustomMetaEntry(
                    name=None,
                    value_text="",
                    attributes=(("specific-use", "form-files"),),
                    named_content=(
                        NamedContentField(content_type="type", text="manuscript"),
                        NamedContentField(content_type="name", text="manuscript"),
                        NamedContentField(
                            content_type="path",
                            text="_temp/f2f0b0b6-5368-4166-8f05-d0383a0fb8c3/manuscript.docx",
                        ),
                    ),
                ),
            )
        ),
    )
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    model = coordinator.build_model(
        article_id="cs-2025-0001",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(_VALID_ARTICLE_VERSION),
        extraction_bundle=bundle,
    )

    assert len(model.custom_meta.file_entries) == 1
    assert model.custom_meta.file_entries[0].round_label == "R1"
    assert model.resolved_files[0].round_label == "R1"
    assert model.custom_meta.file_entries[0].round_label == model.resolved_files[0].round_label


def test_reconcile_file_entry_round_labels_rejects_a_length_mismatch() -> None:
    from meca_engine.exceptions import ModelBuildError
    from meca_engine.model.article import FileEntry
    from meca_engine.transform.coordinator import _reconcile_file_entry_round_labels

    file_entries = (
        FileEntry(
            round_label="uuid-hint",
            category="manuscript",
            original_filename="manuscript",
            declared_path_hint="_temp/uuid/manuscript.docx",
            declared_size_bytes=None,
        ),
    )

    with pytest.raises(ModelBuildError, match="contract was violated"):
        _reconcile_file_entry_round_labels(file_entries, resolved_files=(), skipped_indices=())


def test_reconcile_file_entry_round_labels_keeps_skipped_entries_unchanged() -> None:
    from meca_engine.model.article import FileEntry, ResolvedFile
    from meca_engine.transform.coordinator import _reconcile_file_entry_round_labels

    skipped_entry = FileEntry(
        round_label="uuid-hint",
        category="supplement",
        original_filename="missing.pdf",
        declared_path_hint="_temp/uuid/missing.pdf",
    )
    resolved_entry = FileEntry(
        round_label="uuid-hint",
        category="manuscript",
        original_filename="manuscript.docx",
        declared_path_hint="_temp/uuid/manuscript.docx",
    )
    resolved_file = ResolvedFile(
        round_label="R1",
        category="manuscript",
        original_filename="manuscript.docx",
        staged_physical_path="/tmp/R1/manuscript.docx",
        checksum="abc",
        size_bytes=1,
        media_type="application/msword",
    )

    reconciled = _reconcile_file_entry_round_labels(
        (skipped_entry, resolved_entry), resolved_files=(resolved_file,), skipped_indices=(0,)
    )

    assert reconciled[0].round_label == "uuid-hint"
    assert reconciled[1].round_label == "R1"


def test_two_calls_produce_independent_models(tmp_path: Path) -> None:
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG)

    first = coordinator.build_model(
        article_id="a",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=_empty_bundle(),
    )
    second = coordinator.build_model(
        article_id="b",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=_empty_bundle(),
    )

    assert first.identity.article_id == "a"
    assert second.identity.article_id == "b"


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_logs_start_and_completion(tmp_path: Path) -> None:
    underlying = logging.getLogger("meca_engine.test.coordinator_logging")
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False

    logger = StructuredLogger("test.coordinator_logging")
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG, logger=logger)

    coordinator.build_model(
        article_id="cs-2025-0001",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=_empty_bundle(),
    )

    messages = [r.getMessage() for r in handler.records]
    assert any("started" in m for m in messages)
    assert any("completed" in m for m in messages)
    underlying.removeHandler(handler)


def test_emits_a_performance_event_when_logger_supplied(tmp_path: Path) -> None:
    from meca_engine.constants import LogCategory
    from meca_engine.logging_.record_fields import EXTRA_CATEGORY

    underlying = logging.getLogger("meca_engine.test.coordinator_perf")
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False

    logger = StructuredLogger("test.coordinator_perf")
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG, logger=logger)

    coordinator.build_model(
        article_id="cs-2025-0001",
        source_object_key="x",
        staged_root=str(tmp_path),
        parsed_document=_document(),
        extraction_bundle=_empty_bundle(),
    )

    performance_events = [
        r
        for r in handler.records
        if getattr(r, EXTRA_CATEGORY, None) == LogCategory.PERFORMANCE.value
    ]
    assert len(performance_events) == 1
    underlying.removeHandler(handler)
