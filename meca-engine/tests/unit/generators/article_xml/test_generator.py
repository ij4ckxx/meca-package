"""Unit tests for meca_engine.generators.article_xml.generator.ArticleXmlGenerator."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element, SubElement, fromstring

import pytest

from meca_engine.config.schema import LicenseTemplatesConfig
from meca_engine.exceptions import GeneratorInvariantError, MissingDoiError
from meca_engine.generators.article_xml.generator import _UUID_ID_PATTERN, ArticleXmlGenerator
from meca_engine.generators.diagnostics import DiagnosticSeverity
from meca_engine.generators.result import GenerationResult
from meca_engine.generators.xml.helpers import strip_attribute_matching
from meca_engine.model.article import (
    DecisionDraft,
    DeclineReason,
    FormAnswerBag,
    FormAnswerEntry,
    ReviewerScorecard,
)
from meca_engine.model.enums import ContribType, ReviewOutcomeStatus

if TYPE_CHECKING:
    from meca_engine.config.schema import (
        ArticleTypeMappingConfig,
        ArticleXmlConfig,
        PublisherAbbreviationMappingConfig,
    )
    from meca_engine.generators.article_xml.document import ArticleXmlDocument
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.raw_xml.generator import RawXmlGenerator
    from meca_engine.generators.xml.namespaces import NamespaceManager

pytestmark = pytest.mark.unit


def _decode(document: ArticleXmlDocument) -> str:
    return document.xml_bytes.decode("utf-8")


# --- lifecycle / framework usage ----------------------------------------------


def test_generator_name_is_article_xml(article_xml_generator: ArticleXmlGenerator) -> None:
    assert article_xml_generator.generator_name == "article_xml"


def test_generate_returns_a_generation_result(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = article_xml_generator.generate(rich_context)

    assert isinstance(result, GenerationResult)
    assert result.article_id == "cs-2025-0001"
    assert result.generator_name == "article_xml"
    assert result.duration_ms >= 0


def test_filename_matches_br_073_pattern(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = article_xml_generator.generate(rich_context)

    assert result.document.filename == "cs-2025-0001_article.xml"


def test_output_is_well_formed_xml(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = article_xml_generator.generate(rich_context)

    fromstring(result.document.xml_bytes)  # raises if not well-formed


def test_raw_xml_generator_diagnostics_are_shared(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    # BaseGenerator.generate shares one DiagnosticsCollector across every
    # generator invoked for one article's generation pass — raw_xml's own
    # diagnostics (e.g. the always-emitted missing-<back> warning) must
    # already be present when article_xml's generate() returns.
    result = article_xml_generator.generate(rich_context)

    assert any("<back>" in d.message for d in result.diagnostics)


# --- root / declaration / DTD (BR-052/053/055/056/074) ------------------------


def test_xml_declaration_matches_br_053(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(article_xml_generator.generate(rich_context).document)

    assert output.startswith('<?xml version="1.0" encoding="utf-8"?>')


def test_doctype_matches_br_052(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(article_xml_generator.generate(rich_context).document)

    assert (
        '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and '
        'Interchange DTD v1.2 20190208//EN" '
        '"https://jats.nlm.nih.gov/archiving/1.2/JATS-archivearticle1.dtd">'
    ) in output


def test_dtd_version_matches_br_074(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    assert root.get("dtd-version") == "1.2"


def test_root_never_declares_mml_xsi_ali_or_xml_lang_br_055(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(article_xml_generator.generate(rich_context).document)

    assert "xmlns:mml" not in output
    assert "xmlns:xsi" not in output
    assert "xmlns:ali" not in output
    assert "xml:lang" not in output


def test_xlink_declared_when_used_br_056(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(article_xml_generator.generate(rich_context).document)

    assert 'xmlns:xlink="http://www.w3.org/1999/xlink"' in output


def test_xlink_not_declared_when_unused_br_056(
    article_xml_generator: ArticleXmlGenerator, empty_context: GeneratorContext
) -> None:
    output = _decode(article_xml_generator.generate(empty_context).document)

    assert "xmlns:xlink" not in output


def test_article_type_is_always_original_study_br_057(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    assert root.get("article-type") == "Original Study"


def test_article_type_falls_back_to_default_for_unmapped_display_channel(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    unmapped_meta = replace(rich_context.model.article_meta, display_channel_subject="Unknown Type")
    unmapped_context = replace(
        rich_context, model=replace(rich_context.model, article_meta=unmapped_meta)
    )

    root = fromstring(article_xml_generator.generate(unmapped_context).document.xml_bytes)

    assert root.get("article-type") == "Original Study"


# --- DOI generation (BR-058/059) ------------------------------------------------


def test_doi_generated_from_doi_article_id_br_058(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)
    doi = root.find("front/article-meta/article-id[@pub-id-type='doi']")

    assert doi is not None
    assert doi.text == "10.1042/ex2025001"


def test_doi_prefix_comes_from_journal_config_br_059(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    custom_journal_config = replace(rich_context.journal_config, doi_prefix="10.9999")
    custom_context = replace(rich_context, journal_config=custom_journal_config)

    root = fromstring(article_xml_generator.generate(custom_context).document.xml_bytes)
    doi = root.find("front/article-meta/article-id[@pub-id-type='doi']")

    assert doi is not None
    assert doi.text == "10.9999/ex2025001"


def test_missing_doi_article_id_raises_missing_doi_error(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    broken_identity = replace(rich_context.model.identity, doi_article_id_value="")
    broken_context = replace(
        rich_context, model=replace(rich_context.model, identity=broken_identity)
    )

    with pytest.raises(MissingDoiError):
        article_xml_generator.generate(broken_context)


def test_publisher_id_article_id_copied_verbatim(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)
    publisher_id = root.find("front/article-meta/article-id[@pub-id-type='publisher-id']")

    assert publisher_id is not None
    assert publisher_id.text == "EX-2025-001"


def test_missing_publisher_id_is_diagnosed(
    article_xml_generator: ArticleXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = article_xml_generator.generate(empty_context)

    assert any("publisher-id" in d.message for d in result.diagnostics)


# --- id stripping (BR-054) ------------------------------------------------------


def test_uuid_style_ids_are_stripped_from_body_derived_content(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    # The journal-meta/article-meta content this generator copies from
    # raw.xml never carries real Kriyadocs UUIDs in this test's fixture
    # (only semantic ids like "aff1") — this test instead confirms the
    # semantic ones (load-bearing for xref linking) survive, and directly
    # exercises the UUID-pattern stripper against a synthetic UUID id.
    element = Element("aff", {"id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"})
    strip_attribute_matching(element, "id", _UUID_ID_PATTERN)

    assert element.get("id") is None


def test_semantic_aff_ids_survive_for_cross_reference_linking(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)
    aff = root.find("front/article-meta/aff")

    assert aff is not None
    assert aff.get("id") == "aff1"


# --- copied-verbatim sections (BR-060) ------------------------------------------


def test_title_group_copied_from_raw_xml(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    title = root.find("front/article-meta/title-group/article-title")
    assert title is not None
    assert title.text == "A Study of Example Practices"


def test_contrib_group_copied_from_raw_xml(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    contrib = root.find("front/article-meta/contrib-group/contrib")
    assert contrib is not None
    assert contrib.get("contrib-type") == ContribType.AUTHOR.value
    assert contrib.findtext("name/surname") == "Doe"


def test_history_copied_from_raw_xml(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    history = root.find("front/article-meta/history")
    assert history is not None
    assert {d.get("date-type") for d in history.findall("date")} == {
        "received",
        "revised",
        "accepted",
    }


def test_abstract_copied_from_raw_xml(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    abstract = root.find("front/article-meta/abstract")
    assert abstract is not None
    assert abstract.findtext("p") == "This study examines example practices."


def test_counts_copied_from_raw_xml(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    counts = root.find("front/article-meta/counts")
    assert counts is not None
    word_count = counts.find("word-count")
    assert word_count is not None
    assert word_count.get("count") == "5000"


def test_no_body_element_ever_included_br_072(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    assert root.find("body") is None


# --- author-notes / corresp (BR-060/061) ----------------------------------------


def test_corresponding_email_xlink_attributes_stripped_br_061(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    corresp = root.find("front/article-meta/author-notes/corresp")
    assert corresp is not None
    email = corresp.find("email")
    assert email is not None
    assert email.text == "jane.doe@example.com"
    assert email.get("{http://www.w3.org/1999/xlink}href") is None
    assert email.get("xlink:href") is None


def test_corresp_id_survives_stripping(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    corresp = root.find("front/article-meta/author-notes/corresp")
    assert corresp is not None
    assert corresp.get("id") == "cor1"


# --- permissions / license (BR-062/063/064/065) --------------------------------


def test_copyright_statement_copied_verbatim_br_062(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    permissions = root.find("front/article-meta/permissions")
    assert permissions is not None
    assert permissions.findtext("copyright-statement") == "© 2025 The Author(s)."


def test_cc_by_license_synthesized_when_no_license_type_key_br_065_evidence(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    # No "license type"/"License Type" key exists in the rich_context
    # fixture at all — matches cs-2025-8827's real, confirmed behavior.
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    license_element = root.find("front/article-meta/permissions/license")
    assert license_element is not None
    assert license_element.get("license-type") == "open-access"
    assert (
        license_element.get("{http://www.w3.org/1999/xlink}href")
        == "https://creativecommons.org/licenses/by/4.0/"
    )
    license_p = license_element.find("license-p")
    assert license_p is not None
    assert "Creative Commons Attribution License 4.0 (CC BY)" in (license_p.text or "")


def test_cc_by_license_synthesized_when_license_type_key_confirms_it(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    custom_meta = replace(
        rich_context.model.custom_meta,
        form_answers=FormAnswerBag(
            entries=(FormAnswerEntry(key="license type", values=("CC-BY-4-0",)),)
        ),
    )
    context = replace(rich_context, model=replace(rich_context.model, custom_meta=custom_meta))

    root = fromstring(article_xml_generator.generate(context).document.xml_bytes)

    assert root.find("front/article-meta/permissions/license") is not None


def test_no_license_synthesized_for_a_non_cc_by_license_type(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    custom_meta = replace(
        rich_context.model.custom_meta,
        form_answers=FormAnswerBag(
            entries=(FormAnswerEntry(key="license type", values=("All Rights Reserved",)),)
        ),
    )
    context = replace(rich_context, model=replace(rich_context.model, custom_meta=custom_meta))

    result = article_xml_generator.generate(context)
    root = fromstring(result.document.xml_bytes)

    assert root.find("front/article-meta/permissions/license") is None
    assert any(
        d.severity is DiagnosticSeverity.INFO and "License Type" in d.message
        for d in result.diagnostics
    )


def test_unconfigured_license_type_recovers_by_omitting_the_license_block(
    raw_xml_generator: RawXmlGenerator,
    namespace_manager: NamespaceManager,
    article_xml_config: ArticleXmlConfig,
    article_type_mapping: ArticleTypeMappingConfig,
    publisher_abbreviation_mapping: PublisherAbbreviationMappingConfig,
    rich_context: GeneratorContext,
) -> None:
    """Milestone 11: a configuration gap (no template for a resolved License
    Type) recovers by omitting the license block, rather than raising."""
    generator = ArticleXmlGenerator(
        raw_xml_generator=raw_xml_generator,
        namespace_manager=namespace_manager,
        article_xml_config=article_xml_config,
        article_type_mapping=article_type_mapping,
        license_templates=LicenseTemplatesConfig(templates={}),
        publisher_abbreviation_mapping=publisher_abbreviation_mapping,
    )

    result = generator.generate(rich_context)

    root = fromstring(result.document.xml_bytes)
    assert root.find(".//license") is None
    assert any(
        "No license template configured" in d.message and "recoverable" in d.message
        for d in result.diagnostics
    )


# --- custom-meta pruning (BR-066/067/068/069/071/075) --------------------------


def test_form_answers_pass_through_unchanged_br_071(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    entries = root.findall("front/article-meta/custom-meta-group/custom-meta")
    names = [e.findtext("meta-name") for e in entries]
    assert "Authorship" in names


def test_only_latest_round_file_entries_survive_br_066(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(article_xml_generator.generate(rich_context).document.xml_bytes)

    entries = root.findall("front/article-meta/custom-meta-group/custom-meta")
    file_values = [e.findtext("meta-value") for e in entries if e.findtext("meta-name") == "file"]
    assert len(file_values) == 2  # R1's manuscript + supplement, not Original's manuscript
    assert all(v is not None and "(R1)" in v for v in file_values)
    assert not any(v is not None and "manuscript_v1.docx" in v for v in file_values)


def test_reviewer_scorecards_never_appear_br_067_075(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    custom_meta = replace(
        rich_context.model.custom_meta,
        reviewer_scorecards=(
            ReviewerScorecard(
                round_label="Original",
                reviewer_name="Alex Reviewer",
                reviewer_email="reviewer@example.com",
                outcome_status=ReviewOutcomeStatus.COMPLETED,
                answers=(("QN_01", "Yes"),),
            ),
        ),
    )
    context = replace(rich_context, model=replace(rich_context.model, custom_meta=custom_meta))

    root = fromstring(article_xml_generator.generate(context).document.xml_bytes)
    entries = root.findall("front/article-meta/custom-meta-group/custom-meta")
    names = [e.findtext("meta-name") or "" for e in entries]

    assert not any(name.startswith("QN_") or "reviewer-scorecard" in name for name in names)


def test_decline_reasons_never_appear_br_068(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    custom_meta = replace(
        rich_context.model.custom_meta,
        decline_reasons=(
            DeclineReason(round_label="Original", reviewer_name="Sam Decliner", reason_text="Busy"),
        ),
    )
    context = replace(rich_context, model=replace(rich_context.model, custom_meta=custom_meta))

    root = fromstring(article_xml_generator.generate(context).document.xml_bytes)
    entries = root.findall("front/article-meta/custom-meta-group/custom-meta")
    names = [e.findtext("meta-name") or "" for e in entries]

    assert not any("decline" in name.lower() for name in names)


def test_decision_drafts_never_appear_br_069(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    custom_meta = replace(
        rich_context.model.custom_meta,
        decision_drafts=(
            DecisionDraft(round_label="Original", decision_text="Send for minor revisions."),
        ),
    )
    context = replace(rich_context, model=replace(rich_context.model, custom_meta=custom_meta))

    root = fromstring(article_xml_generator.generate(context).document.xml_bytes)
    entries = root.findall("front/article-meta/custom-meta-group/custom-meta")
    names = [e.findtext("meta-name") for e in entries]

    assert "Decision Draft" not in names


def test_no_custom_meta_information_is_diagnosed(
    article_xml_generator: ArticleXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = article_xml_generator.generate(empty_context)
    root = fromstring(result.document.xml_bytes)

    assert root.find("front/article-meta/custom-meta-group") is None
    assert any("custom-meta" in d.message for d in result.diagnostics)


def test_no_latest_round_is_diagnosed(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    broken_model = replace(rich_context.model, rounds=())
    context = replace(rich_context, model=broken_model)

    result = article_xml_generator.generate(context)

    assert any("latest round" in d.message for d in result.diagnostics)


def test_no_file_manifest_entries_is_diagnosed(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    custom_meta = replace(rich_context.model.custom_meta, file_entries=())
    context = replace(rich_context, model=replace(rich_context.model, custom_meta=custom_meta))

    result = article_xml_generator.generate(context)

    assert any("file-manifest" in d.message for d in result.diagnostics)


# --- deterministic ordering / malformed ICAM / exceptions -----------------------


def test_generation_is_deterministic_across_repeated_calls(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    first = article_xml_generator.generate(rich_context).document.xml_bytes
    second = article_xml_generator.generate(rich_context).document.xml_bytes

    assert first == second


def test_malformed_body_fragment_raises_generator_invariant_error(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    broken_model = replace(
        rich_context.model,
        body_fragment=replace(
            rich_context.model.body_fragment, raw_xml_fragment="<body><unclosed>"
        ),
    )
    broken_context = replace(rich_context, model=broken_model)

    with pytest.raises(GeneratorInvariantError):
        article_xml_generator.generate(broken_context)


def test_every_optional_field_missing_still_produces_a_document(
    article_xml_generator: ArticleXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = article_xml_generator.generate(empty_context)

    assert result.document.xml_bytes
    assert len(result.diagnostics) > 3


# --- BR-164: publisher abbreviation journal title -----------------------------


def _journal_meta_fixture(
    *, publisher_id: str = "cs", existing_abbrevs: tuple[tuple[str, str], ...] = ()
) -> Element:
    front = Element("front")
    journal_meta = SubElement(front, "journal-meta")
    SubElement(journal_meta, "journal-id", {"journal-id-type": "publisher-id"}).text = publisher_id
    title_group = SubElement(journal_meta, "journal-title-group")
    SubElement(title_group, "journal-title").text = "Clinical Science"
    for abbrev_type, text in existing_abbrevs:
        SubElement(title_group, "abbrev-journal-title", {"abbrev-type": abbrev_type}).text = text
    return front


def test_br164_generates_publisher_abbreviation_when_missing() -> None:
    from meca_engine.config.schema import PublisherAbbreviationMappingConfig
    from meca_engine.generators.article_xml.generator import _copy_journal_meta
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder

    builder = XmlDocumentBuilder()
    front = builder.create_root("front")
    raw_front = _journal_meta_fixture(
        publisher_id="cs", existing_abbrevs=(("pubmed", "Clin. Sci."),)
    )
    diagnostics = DiagnosticsCollector()
    mapping = PublisherAbbreviationMappingConfig(mappings={"cs": "CS"})

    _copy_journal_meta(builder, front, raw_front, mapping, diagnostics)

    title_group = front.find("journal-meta/journal-title-group")
    assert title_group is not None
    children = list(title_group)
    tags_and_types = [(c.tag, c.get("abbrev-type")) for c in children]
    assert tags_and_types == [
        ("journal-title", None),
        ("abbrev-journal-title", "publisher"),
        ("abbrev-journal-title", "pubmed"),
    ]
    publisher_abbrev = title_group.find('abbrev-journal-title[@abbrev-type="publisher"]')
    assert publisher_abbrev is not None
    assert publisher_abbrev.text == "CS"
    assert any("BR-164" in d.message and "CS" in d.message for d in diagnostics.diagnostics)


def test_br164_lookup_is_case_insensitive() -> None:
    """Regression (real corpus evidence, CS-2025-6808): journal-id can be uppercase
    ("CS") for the same journal a lowercase mapping key ("cs") identifies — this is
    a casing variant of a known key, not a guess, so it must still resolve."""
    from meca_engine.config.schema import PublisherAbbreviationMappingConfig
    from meca_engine.generators.article_xml.generator import _copy_journal_meta
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder

    builder = XmlDocumentBuilder()
    front = builder.create_root("front")
    raw_front = _journal_meta_fixture(publisher_id="CS")
    diagnostics = DiagnosticsCollector()
    mapping = PublisherAbbreviationMappingConfig(mappings={"cs": "CS"})

    _copy_journal_meta(builder, front, raw_front, mapping, diagnostics)

    title_group = front.find("journal-meta/journal-title-group")
    assert title_group is not None
    publisher_abbrev = title_group.find('abbrev-journal-title[@abbrev-type="publisher"]')
    assert publisher_abbrev is not None
    assert publisher_abbrev.text == "CS"


def test_br164_never_generates_a_duplicate_when_already_present() -> None:
    from meca_engine.config.schema import PublisherAbbreviationMappingConfig
    from meca_engine.generators.article_xml.generator import _copy_journal_meta
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder

    builder = XmlDocumentBuilder()
    front = builder.create_root("front")
    raw_front = _journal_meta_fixture(
        publisher_id="cs", existing_abbrevs=(("publisher", "CS"), ("pubmed", "Clin. Sci."))
    )
    diagnostics = DiagnosticsCollector()
    mapping = PublisherAbbreviationMappingConfig(mappings={"cs": "CS"})

    _copy_journal_meta(builder, front, raw_front, mapping, diagnostics)

    title_group = front.find("journal-meta/journal-title-group")
    assert title_group is not None
    publisher_abbrevs = title_group.findall('abbrev-journal-title[@abbrev-type="publisher"]')
    assert len(publisher_abbrevs) == 1
    assert not any("BR-164" in d.message for d in diagnostics.diagnostics)


def test_br164_leaves_xml_unchanged_for_unknown_publisher_id() -> None:
    from meca_engine.config.schema import PublisherAbbreviationMappingConfig
    from meca_engine.generators.article_xml.generator import _copy_journal_meta
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder

    builder = XmlDocumentBuilder()
    front = builder.create_root("front")
    raw_front = _journal_meta_fixture(publisher_id="unknown-journal")
    diagnostics = DiagnosticsCollector()
    mapping = PublisherAbbreviationMappingConfig(mappings={"cs": "CS"})

    _copy_journal_meta(builder, front, raw_front, mapping, diagnostics)

    title_group = front.find("journal-meta/journal-title-group")
    assert title_group is not None
    assert title_group.find('abbrev-journal-title[@abbrev-type="publisher"]') is None
    assert list(title_group) == [title_group.find("journal-title")]
    warnings = [d for d in diagnostics.diagnostics if d.severity is DiagnosticSeverity.WARNING]
    assert any("BR-164" in d.message and "unknown-journal" in d.message for d in warnings)


# --- defensive branches (missing raw.xml sections; internal helpers) -----------


def test_missing_raw_front_and_article_meta_is_diagnosed_and_still_produces_a_document() -> None:
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import PublisherAbbreviationMappingConfig
    from meca_engine.generators.article_xml.generator import _copy_journal_meta
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder

    builder = XmlDocumentBuilder()
    front = builder.create_root("front")
    raw_front_without_journal_meta = Element("front")
    diagnostics = DiagnosticsCollector()

    _copy_journal_meta(
        builder,
        front,
        raw_front_without_journal_meta,
        PublisherAbbreviationMappingConfig(mappings={}),
        diagnostics,
    )

    assert front.find("journal-meta") is None
    assert any("journal-meta" in d.message for d in diagnostics.diagnostics)


def test_corresp_without_email_child_is_left_untouched() -> None:
    from xml.etree.ElementTree import Element, SubElement

    from meca_engine.generators.article_xml.generator import _copy_author_notes
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder

    builder = XmlDocumentBuilder()
    article_meta = builder.create_root("article-meta")
    raw_author_notes = Element("author-notes")
    SubElement(raw_author_notes, "corresp", {"id": "cor1"})
    diagnostics = DiagnosticsCollector()

    _copy_author_notes(builder, article_meta, [raw_author_notes], diagnostics)

    corresp = article_meta.find("author-notes/corresp")
    assert corresp is not None
    assert corresp.find("email") is None


def test_copy_author_notes_merges_multiple_blocks_preserving_every_fn() -> None:
    """Regression test (cs-2024-5002): every separate author-notes block must survive."""
    from xml.etree.ElementTree import Element, SubElement

    from meca_engine.generators.article_xml.generator import _copy_author_notes
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder

    builder = XmlDocumentBuilder()
    article_meta = builder.create_root("article-meta")
    blocks = []
    for index in range(1, 15):
        block = Element("author-notes", {"id": f"raw-uuid-{index}"})
        fn = SubElement(block, "fn", {"fn-type": "con", "id": f"con{index}"})
        SubElement(fn, "p").text = f"Role {index}"
        blocks.append(block)
    diagnostics = DiagnosticsCollector()

    _copy_author_notes(builder, article_meta, blocks, diagnostics)

    author_notes_elements = article_meta.findall("author-notes")
    assert len(author_notes_elements) == 1
    fn_ids = [fn.get("id") for fn in author_notes_elements[0].findall("fn")]
    assert fn_ids == [f"con{index}" for index in range(1, 15)]
    messages = [d.message for d in diagnostics.diagnostics]
    assert any("Merged 14 separate author-notes blocks" in message for message in messages)


def test_copy_author_notes_keeps_same_id_children_when_content_differs() -> None:
    """Never silently drop a same-id repeat unless it's byte-for-byte identical."""
    from xml.etree.ElementTree import Element, SubElement

    from meca_engine.generators.article_xml.generator import _copy_author_notes
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder

    builder = XmlDocumentBuilder()
    article_meta = builder.create_root("article-meta")
    block_a = Element("author-notes")
    fn_a = SubElement(block_a, "fn", {"fn-type": "con", "id": "con1"})
    SubElement(fn_a, "p").text = "Conceptualization"
    block_b = Element("author-notes")
    fn_b = SubElement(block_b, "fn", {"fn-type": "con", "id": "con1"})
    SubElement(fn_b, "p").text = "Different text under the same id"
    diagnostics = DiagnosticsCollector()

    _copy_author_notes(builder, article_meta, [block_a, block_b], diagnostics)

    fn_texts = [fn.findtext("p") for fn in article_meta.findall("author-notes/fn")]
    assert fn_texts == ["Conceptualization", "Different text under the same id"]


