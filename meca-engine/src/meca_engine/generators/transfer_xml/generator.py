"""Transfer XML Generator — produces <ArticleID>_transfer.xml (Business Rule Book §H, BR-126–140).

Implemented in Milestone 6G, reusing the Generator Framework (Milestone
6A) exactly as the 4 prior generators do. Per
11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7: "Emit BR-126–140 exactly,
using config for provider names/acronym and the ICAM's primary
corresponding email." Depends on **no other generator** — only the ICAM
(`model.identity`, `model.journal_meta`, `model.article_meta.corresponding_emails`)
and configuration (`TransferXmlConfig`, `JournalConfig`, `PublisherConfig`,
`NamespaceManager`), matching manifest.xml's and reviews.xml's own
"no generator-to-generator dependency" precedent.

**BR-140: content never varies by round** — satisfied by construction:
this module never reads `model.rounds`, `model.custom_meta`, or any
round-scoped field at all.

**ADR-007 (journal acronym) resolution**: 2 of the 3 real reference
packages use `"CLINSCI"` (present nowhere in any source XML); the third
uses `"CS"` (matching source `abbrev-journal-title`). This cannot be
resolved from evidence alone (ADR-007 is explicitly unresolved,
"Business Confirmation Required: Yes — highest priority"). Per ADR-007's
own recommended fallback (an external per-journal configuration table),
this generator reads `context.journal_config.acronym` — already an
existing, ADR-007-cited field — rather than guessing or hard-coding
either observed value. See `29_TRANSFER_DECISION_LOG.md` for the full
reasoning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.exceptions import GeneratorInvariantError
from meca_engine.generators.base import BaseGenerator
from meca_engine.generators.transfer_xml.document import TransferXmlDocument
from meca_engine.generators.xml.builder import DoctypeDeclaration, XmlDocumentBuilder
from meca_engine.generators.xml.helpers import add_optional_element

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import TransferXmlConfig
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.namespaces import NamespaceManager
    from meca_engine.model.article import ArticleMeta

_GENERATOR_NAME = "transfer_xml"
_TRANSFER_NAMESPACE_PREFIX = "meca-transfer"
_EXPECTED_PROCESSING_INSTRUCTION_COUNT = 2


class TransferXmlGenerator(BaseGenerator[TransferXmlDocument]):
    """Generates transfer.xml from the ICAM. See module docstring for BR traceability."""

    def __init__(
        self,
        *,
        namespace_manager: NamespaceManager,
        transfer_xml_config: TransferXmlConfig,
    ) -> None:
        """Initialize the generator.

        Args:
            namespace_manager: Resolves BR-126's default namespace.
            transfer_xml_config: BR-126/127/136/137/138/139's externalized constants.
        """
        self._namespace_manager = namespace_manager
        self._config = transfer_xml_config

    @property
    def generator_name(self) -> str:
        """This generator's stable name, ``"transfer_xml"``."""
        return _GENERATOR_NAME

    def _generate(self, context: GeneratorContext) -> TransferXmlDocument:
        model = context.model
        config = self._config
        diagnostics = context.diagnostics

        self._check_configuration(context, diagnostics)

        builder = XmlDocumentBuilder()
        root = builder.create_root(
            "transfer",
            attributes={
                "xmlns": self._require_uri(_TRANSFER_NAMESPACE_PREFIX),
                "transfer-version": config.transfer_version,  # BR-126: constant root attribute
            },
        )

        primary_email = self._primary_corresponding_email(model.article_meta, diagnostics)

        builder.add_comment(root, config.source_section_comment)
        self._build_transfer_source(builder, root, context, primary_email, diagnostics)

        builder.add_comment(root, config.destination_section_comment)
        self._build_destination(builder, root, context, diagnostics)

        builder.add_comment(root, config.instructions_section_comment)
        self._build_processing_instructions(builder, root, model.identity.article_id, diagnostics)

        xml_bytes = builder.serialize(
            root,
            pretty=True,
            encoding=None,  # BR-127: no encoding attribute in the XML declaration
            indent_spaces=config.pretty_indent_spaces,
            doctype=DoctypeDeclaration(  # BR-126
                root_tag="transfer",
                public_id=config.doctype_public_id,
                system_id=config.doctype_system_id,
            ),
        )

        return TransferXmlDocument(
            article_id=model.identity.article_id,
            filename=config.transfer_filename_pattern.format(  # BR-139
                article_id=model.identity.article_id
            ),
            xml_bytes=xml_bytes,
        )

    def _require_uri(self, prefix: str) -> str:
        uri = self._namespace_manager.uri_for(prefix)
        if uri is None:
            raise GeneratorInvariantError(
                f"Namespace prefix {prefix!r} is not registered in the namespace configuration",
                stage=_GENERATOR_NAME,
            )
        return uri

    def _check_configuration(
        self, context: GeneratorContext, diagnostics: DiagnosticsCollector
    ) -> None:
        config = self._config
        if not context.publisher_config.provider_name:
            diagnostics.warn(_GENERATOR_NAME, "PublisherConfig.provider_name is empty (BR-128)")
        if not context.publisher_config.destination_provider_name:
            diagnostics.warn(
                _GENERATOR_NAME,
                "PublisherConfig.destination_provider_name is empty (BR-134) — "
                "no destination service-provider name available",
            )
        if not context.journal_config.acronym:
            diagnostics.warn(
                _GENERATOR_NAME, "JournalConfig.acronym is empty (BR-133/135, ADR-007)"
            )
        if len(config.processing_instructions) != _EXPECTED_PROCESSING_INSTRUCTION_COUNT:
            diagnostics.warn(
                _GENERATOR_NAME,
                f"Configured processing_instructions has "
                f"{len(config.processing_instructions)} entries; BR-137 expects exactly "
                f"{_EXPECTED_PROCESSING_INSTRUCTION_COUNT} — unsupported transfer value",
            )

    def _primary_corresponding_email(
        self, article_meta: ArticleMeta, diagnostics: DiagnosticsCollector
    ) -> str:
        corresponding_emails = article_meta.corresponding_emails
        if not corresponding_emails:
            diagnostics.warn(
                _GENERATOR_NAME,
                "No corresponding-author email available (BR-130) — missing source contact",
            )
            return ""
        return corresponding_emails[0].email

    def _build_transfer_source(
        self,
        builder: XmlDocumentBuilder,
        root: Element,
        context: GeneratorContext,
        primary_email: str,
        diagnostics: DiagnosticsCollector,
    ) -> None:
        config = self._config
        source = builder.create_element(root, "transfer-source")
        service_provider = builder.create_element(source, "service-provider")
        builder.create_element(  # BR-128
            service_provider, "provider-name", text=context.publisher_config.provider_name or None
        )
        contact = builder.create_element(service_provider, "contact")
        contact_name = builder.create_element(contact, "contact-name")  # BR-129: always empty
        builder.create_element(contact_name, "surname")
        builder.create_element(contact_name, "given-names")
        builder.create_element(contact, "email", text=primary_email or None)  # BR-130
        builder.create_element(contact, "phone")  # BR-131: always empty

        if not context.model.journal_meta.journal_title:
            diagnostics.warn(
                _GENERATOR_NAME,
                "JournalMeta.journal_title is empty (BR-132) — missing transfer metadata",
            )
        publication = builder.create_element(
            source, "publication", attributes={"type": config.publication_type}
        )
        builder.create_element(  # BR-132
            publication, "publication-title", text=context.model.journal_meta.journal_title or None
        )
        builder.create_element(publication, "acronym", text=context.journal_config.acronym or None)
        publication_contact = builder.create_element(publication, "contact")
        builder.create_element(publication_contact, "email", text=primary_email or None)  # BR-130

    def _build_destination(
        self,
        builder: XmlDocumentBuilder,
        root: Element,
        context: GeneratorContext,
        diagnostics: DiagnosticsCollector,
    ) -> None:
        config = self._config
        destination = builder.create_element(root, "destination")
        service_provider = builder.create_element(destination, "service-provider")
        builder.create_element(  # BR-134
            service_provider,
            "provider-name",
            text=context.publisher_config.destination_provider_name or None,
        )

        publication = builder.create_element(  # BR-135
            destination, "publication", attributes={"type": config.publication_type}
        )
        builder.create_element(
            publication, "publication-title", text=context.model.journal_meta.journal_title or None
        )
        builder.create_element(publication, "acronym", text=context.journal_config.acronym or None)

        security = builder.create_element(destination, "security")
        publisher_id_value = context.model.identity.publisher_id_value
        if not publisher_id_value:
            diagnostics.warn(
                _GENERATOR_NAME,
                "ArticleIdentity.publisher_id_value is empty (BR-136) — incomplete identifiers",
            )
        authentication_code = config.authentication_code_separator.join(
            (publisher_id_value, publisher_id_value)
        )
        builder.create_element(security, "authentication-code", text=authentication_code)

    def _build_processing_instructions(
        self,
        builder: XmlDocumentBuilder,
        root: Element,
        article_id: str,
        diagnostics: DiagnosticsCollector,
    ) -> None:
        config = self._config
        instructions = builder.create_element(root, "processing-instructions")
        for sequence, step_text in enumerate(config.processing_instructions, start=1):
            builder.create_element(
                instructions,
                "processing-instruction",
                attributes={"processing-sequence": str(sequence)},
                text=step_text,
            )
        add_optional_element(
            builder,
            instructions,
            "processing-comments",
            config.processing_comments_template.format(  # BR-138
                raw_xml_filename=config.raw_xml_filename_pattern.format(article_id=article_id)
            ),
        )
