"""Test-only helper: serialize an ExtractionBundle into a JSON-comparable dict.

Not a test module itself (no ``test_`` prefix — pytest will not collect
it). Used by ``test_metadata_golden_snapshots.py`` to compare a
freshly-extracted metadata bundle's structure against a checked-in golden
JSON file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meca_engine.extraction.file_relationships import FileReference
    from meca_engine.extraction.metadata_models import (
        AbstractRecord,
        AffiliationRecord,
        ArticleIdentifier,
        ArticleMetadata,
        AssetMetadata,
        AssetRecord,
        ContributorMetadata,
        ContributorRecord,
        CrossReferenceMap,
        CustomMetadata,
        CustomMetaEntry,
        DateRecord,
        ExtractionBundle,
        JournalMetadata,
        NamedContentField,
        ReferenceRecord,
        WorkflowEventRecord,
        WorkflowMetadata,
    )


def _identifier_to_dict(identifier: ArticleIdentifier) -> dict[str, Any]:
    return {"id_type": identifier.id_type, "value": identifier.value}


def _date_to_dict(date: DateRecord) -> dict[str, Any]:
    return {
        "date_type": date.date_type,
        "year": date.year,
        "month": date.month,
        "day": date.day,
    }


def _abstract_to_dict(abstract: AbstractRecord) -> dict[str, Any]:
    return {
        "text": abstract.text,
        "abstract_type": abstract.abstract_type,
        "language": abstract.language,
    }


def article_metadata_to_dict(article: ArticleMetadata) -> dict[str, Any]:
    """Convert one ArticleMetadata to a JSON-safe dict."""
    return {
        "identifiers": [_identifier_to_dict(i) for i in article.identifiers],
        "title": article.title,
        "subtitle": article.subtitle,
        "article_type": article.article_type,
        "publication_status": article.publication_status,
        "language": article.language,
        "history_dates": [_date_to_dict(d) for d in article.history_dates],
        "pub_dates": [_date_to_dict(d) for d in article.pub_dates],
        "display_channel_subject": article.display_channel_subject,
        "heading_subjects": list(article.heading_subjects),
        "copyright_statement": article.copyright_statement,
        "copyright_year": article.copyright_year,
        "keywords": list(article.keywords),
        "funding_statements": list(article.funding_statements),
        "word_count": article.word_count,
        "ref_count": article.ref_count,
        "fig_count": article.fig_count,
        "abstracts": [_abstract_to_dict(a) for a in article.abstracts],
    }


def _affiliation_to_dict(affiliation: AffiliationRecord) -> dict[str, Any]:
    return {
        "element_id": affiliation.element_id,
        "label": affiliation.label,
        "department": affiliation.department,
        "institution": affiliation.institution,
        "city": affiliation.city,
        "state": affiliation.state,
        "country": affiliation.country,
        "raw_text": affiliation.raw_text,
    }


def _contributor_to_dict(contributor: ContributorRecord) -> dict[str, Any]:
    return {
        "contrib_type": contributor.contrib_type,
        "surname": contributor.surname,
        "given_names": contributor.given_names,
        "orcid": contributor.orcid,
        "emails": list(contributor.emails),
        "affiliation_ref_ids": list(contributor.affiliation_ref_ids),
        "is_corresponding": contributor.is_corresponding,
        "suffix": contributor.suffix,
        "equal_contrib": contributor.equal_contrib,
    }


def contributor_metadata_to_dict(contributors: ContributorMetadata) -> dict[str, Any]:
    """Convert one ContributorMetadata to a JSON-safe dict."""
    return {
        "authors": [_contributor_to_dict(c) for c in contributors.authors],
        "editors": [_contributor_to_dict(c) for c in contributors.editors],
        "other_contributors": [_contributor_to_dict(c) for c in contributors.other_contributors],
        "affiliations": [_affiliation_to_dict(a) for a in contributors.affiliations],
    }


def journal_metadata_to_dict(journal: JournalMetadata) -> dict[str, Any]:
    """Convert one JournalMetadata to a JSON-safe dict."""
    return {
        "journal_title": journal.journal_title,
        "journal_id": journal.journal_id,
        "issns": [list(pair) for pair in journal.issns],
        "publisher_name": journal.publisher_name,
        "volume": journal.volume,
        "issue": journal.issue,
        "fpage": journal.fpage,
        "lpage": journal.lpage,
        "elocation_id": journal.elocation_id,
        "doi_related_ids": list(journal.doi_related_ids),
        "abbrev_titles": [list(pair) for pair in journal.abbrev_titles],
    }


def _workflow_event_to_dict(event: WorkflowEventRecord) -> dict[str, Any]:
    return {
        "event_tag": event.event_tag,
        "fields": [list(pair) for pair in event.fields],
    }


def workflow_metadata_to_dict(workflow: WorkflowMetadata) -> dict[str, Any]:
    """Convert one WorkflowMetadata to a JSON-safe dict."""
    return {"events": [_workflow_event_to_dict(e) for e in workflow.events]}


def _named_content_to_dict(named_content: NamedContentField) -> dict[str, Any]:
    return {"content_type": named_content.content_type, "text": named_content.text}


def _custom_entry_to_dict(entry: CustomMetaEntry) -> dict[str, Any]:
    return {
        "name": entry.name,
        "value_text": entry.value_text,
        "named_content": [_named_content_to_dict(n) for n in entry.named_content],
        "attributes": [list(pair) for pair in entry.attributes],
    }


def custom_metadata_to_dict(custom: CustomMetadata) -> dict[str, Any]:
    """Convert one CustomMetadata to a JSON-safe dict."""
    return {"entries": [_custom_entry_to_dict(e) for e in custom.entries]}


def _file_reference_to_dict(reference: FileReference) -> dict[str, Any]:
    return {
        "referencing_tag": reference.referencing_tag,
        "attribute_name": reference.attribute_name,
        "value": reference.value,
    }


def _asset_to_dict(asset: AssetRecord) -> dict[str, Any]:
    return {
        "asset_tag": asset.asset_tag,
        "element_id": asset.element_id,
        "label": asset.label,
        "file_references": [_file_reference_to_dict(f) for f in asset.file_references],
    }


def asset_metadata_to_dict(assets: AssetMetadata) -> dict[str, Any]:
    """Convert one AssetMetadata to a JSON-safe dict."""
    return {"assets": [_asset_to_dict(a) for a in assets.assets]}


def _reference_to_dict(reference: ReferenceRecord) -> dict[str, Any]:
    return {
        "referencing_tag": reference.referencing_tag,
        "referencing_ref_type": reference.referencing_ref_type,
        "attribute_name": reference.attribute_name,
        "target_ids": list(reference.target_ids),
    }


def cross_reference_map_to_dict(cross_references: CrossReferenceMap) -> dict[str, Any]:
    """Convert one CrossReferenceMap to a JSON-safe dict."""
    return {
        "id_index": sorted(list(pair) for pair in cross_references.id_index),
        "references": [_reference_to_dict(r) for r in cross_references.references],
    }


def extraction_bundle_to_snapshot_dict(bundle: ExtractionBundle) -> dict[str, Any]:
    """Convert a complete ExtractionBundle to a JSON-safe, order-stable dict."""
    return {
        "article": article_metadata_to_dict(bundle.article),
        "contributors": contributor_metadata_to_dict(bundle.contributors),
        "journal": journal_metadata_to_dict(bundle.journal),
        "workflow": workflow_metadata_to_dict(bundle.workflow),
        "custom": custom_metadata_to_dict(bundle.custom),
        "assets": asset_metadata_to_dict(bundle.assets),
        "cross_references": cross_reference_map_to_dict(bundle.cross_references),
        "diagnostics": [
            {"severity": d.severity.value, "category": d.category.value, "message": d.message}
            for d in bundle.diagnostics
        ],
    }
