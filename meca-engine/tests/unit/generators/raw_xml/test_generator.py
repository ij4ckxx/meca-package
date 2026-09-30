"""Unit tests for meca_engine.generators.raw_xml.generator.RawXmlGenerator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from xml.etree.ElementTree import fromstring

import pytest

from meca_engine.config.schema import RawXmlConfig
from meca_engine.exceptions import GeneratorInvariantError
from meca_engine.generators.diagnostics import DiagnosticSeverity
from meca_engine.generators.raw_xml.generator import RawXmlGenerator
from meca_engine.generators.result import GenerationResult
from meca_engine.generators.xml.namespaces import NamespaceManager

if TYPE_CHECKING:
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.raw_xml.document import RawXmlDocument

pytestmark = pytest.mark.unit


# --- lifecycle / framework usage ----------------------------------------------


def test_generator_name_is_raw_xml(raw_xml_generator: RawXmlGenerator) -> None:
    assert raw_xml_generator.generator_name == "raw_xml"


def test_generate_returns_a_generation_result(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(rich_context)

    assert isinstance(result, GenerationResult)
    assert result.article_id == "cs-2025-0001"
    assert result.generator_name == "raw_xml"
    assert result.duration_ms >= 0


def test_filename_matches_br_048_pattern(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(rich_context)

    assert result.document.filename == "cs-2025-0001_raw.xml"


def test_output_is_well_formed_xml(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(rich_context)

    fromstring(result.document.xml_bytes)  # raises if not well-formed


# --- root element / declaration / namespaces (BR-036/37/38/40/49/50) ---------


def _decode(document: RawXmlDocument) -> str:
    return document.xml_bytes.decode("utf-8")


def test_xml_declaration_matches_br_038(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(raw_xml_generator.generate(rich_context).document)

    assert output.startswith('<?xml version="1.0" encoding="UTF-8"?>')


def test_doctype_matches_br_036(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(raw_xml_generator.generate(rich_context).document)

    assert (
        '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD '
        'v1.3 20210610//EN" "JATS-journalpublishing1-3.dtd">'
    ) in output


def test_root_declares_4_namespaces_unconditionally_br_037(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    output = _decode(raw_xml_generator.generate(empty_context).document)

    assert 'xmlns:mml="http://www.w3.org/1998/Math/MathML"' in output
    assert 'xmlns:xlink="http://www.w3.org/1999/xlink"' in output
    assert 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' in output
    assert 'xmlns:ali="http://www.niso.org/schemas/ali/1.0/"' in output


def test_root_attribute_order_matches_real_reference_packages(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    output = _decode(raw_xml_generator.generate(empty_context).document)

    root_line = output.splitlines()[2]
    assert root_line.index("xmlns:mml") < root_line.index("xmlns:xlink")
    assert root_line.index("xmlns:xlink") < root_line.index("xmlns:xsi")
    assert root_line.index("xmlns:xsi") < root_line.index("xmlns:ali")
    assert root_line.index("xmlns:ali") < root_line.index("article-type")
    assert root_line.index("article-type") < root_line.index("dtd-version")
    assert root_line.index("dtd-version") < root_line.index("xml:lang")


def test_article_type_matches_br_040(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(empty_context).document.xml_bytes)

    assert root.get("article-type") == "research-article"


def test_dtd_version_matches_br_049(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(empty_context).document.xml_bytes)

    assert root.get("dtd-version") == "1.3"


def test_xml_lang_matches_br_050(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(empty_context).document.xml_bytes)

    assert root.get("{http://www.w3.org/XML/1998/namespace}lang") == "en"


def test_namespace_uris_come_from_config_not_hard_coded(empty_context: GeneratorContext) -> None:
    custom_manager = NamespaceManager({"xlink": "urn:example:custom-xlink"})
    custom_config = RawXmlConfig(
        doctype_public_id="x",
        doctype_system_id="y",
        article_type="research-article",
        dtd_version="1.3",
        default_xml_lang="en",
        encoding="UTF-8",
        namespace_prefixes=("xlink",),
        pretty_indent_spaces=0,
    )
    generator = RawXmlGenerator(namespace_manager=custom_manager, raw_xml_config=custom_config)

    output = _decode(generator.generate(empty_context).document)

    assert 'xmlns:xlink="urn:example:custom-xlink"' in output
    assert "http://www.w3.org/1999/xlink" not in output


# --- pretty vs compact serialization (BR-044) ---------------------------------


def test_pretty_print_uses_zero_indentation_per_br_044(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(raw_xml_generator.generate(rich_context).document)

    for line in output.splitlines()[3:]:
        if line.strip():
            assert not line.startswith(" "), f"unexpected indentation: {line!r}"


def test_compact_mode_produces_no_newlines_between_elements(
    raw_xml_generator: RawXmlGenerator,
    rich_context: GeneratorContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # BaseGenerator's serialize call is pretty=True by design for raw.xml
    # (BR-044); this test exercises XmlDocumentBuilder's compact mode
    # directly through the same tree the generator builds, confirming the
    # framework component itself (not this generator) owns that toggle.
    from meca_engine.generators.xml.builder import XmlDocumentBuilder

    builder = XmlDocumentBuilder()
    root = builder.create_root("article")
    builder.create_element(root, "front")
    compact = builder.serialize(root, pretty=False).decode("utf-8")

    # Exactly one newline separates the declaration from the (single-line) body.
    assert compact.count("\n") == 1


# --- journal-meta --------------------------------------------------------------


def test_journal_meta_fields_mapped(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    journal_meta = root.find("front/journal-meta")

    assert journal_meta is not None
    assert journal_meta.findtext("journal-id") == "clinical-science"
    assert journal_meta.findtext("journal-title-group/journal-title") == "Journal of Examples"
    assert journal_meta.findtext("journal-title-group/abbrev-journal-title") == "J. Ex."
    issns = {(issn.get("pub-type"), issn.text) for issn in journal_meta.findall("issn")}
    assert issns == {("ppub", "1234-5678"), ("epub", "8765-4321")}
    assert journal_meta.findtext("publisher/publisher-name") == "Example Press"

    journal_ids = {
        (el.get("journal-id-type"), el.text) for el in journal_meta.findall("journal-id")
    }
    assert journal_ids == {("publisher-id", "clinical-science"), ("nlm-ta", "j-ex")}


def test_publication_info_mapped(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    article_meta = root.find("front/article-meta")
    assert article_meta is not None

    pub_dates = {
        (el.get("pub-type"), el.findtext("year"), el.findtext("month"), el.findtext("day"))
        for el in article_meta.findall("pub-date")
    }
    assert pub_dates == {("epub", "2025", "03", "01"), ("ppub", "2025", "03", "15")}
    assert article_meta.findtext("volume") == "12"
    assert article_meta.findtext("issue") == "3"
    assert article_meta.findtext("fpage") == "100"
    assert article_meta.findtext("lpage") == "120"


def test_journal_meta_missing_journal_id_is_diagnosed(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)

    messages = [d.message for d in result.diagnostics]
    assert any("journal-id" in m for m in messages)


# --- article-meta: ids, categories, title ------------------------------------


def test_article_ids_mapped_from_identity(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    article_meta = root.find("front/article-meta")
    assert article_meta is not None

    ids = {(el.get("pub-id-type"), el.text) for el in article_meta.findall("article-id")}
    assert ids == {("publisher-id", "EX-2025-001"), ("doi", "EX-2025-001")}


def test_article_categories_mapped(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    article_meta = root.find("front/article-meta")
    assert article_meta is not None

    display = article_meta.find(
        "article-categories/subj-group[@subj-group-type='display-channel']/subject"
    )
    assert display is not None
    assert display.text == "Research Article"
    heading = article_meta.find("article-categories/subj-group[@subj-group-type='heading']/subject")
    assert heading is not None
    assert heading.text == "Cell Biology"


def test_article_categories_with_only_heading_subjects_omits_display_channel(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    from dataclasses import replace

    no_display_meta = replace(rich_context.model.article_meta, display_channel_subject="")
    no_display_context = replace(
        rich_context, model=replace(rich_context.model, article_meta=no_display_meta)
    )

    root = fromstring(raw_xml_generator.generate(no_display_context).document.xml_bytes)
    article_meta = root.find("front/article-meta")
    assert article_meta is not None

    assert (
        article_meta.find("article-categories/subj-group[@subj-group-type='display-channel']")
        is None
    )
    heading = article_meta.find("article-categories/subj-group[@subj-group-type='heading']/subject")
    assert heading is not None
    assert heading.text == "Cell Biology"


def test_title_group_mapped(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)

    title = root.find("front/article-meta/title-group/article-title")
    assert title is not None
    assert title.text == "A Study of Example Practices"


# --- contributors / affiliations (multiple) -----------------------------------


def test_multiple_affiliations_rendered_with_sequential_aff_ids(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    article_meta = root.find("front/article-meta")
    assert article_meta is not None

    affs = article_meta.findall("aff")
    assert [a.get("id") for a in affs] == ["aff1", "aff2"]
    assert affs[0].findtext("institution") == "University of Example"
    assert affs[0].findtext("country") == "USA"


def test_multiple_contributors_rendered_in_one_contrib_group(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    article_meta = root.find("front/article-meta")
    assert article_meta is not None

    contribs = article_meta.findall("contrib-group/contrib")
    assert len(contribs) == 3
    assert [c.get("contrib-type") for c in contribs] == ["author", "author", "reviewer"]


def test_author_contrib_uses_structured_name(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    contrib = root.find("front/article-meta/contrib-group/contrib[@contrib-type='author']")
    assert contrib is not None

    assert contrib.findtext("name/surname") == "Doe"
    assert contrib.findtext("name/given-names") == "Jane"
    assert contrib.get("corresp") == "yes"
    assert contrib.get("equal-contrib") == "yes"
    assert contrib.findtext("email") == "jane.doe@example.com"
    xref = contrib.find("xref")
    assert xref is not None
    assert xref.get("ref-type") == "aff"
    assert xref.get("rid") == "aff1"


def test_reviewer_contrib_uses_full_name_raw_not_structured_name(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    contrib = root.find("front/article-meta/contrib-group/contrib[@contrib-type='reviewer']")
    assert contrib is not None

    assert contrib.findtext("string-name") == "Alex Reviewer"
    assert contrib.find("name") is None


def test_contributor_suffix_rendered(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    contribs = root.findall("front/article-meta/contrib-group/contrib[@contrib-type='author']")

    assert contribs[1].findtext("name/suffix") == "PhD"


def test_no_contributors_is_diagnosed_and_omits_contrib_group(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)
    root = fromstring(result.document.xml_bytes)

    assert root.find("front/article-meta/contrib-group") is None
    assert any("contributors" in d.message for d in result.diagnostics)


def test_no_affiliations_is_diagnosed(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)

    assert any("affiliations" in d.message for d in result.diagnostics)


# --- author-notes / corresponding emails --------------------------------------


def test_corresponding_email_rendered_in_author_notes(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    corresp = root.find("front/article-meta/author-notes/corresp")

    assert corresp is not None
    assert corresp.get("id") == "cor1"
    email = corresp.find("email")
    assert email is not None
    assert email.text == "jane.doe@example.com"
    assert email.get("{http://www.w3.org/1999/xlink}href") == "jane.doe@example.com"


def test_no_corresponding_email_is_diagnosed(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)
    root = fromstring(result.document.xml_bytes)

    assert root.find("front/article-meta/author-notes") is None
    assert any("corresponding" in d.message for d in result.diagnostics)


# --- history (BR-047) ----------------------------------------------------------


def test_history_dates_copied_verbatim(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    history = root.find("front/article-meta/history")
    assert history is not None

    dates = {d.get("date-type"): d for d in history.findall("date")}
    assert set(dates) == {"received", "revised", "accepted"}
    received = dates["received"]
    assert received.findtext("year") == "2025"
    assert received.findtext("month") == "01"
    assert received.findtext("day") == "10"


def test_no_history_dates_is_diagnosed(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)
    root = fromstring(result.document.xml_bytes)

    assert root.find("front/article-meta/history") is None
    assert any("history" in d.message for d in result.diagnostics)


# --- permissions (BR-045/046) --------------------------------------------------


def test_copyright_statement_preserved_verbatim(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    permissions = root.find("front/article-meta/permissions")
    assert permissions is not None

    assert permissions.findtext("copyright-statement") == "© 2025 The Author(s)."
    assert permissions.findtext("copyright-year") == "2025"


def test_no_license_element_ever_added_br_046(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(raw_xml_generator.generate(rich_context).document)

    assert "<license" not in output


# --- abstracts / keywords / funding / counts ----------------------------------


def test_abstract_text_preserved(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)

    abstract = root.find("front/article-meta/abstract")
    assert abstract is not None
    assert abstract.findtext("p") == "This study examines example practices."


def test_abstract_type_and_language_rendered_when_present(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    from dataclasses import replace

    from meca_engine.model.article import Abstract

    typed_abstract = Abstract(text="Summary.", abstract_type="graphical", language="en")
    typed_meta = replace(rich_context.model.article_meta, abstracts=(typed_abstract,))
    typed_context = replace(
        rich_context, model=replace(rich_context.model, article_meta=typed_meta)
    )

    root = fromstring(raw_xml_generator.generate(typed_context).document.xml_bytes)
    abstract = root.find("front/article-meta/abstract")

    assert abstract is not None
    assert abstract.get("abstract-type") == "graphical"
    assert abstract.get("{http://www.w3.org/XML/1998/namespace}lang") == "en"


def test_no_abstract_is_diagnosed(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)

    assert any(
        d.severity is DiagnosticSeverity.WARNING and "abstract" in d.message
        for d in result.diagnostics
    )


def test_keywords_rendered_in_order(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)

    kwds = [k.text for k in root.findall("front/article-meta/kwd-group/kwd")]
    assert kwds == ["examples", "testing"]


def test_funding_group_rendered(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)

    funding = root.findall("front/article-meta/funding-group")
    assert [f.text for f in funding] == ["Example Foundation Grant 12345"]


def test_counts_rendered(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    counts = root.find("front/article-meta/counts")
    assert counts is not None

    word_count = counts.find("word-count")
    ref_count = counts.find("ref-count")
    fig_count = counts.find("fig-count")
    assert word_count is not None
    assert ref_count is not None
    assert fig_count is not None
    assert word_count.get("count") == "5000"
    assert ref_count.get("count") == "42"
    assert fig_count.get("count") == "3"
    # fig-count, ref-count, word-count — real reference-package order,
    # not source declaration order (Milestone 9 correction).
    assert [child.tag for child in counts] == ["fig-count", "ref-count", "word-count"]


def test_counts_full_ordering_including_table_equation_page(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    from dataclasses import replace

    from meca_engine.model.article import ArticleCounts

    full_meta = replace(
        rich_context.model.article_meta,
        counts=ArticleCounts(
            word_count=5000,
            ref_count=42,
            fig_count=3,
            table_count=2,
            equation_count=1,
            page_count=10,
        ),
    )
    full_context = replace(rich_context, model=replace(rich_context.model, article_meta=full_meta))

    root = fromstring(raw_xml_generator.generate(full_context).document.xml_bytes)
    counts = root.find("front/article-meta/counts")

    assert counts is not None
    assert [child.tag for child in counts] == [
        "fig-count",
        "table-count",
        "equation-count",
        "ref-count",
        "page-count",
        "word-count",
    ]
    table_count = counts.find("table-count")
    equation_count = counts.find("equation-count")
    page_count = counts.find("page-count")
    assert table_count is not None
    assert equation_count is not None
    assert page_count is not None
    assert table_count.get("count") == "2"
    assert equation_count.get("count") == "1"
    assert page_count.get("count") == "10"


def test_partial_counts_render_only_the_present_ones(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    from dataclasses import replace

    from meca_engine.model.article import ArticleCounts

    partial_meta = replace(rich_context.model.article_meta, counts=ArticleCounts(word_count=5000))
    partial_context = replace(
        rich_context, model=replace(rich_context.model, article_meta=partial_meta)
    )

    root = fromstring(raw_xml_generator.generate(partial_context).document.xml_bytes)
    counts = root.find("front/article-meta/counts")

    assert counts is not None
    assert counts.find("word-count") is not None
    assert counts.find("ref-count") is None
    assert counts.find("fig-count") is None


def test_counts_with_only_ref_count_omits_word_count(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    from dataclasses import replace

    from meca_engine.model.article import ArticleCounts

    partial_meta = replace(rich_context.model.article_meta, counts=ArticleCounts(ref_count=42))
    partial_context = replace(
        rich_context, model=replace(rich_context.model, article_meta=partial_meta)
    )

    root = fromstring(raw_xml_generator.generate(partial_context).document.xml_bytes)
    counts = root.find("front/article-meta/counts")

    assert counts is not None
    assert counts.find("word-count") is None
    assert counts.find("ref-count") is not None


def test_no_counts_is_diagnosed(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)
    root = fromstring(result.document.xml_bytes)

    assert root.find("front/article-meta/counts") is None
    assert any("counts" in d.message for d in result.diagnostics)


# --- custom-meta-group (BR-042) reconstruction --------------------------------


def test_custom_meta_group_reconstructed_from_all_categories(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    entries = root.findall("front/article-meta/custom-meta-group/custom-meta")

    names = [e.findtext("meta-name") for e in entries]
    assert "Authorship" in names
    assert "file" in names
    assert any(n is not None and n.startswith("reviewer-scorecard:") for n in names)
    assert "Decision Draft" in names
    assert "reviewer-decline-reason" in names


def test_partial_custom_meta_categories_diagnose_only_missing_ones(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    from dataclasses import replace

    partial_custom_meta = replace(
        rich_context.model.custom_meta,
        file_entries=(),
        reviewer_scorecards=(),
        decline_reasons=(),
    )
    partial_context = replace(
        rich_context, model=replace(rich_context.model, custom_meta=partial_custom_meta)
    )

    result = raw_xml_generator.generate(partial_context)

    messages = [d.message for d in result.diagnostics]
    assert any("file-manifest" in m for m in messages)
    assert any("reviewer scorecard" in m for m in messages)
    assert any("decline-reason" in m for m in messages)


def test_no_custom_meta_information_is_diagnosed(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)
    root = fromstring(result.document.xml_bytes)

    assert root.find("front/article-meta/custom-meta-group") is None
    assert any(
        d.severity is DiagnosticSeverity.WARNING and "custom-meta" in d.message
        for d in result.diagnostics
    )


# --- body (BR-043) --------------------------------------------------------------


def test_body_attached_verbatim_including_ids(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(raw_xml_generator.generate(rich_context).document.xml_bytes)
    body = root.find("body")

    assert body is not None
    assert body.get("id") == "b1"
    assert body.findtext("title") == "Example Title Page"
    body_p = body.find("p")
    assert body_p is not None
    assert body_p.get("id") == "p1"


def test_missing_body_is_diagnosed(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)
    root = fromstring(result.document.xml_bytes)

    assert root.find("body") is None
    assert any(
        d.severity is DiagnosticSeverity.WARNING and "body" in d.message for d in result.diagnostics
    )


# --- back matter (documented ICAM gap) ----------------------------------------


def test_back_matter_always_diagnosed_never_fabricated(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(rich_context)
    root = fromstring(result.document.xml_bytes)

    assert root.find("back") is None
    assert any("<back>" in d.message for d in result.diagnostics)


# --- deterministic ordering ----------------------------------------------------


def test_generation_is_deterministic_across_repeated_calls(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    first = raw_xml_generator.generate(rich_context).document.xml_bytes
    second = raw_xml_generator.generate(rich_context).document.xml_bytes

    assert first == second


# --- malformed ICAM / generator exceptions ------------------------------------


def test_malformed_body_fragment_raises_generator_invariant_error(
    raw_xml_generator: RawXmlGenerator, rich_context: GeneratorContext
) -> None:
    from dataclasses import replace

    broken_model = replace(
        rich_context.model,
        body_fragment=replace(
            rich_context.model.body_fragment, raw_xml_fragment="<body><unclosed>"
        ),
    )
    broken_context = replace(rich_context, model=broken_model)

    with pytest.raises(GeneratorInvariantError) as exc_info:
        raw_xml_generator.generate(broken_context)

    assert exc_info.value.article_id == "cs-2025-0001"
    assert exc_info.value.stage == "generators.raw_xml"


# --- diagnostics do not fail generation ---------------------------------------


def test_every_optional_field_missing_still_produces_a_document(
    raw_xml_generator: RawXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = raw_xml_generator.generate(empty_context)

    assert result.document.xml_bytes
    assert len(result.diagnostics) > 5
    assert all(d.severity is not None for d in result.diagnostics)
