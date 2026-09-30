"""Workflow-level metadata extraction — Milestone 4.

Reads workflow/processing-log event elements out of a
:class:`~meca_engine.extraction.parsed_model.ParsedDocument`, flattening
each one's direct simple-text children generically — never reconstructing
a timeline or narrative, never inferring an event that isn't literally
present. A pure function: no logging, no I/O, no exceptions for missing
fields.

No single confirmed source-system tag name was identified during
analysis for this concept (it is not a standard JATS structure); the
recognized tag names are therefore a caller-overridable parameter with a
documented, best-effort default — see the Milestone 4 Architecture
Compliance Report for this open question.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.extraction.metadata_models import WorkflowEventRecord, WorkflowMetadata
from meca_engine.extraction.navigation import find_all, get_text

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedDocument, ParsedElement, ParseDiagnostic

DEFAULT_EVENT_TAG_NAMES: tuple[str, ...] = ("event", "log-entry", "stage")


def _flatten_simple_children(element: ParsedElement) -> tuple[tuple[str, str], ...]:
    return tuple((child.tag, get_text(child, recursive=True)) for child in element.children)


def extract_workflow_metadata(
    document: ParsedDocument,
    *,
    event_tag_names: tuple[str, ...] = DEFAULT_EVENT_TAG_NAMES,
) -> tuple[WorkflowMetadata, tuple[ParseDiagnostic, ...]]:
    """Extract workflow-level metadata from a parsed document.

    Args:
        document: The parsed document to read from.
        event_tag_names: Which local tag names count as a workflow event.
            Defaults to a documented best-effort set (``"event"``,
            ``"log-entry"``, ``"stage"``) — pass a different set once the
            actual source convention is confirmed.

    Returns:
        The extracted
        :class:`~meca_engine.extraction.metadata_models.WorkflowMetadata`,
        alongside an always-empty diagnostics tuple. No timeline or
        narrative is reconstructed — each event's fields are its direct
        simple-text children, verbatim.
    """
    events = tuple(
        WorkflowEventRecord(
            event_tag=element.tag,
            fields=_flatten_simple_children(element),
            raw_element=element,
        )
        for tag_name in event_tag_names
        for element in find_all(document.root, tag_name)
    )
    return WorkflowMetadata(events=events), ()
