"""Typed collection aliases used by the Internal Canonical Article Model.

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §3.2-3.6 and
10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.1's package sketch (``model/collections.py``:
"typed collections: ContributorList, FileEntryList, ReviewEventList"). Every
alias is a plain immutable ``tuple`` — never a ``list`` — so no generator
can accidentally mutate shared state (11_LLD_02... §3.7).

Type-checking-only: each alias exists purely so ``model/article.py``'s
dataclass fields can carry a descriptive annotation
(``contributors: ContributorList``) instead of a bare
``tuple[Contributor, ...]`` repeated at every use site. Every field
annotation in this codebase is a deferred string (``from __future__ import
annotations`` is active everywhere), so none of these aliases needs a
runtime value — importing ``meca_engine.model.article`` at runtime never
touches this module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meca_engine.model.article import (
        Affiliation,
        Contributor,
        CorrespondenceEvent,
        FileEntry,
        ResolvedFile,
        RoundInfo,
    )

    # Plain (unannotated) alias assignments, not `X: TypeAlias = ...` —
    # ruff's UP040 otherwise suggests the Python 3.12+-only `type X = ...`
    # statement syntax, which this codebase avoids (see pyproject.toml's
    # documented UP042/UP017 rationale for the same 3.9-compat reason).
    ContributorList = tuple[Contributor, ...]
    AffiliationList = tuple[Affiliation, ...]
    FundingList = tuple[str, ...]
    RoundIndex = tuple[RoundInfo, ...]
    ResolvedFileList = tuple[ResolvedFile, ...]
    FileEntryList = tuple[FileEntry, ...]
    ReviewEventList = tuple[CorrespondenceEvent, ...]
