"""Extension-to-MIME-type resolution — shared foundation-layer helper.

Per 10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.1: ``utils/`` is dependency-free
and importable by both `extraction` (Milestone 5B's `file_resolver.py`)
and `generators` (Milestone 6D's `manifest_xml/generator.py`) without
either layer importing the other — the one place this specific lookup
logic lives, rather than being duplicated on each side of that boundary.
Contains no business logic beyond the lookup itself.
"""

from __future__ import annotations

from pathlib import PurePath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meca_engine.config.schema import MediaTypeConfig


def resolve_media_type(filename: str, media_type_config: MediaTypeConfig) -> tuple[str, bool]:
    """Resolve ``filename``'s extension to a MIME type via ``media_type_config``.

    Args:
        filename: A filename or path; only its extension is consulted.
        media_type_config: Extension-to-MIME-type mapping (ADR-008/009).

    Returns:
        A ``(media_type, matched)`` pair — ``matched`` is ``True`` when
        the extension was found in ``media_type_config.mappings``,
        ``False`` when ``media_type_config.unmapped_extension_default``
        was used instead, letting a caller diagnose the fallback case
        without re-deriving it independently.
    """
    extension = PurePath(filename).suffix.lower()
    media_type = media_type_config.mappings.get(extension)
    if media_type is not None:
        return media_type, True
    return media_type_config.unmapped_extension_default, False
