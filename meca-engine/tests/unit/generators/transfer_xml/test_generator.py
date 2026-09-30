"""Unit tests for meca_engine.generators.transfer_xml.generator.TransferXmlGenerator."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from xml.etree.ElementTree import fromstring

import pytest

from meca_engine.exceptions import GeneratorInvariantError
from meca_engine.generators.result import GenerationResult
from meca_engine.generators.transfer_xml.generator import TransferXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.model.article import CorrespEmail

if TYPE_CHECKING:
    from meca_engine.config.schema import (
        JournalConfig,
        PublisherConfig,
        TransferXmlConfig,
    )
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.transfer_xml.document import TransferXmlDocument

pytestmark = pytest.mark.unit

_NS = {"t": "https://manuscriptexchange.org/schema/transfer"}


def _decode(document: TransferXmlDocument) -> str:
    return document.xml_bytes.decode("utf-8")


# --- lifecycle / framework usage ----------------------------------------------


def test_generator_name_is_transfer_xml(transfer_xml_generator: TransferXmlGenerator) -> None:
    assert transfer_xml_generator.generator_name == "transfer_xml"


def test_generate_returns_a_generation_result(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = transfer_xml_generator.generate(rich_context)

    assert isinstance(result, GenerationResult)
    assert result.article_id == "cs-2025-0001"
    assert result.generator_name == "transfer_xml"
    assert result.duration_ms >= 0


def test_filename_matches_br_139_pattern(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = transfer_xml_generator.generate(rich_context)

    assert result.document.filename == "cs-2025-0001_transfer.xml"


def test_output_is_well_formed_xml(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = transfer_xml_generator.generate(rich_context)

    fromstring(result.document.xml_bytes)  # raises if not well-formed


# --- root / DOCTYPE / declaration (BR-126/127) ----------------------------------


def test_xml_declaration_has_no_encoding_attribute_br_127(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(transfer_xml_generator.generate(rich_context).document)

    assert output.startswith('<?xml version="1.0"?>')
    assert "encoding" not in output.splitlines()[0]


def test_doctype_matches_br_126(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(transfer_xml_generator.generate(rich_context).document)

    assert (
        '<!DOCTYPE transfer PUBLIC "-//MECA//DTD Transfer v1.0//en" "./schema/transfer-1.0.dtd">'
        in output
    )


def test_root_declares_default_namespace_and_version(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    assert root.tag == "{https://manuscriptexchange.org/schema/transfer}transfer"
    assert root.get("transfer-version") == "1.0"


def test_unregistered_namespace_raises_generator_invariant_error(
    transfer_xml_config: TransferXmlConfig, rich_context: GeneratorContext
) -> None:
    generator = TransferXmlGenerator(
        namespace_manager=NamespaceManager({}), transfer_xml_config=transfer_xml_config
    )

    with pytest.raises(GeneratorInvariantError):
        generator.generate(rich_context)


def test_output_uses_two_space_indentation(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(transfer_xml_generator.generate(rich_context).document)

    assert "\n  <transfer-source>" in output


def test_section_comments_present(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(transfer_xml_generator.generate(rich_context).document)

    assert "<!-- ======== SOURCE ======== -->" in output
    assert "<!-- ======== DESTINATION ======== -->" in output
    assert "<!-- ======== INSTRUCTIONS & PROVENANCE ======== -->" in output


# --- transfer-source (BR-128/129/130/131/132/133) -------------------------------


def test_source_provider_name_matches_br_128(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    provider_name = root.findtext(
        "t:transfer-source/t:service-provider/t:provider-name", namespaces=_NS
    )
    assert provider_name == "Portland Press Limited"


def test_source_contact_name_is_always_empty_br_129(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    contact_name = root.find(
        "t:transfer-source/t:service-provider/t:contact/t:contact-name", namespaces=_NS
    )
    assert contact_name is not None
    surname = contact_name.find("t:surname", namespaces=_NS)
    given_names = contact_name.find("t:given-names", namespaces=_NS)
    assert surname is not None
    assert given_names is not None
    assert not surname.text
    assert not given_names.text


def test_source_and_publication_contact_email_matches_corresponding_author_br_130(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    source_email = root.findtext(
        "t:transfer-source/t:service-provider/t:contact/t:email", namespaces=_NS
    )
    publication_email = root.findtext(
        "t:transfer-source/t:publication/t:contact/t:email", namespaces=_NS
    )
    assert source_email == publication_email == "jane@example.com"


def test_source_contact_phone_is_always_empty_br_131(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    phone = root.find("t:transfer-source/t:service-provider/t:contact/t:phone", namespaces=_NS)
    assert phone is not None
    assert not phone.text


def test_publication_title_matches_journal_title_br_132(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    title = root.findtext("t:transfer-source/t:publication/t:publication-title", namespaces=_NS)
    assert title == "Journal of Examples"


def test_publication_acronym_comes_from_journal_config_br_133(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    acronym = root.findtext("t:transfer-source/t:publication/t:acronym", namespaces=_NS)
    assert acronym == "CLINSCI"


def test_publication_type_is_configured_not_hardcoded(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    publication = root.find("t:transfer-source/t:publication", namespaces=_NS)
    assert publication is not None
    assert publication.get("type") == "journal"


# --- destination (BR-134/135/136) -----------------------------------------------


def test_destination_provider_name_matches_br_134(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    provider_name = root.findtext(
        "t:destination/t:service-provider/t:provider-name", namespaces=_NS
    )
    assert provider_name == "Silverchair"


def test_destination_publication_mirrors_source_br_135(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    source_title = root.findtext(
        "t:transfer-source/t:publication/t:publication-title", namespaces=_NS
    )
    dest_title = root.findtext("t:destination/t:publication/t:publication-title", namespaces=_NS)
    source_acronym = root.findtext("t:transfer-source/t:publication/t:acronym", namespaces=_NS)
    dest_acronym = root.findtext("t:destination/t:publication/t:acronym", namespaces=_NS)
    assert source_title == dest_title
    assert source_acronym == dest_acronym


def test_authentication_code_matches_br_136(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    auth_code = root.findtext("t:destination/t:security/t:authentication-code", namespaces=_NS)
    assert auth_code == "CS20250001|CS20250001"


# --- processing instructions (BR-137/138) ---------------------------------------


def test_processing_instructions_matches_br_137(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    steps = root.findall("t:processing-instructions/t:processing-instruction", namespaces=_NS)
    assert [(s.get("processing-sequence"), s.text) for s in steps] == [
        ("1", "Validate Metadata"),
        ("2", "Ingest Article Package"),
    ]


def test_processing_comments_matches_br_138(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(transfer_xml_generator.generate(rich_context).document.xml_bytes)

    comments = root.findtext("t:processing-instructions/t:processing-comments", namespaces=_NS)
    assert comments == "Generated automatically from source JATS: cs-2025-0001_raw.xml"


# --- BR-140: content never varies by round --------------------------------------


def test_output_never_references_rounds_or_custom_meta(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(transfer_xml_generator.generate(rich_context).document)

    assert "round" not in output.lower()


# --- diagnostics / missing data --------------------------------------------------


def test_missing_corresponding_email_is_diagnosed_missing_source(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    context = replace(
        rich_context,
        model=replace(
            rich_context.model,
            article_meta=replace(rich_context.model.article_meta, corresponding_emails=()),
        ),
    )

    result = transfer_xml_generator.generate(context)

    assert any("No corresponding-author email" in d.message for d in result.diagnostics)
    root = fromstring(result.document.xml_bytes)
    email = root.find("t:transfer-source/t:service-provider/t:contact/t:email", namespaces=_NS)
    assert email is not None
    assert not email.text


def test_multiple_corresponding_emails_uses_the_primary_one(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    context = replace(
        rich_context,
        model=replace(
            rich_context.model,
            article_meta=replace(
                rich_context.model.article_meta,
                corresponding_emails=(
                    CorrespEmail(email="primary@example.com"),
                    CorrespEmail(email="secondary@example.com"),
                ),
            ),
        ),
    )

    root = fromstring(transfer_xml_generator.generate(context).document.xml_bytes)

    email = root.findtext("t:transfer-source/t:service-provider/t:contact/t:email", namespaces=_NS)
    assert email == "primary@example.com"


def test_missing_journal_title_is_diagnosed(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    context = replace(
        rich_context,
        model=replace(
            rich_context.model,
            journal_meta=replace(rich_context.model.journal_meta, journal_title=""),
        ),
    )

    result = transfer_xml_generator.generate(context)

    assert any("journal_title is empty" in d.message for d in result.diagnostics)


def test_missing_publisher_id_is_diagnosed_incomplete_identifiers(
    transfer_xml_generator: TransferXmlGenerator, rich_context: GeneratorContext
) -> None:
    context = replace(
        rich_context,
        model=replace(
            rich_context.model,
            identity=replace(rich_context.model.identity, publisher_id_value=""),
        ),
    )

    result = transfer_xml_generator.generate(context)

    assert any("incomplete identifiers" in d.message for d in result.diagnostics)
    root = fromstring(result.document.xml_bytes)
    auth_code = root.findtext("t:destination/t:security/t:authentication-code", namespaces=_NS)
    assert auth_code == "|"


def test_missing_provider_name_is_diagnosed(
    transfer_xml_generator: TransferXmlGenerator,
    rich_context: GeneratorContext,
    minimal_publisher_config: PublisherConfig,
) -> None:
    context = replace(
        rich_context, publisher_config=replace(minimal_publisher_config, provider_name="")
    )

    result = transfer_xml_generator.generate(context)

    assert any("provider_name is empty" in d.message for d in result.diagnostics)


def test_missing_destination_provider_name_is_diagnosed(
    transfer_xml_generator: TransferXmlGenerator,
    rich_context: GeneratorContext,
    minimal_publisher_config: PublisherConfig,
) -> None:
    context = replace(
        rich_context,
        publisher_config=replace(minimal_publisher_config, destination_provider_name=""),
    )

    result = transfer_xml_generator.generate(context)

    assert any("destination_provider_name is empty" in d.message for d in result.diagnostics)


def test_missing_acronym_is_diagnosed(
    transfer_xml_generator: TransferXmlGenerator,
    rich_context: GeneratorContext,
    minimal_journal_config: JournalConfig,
) -> None:
    context = replace(rich_context, journal_config=replace(minimal_journal_config, acronym=""))

    result = transfer_xml_generator.generate(context)

    assert any("acronym is empty" in d.message for d in result.diagnostics)


def test_unexpected_processing_instruction_count_is_diagnosed(
    namespace_manager: NamespaceManager,
    transfer_xml_config: TransferXmlConfig,
    rich_context: GeneratorContext,
) -> None:
    bad_config = replace(transfer_xml_config, processing_instructions=("Only One Step",))
    generator = TransferXmlGenerator(
        namespace_manager=namespace_manager, transfer_xml_config=bad_config
    )

    result = generator.generate(rich_context)

    assert any("unsupported transfer value" in d.message for d in result.diagnostics)


def test_every_optional_field_missing_still_produces_a_document(
    transfer_xml_generator: TransferXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = transfer_xml_generator.generate(empty_context)

    assert result.document.xml_bytes
    fromstring(result.document.xml_bytes)
    assert len(result.diagnostics) >= 3