class _StubRawXmlDocument:
    def __init__(self, xml_bytes: bytes) -> None:
        self.xml_bytes = xml_bytes


class _StubRawResult:
    def __init__(self, xml_bytes: bytes) -> None:
        self.document = _StubRawXmlDocument(xml_bytes)


class _FrontlessRawXmlGenerator:
    """Stands in for RawXmlGenerator, producing a document with no <front>."""

    namespace_prefixes: tuple[str, ...] = ()

    def generate(self, context: GeneratorContext) -> _StubRawResult:
        del context
        return _StubRawResult(b"<article/>")


def test_missing_raw_front_element_skips_journal_meta_and_article_meta_copy(
    namespace_manager: NamespaceManager,
    article_xml_config: ArticleXmlConfig,
    article_type_mapping: ArticleTypeMappingConfig,
    license_templates: LicenseTemplatesConfig,
    publisher_abbreviation_mapping: PublisherAbbreviationMappingConfig,
    rich_context: GeneratorContext,
) -> None:
    generator = ArticleXmlGenerator(
        raw_xml_generator=_FrontlessRawXmlGenerator(),  # type: ignore[arg-type]
        namespace_manager=namespace_manager,
        article_xml_config=article_xml_config,
        article_type_mapping=article_type_mapping,
        license_templates=license_templates,
        publisher_abbreviation_mapping=publisher_abbreviation_mapping,
    )

    result = generator.generate(rich_context)
    root = fromstring(result.document.xml_bytes)

    article_meta = root.find("front/article-meta")
    assert root.find("front/journal-meta") is None
    assert article_meta is not None
    assert list(article_meta) == []


