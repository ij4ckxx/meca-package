"""Supplementary, forward-looking Milestone 5B builder interface sketches.

**Not part of 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md's own class design.**
The LLD specifies exactly one concrete builder,
:class:`meca_engine.model.article.ArticleModelBuilder` (§4.1), fed by four
extraction-stage classes (§4.2-4.5: `KriyadocsParser`,
`CustomMetaClassifier`, `RoundResolver`, `FileResolver`) that each produce
an already-built sub-object and hand it to one of the builder's setters —
there is no per-domain "sub-builder" class in the approved LLD.

This module exists solely because the current milestone's task explicitly
requested named, interface-only builder contracts per domain
(`ArticleBuilder`, `ContributorBuilder`, `WorkflowBuilder`,
`JournalBuilder`, `AssetBuilder`) as a Milestone 5B preview. Each is a
plain `typing.Protocol` — structural typing, zero implementation, and
**not wired into anything**: `ArticleModelBuilder` is not declared to
implement `ArticleBuilder` (it satisfies it structurally, automatically,
by having matching method signatures — no inheritance edge is added).
Deleting this entire module has zero effect on any other package; it is
documentation-as-code, not load-bearing architecture. Milestone 5B's
actual implementation is free to use these Protocols, ignore them
entirely, or replace them — whichever the extraction-stage class design
that milestone approves turns out to need.

Every input parameter below is deliberately typed as `object` rather than
importing any `extraction.*` type: `model` is a foundation-layer package
(10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.1) and must not depend on
anything above it, including `extraction` — see that document's import-
direction rules. Milestone 5B's real implementation will narrow these to
whatever concrete extraction-stage input types it actually needs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from meca_engine.model.article import (
        ArticleModel,
        Contributor,
        JournalMeta,
        ResolvedFile,
        WorkflowLog,
    )


@runtime_checkable
class ArticleBuilder(Protocol):
    """Structural mirror of `ArticleModelBuilder`'s public interface.

    Documented separately from the concrete class purely so a future
    Milestone 5B coordinator can type a parameter against this Protocol
    (e.g. for a test double) without importing the concrete builder.
    """

    def set_identity(self, identity: object, /) -> None:
        """Set the article's identity. May be called at most once."""
        ...

    def set_journal_meta(self, journal_meta: object, /) -> None:
        """Set the article's journal metadata. May be called at most once."""
        ...

    def set_article_meta(self, article_meta: object, /) -> None:
        """Set the article's own metadata. May be called at most once."""
        ...

    def set_body_fragment(self, body_fragment: object, /) -> None:
        """Set the article's body fragment. May be called at most once."""
        ...

    def set_custom_meta(self, store: object, /) -> None:
        """Set the article's custom-metadata store. May be called at most once."""
        ...

    def set_rounds(self, index: object, /) -> None:
        """Set the article's round index. May be called at most once."""
        ...

    def set_resolved_files(self, files: object, /) -> None:
        """Set the article's resolved file list. May be called at most once."""
        ...

    def freeze(self) -> ArticleModel:
        """Produce the frozen `ArticleModel`."""
        ...


@runtime_checkable
class ContributorBuilder(Protocol):
    """Milestone 5B preview: builds the author/affiliation portion of `ArticleMeta`."""

    def build(self, raw_contributor_data: object, /) -> tuple[Contributor, ...]:
        """Build the article's ordered `ContributorList` from raw extraction data."""
        ...


@runtime_checkable
class JournalBuilder(Protocol):
    """Milestone 5B preview: builds `JournalMeta` from extracted journal metadata."""

    def build(self, raw_journal_data: object, /) -> JournalMeta:
        """Build the article's `JournalMeta` from raw extraction data."""
        ...


@runtime_checkable
class WorkflowBuilder(Protocol):
    """Milestone 5B preview: builds `WorkflowLog` from classified custom-meta correspondence."""

    def build(self, raw_workflow_data: object, /) -> WorkflowLog:
        """Build the article's `WorkflowLog` from raw extraction data."""
        ...


@runtime_checkable
class AssetBuilder(Protocol):
    """Milestone 5B preview: builds `ResolvedFileList` entries from resolved staged files."""

    def build(self, raw_asset_data: object, /) -> tuple[ResolvedFile, ...]:
        """Build the article's `ResolvedFileList` from raw extraction data."""
        ...