def test_xlink_uri_unregistered_omits_the_namespace_declaration(
    article_xml_config: ArticleXmlConfig,
    article_type_mapping: ArticleTypeMappingConfig,
    license_templates: LicenseTemplatesConfig,
    publisher_abbreviation_mapping: PublisherAbbreviationMappingConfig,
    rich_context: GeneratorContext,
) -> None:
    """BR-056's guard degrades gracefully when `xlink` is unregistered.

    `xlink:href` is still attached to the synthesized license (BR-063/064
    write it directly, independent of raw.xml's own namespace prefixes)
    even though nothing declares the raw.xml-side `xlink` prefix — so
    `uses_prefix(root, "xlink")` is true while `uri_for("xlink")` is
    `None`, exercising the declaration's defensive fallback.
    """
    from meca_engine.config.schema import RawXmlConfig
    from meca_engine.generators.raw_xml.generator import RawXmlGenerator
    from meca_engine.generators.xml.namespaces import NamespaceManager as _NamespaceManager

    namespace_manager_without_xlink = _NamespaceManager(
        {"mml": "http://www.w3.org/1998/Math/MathML"}
    )
    raw_xml_config_without_xlink = RawXmlConfig(
        doctype_public_id="-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.3 20210610//EN",
        doctype_system_id="JATS-journalpublishing1-3.dtd",
        article_type="research-article",
        dtd_version="1.3",
        default_xml_lang="en",
        encoding="UTF-8",
        namespace_prefixes=("mml",),
        pretty_indent_spaces=0,
    )
    raw_xml_generator_without_xlink = RawXmlGenerator(
        namespace_manager=namespace_manager_without_xlink,
        raw_xml_config=raw_xml_config_without_xlink,
    )
    generator = ArticleXmlGenerator(
        raw_xml_generator=raw_xml_generator_without_xlink,
        namespace_manager=namespace_manager_without_xlink,
        article_xml_config=article_xml_config,
        article_type_mapping=article_type_mapping,
        license_templates=license_templates,
        publisher_abbreviation_mapping=publisher_abbreviation_mapping,
    )
    # corresponding_emails cleared: raw.xml itself only emits `xlink:href` for
    # BR-061's corresp/email — clearing it isolates this test to the license's
    # own, independently-added `xlink:href` (BR-063/064).
    article_meta_without_corresp = replace(rich_context.model.article_meta, corresponding_emails=())
    context = replace(
        rich_context, model=replace(rich_context.model, article_meta=article_meta_without_corresp)
    )

    result = generator.generate(context)
    text = _decode(result.document)

    # Re-parsing via ElementTree is deliberately not used here: the output
    # genuinely has an undeclared `xlink:` prefix, which is exactly what
    # this edge case exercises — asserted on the serialized text instead.
    assert "xmlns:xlink=" not in text
    assert "xlink:href=" in text


def test_no_file_entries_match_the_latest_round_is_diagnosed(
    article_xml_generator: ArticleXmlGenerator, rich_context: GeneratorContext
) -> None:
    original_file_entries = rich_context.model.custom_meta.file_entries
    stale_file_entries = tuple(
        replace(entry, round_label="Original") for entry in original_file_entries
    )
    custom_meta = replace(rich_context.model.custom_meta, file_entries=stale_file_entries)
    context = replace(rich_context, model=replace(rich_context.model, custom_meta=custom_meta))

    result = article_xml_generator.generate(context)
    root = fromstring(result.document.xml_bytes)

    file_entries_in_output = [
        e
        for e in root.findall("front/article-meta/custom-meta-group/custom-meta")
        if e.findtext("meta-name") == "file"
    ]
    assert file_entries_in_output == []
    assert any("latest round" in d.message for d in result.diagnostics)
