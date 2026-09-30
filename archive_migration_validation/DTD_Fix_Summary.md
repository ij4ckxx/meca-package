# DTD Fix Summary — Specification-Alignment Milestone

Every DTD finding across the full 37-article corpus was individually
investigated and classified into Category A–E *before* any code was
touched (see `Remaining_Validation_Issues.md`, `Proposed_Business_Rules.md`,
`Proposed_Recovery_Rules.md` for B/C/D/E). Only Category A (Safe Engine
Defect) issues were fixed. Nothing else was changed.

## Category A fixes implemented

### 1. Duplicate empty `aff` stubs (9/37 articles)

**Finding**: 16/37 articles carry a second `<aff>` sharing an
already-used id, always nested inside a per-contributor
`<contrib-group>` (a source authoring-tool artifact — confirmed by
direct inspection, not a top-level article-meta sibling as first
assumed). Checked every one of the 16 individually: 9 are a
content-free stub (`<aff id="aff1"><label>1</label></aff>`, nothing
else), the other 7 carry a genuinely different institution's address
under the same id.

**Fix**: only the 9 confirmed-empty stubs are dropped. `generators/article_xml/generator.py`'s
new `_drop_duplicate_empty_aff_stubs()` walks the fully-assembled
`article_meta` tree (catching both top-level and contrib-group-nested
`aff`), keeps every id's first occurrence, and drops a later one only
when `_is_empty_aff_stub()` confirms it adds no institution/address
text beyond a repeated `<label>`. The other 7 are left untouched —
see `Remaining_Validation_Issues.md`.

**Result**: "ID aff1 already defined" dropped from 16/37 to 7/37 articles.

### 2. Corrupted internal id on journal-meta (1/37 articles)

**Finding**: `cs-2025-5853_C`'s `journal-meta` (and its
`journal-title-group`/`abbrev-journal-title`/`issn` descendants) carry
a mangled, non-hex "UUID" (e.g. `40f760rd-15b0-42bf-bbe7-6f82025849ae`)
that (a) fails `_UUID_ID_PATTERN`'s strict hex match, so BR-054's
existing strip never touched it, and (b) starts with a digit, which
XML's `Name` production forbids — invalidating the DTD. Confirmed
corpus-wide that no `journal-meta` id, well-formed or corrupted, is
ever a cross-reference target anywhere in this pipeline's output.

**Fix**: `_copy_journal_meta()` now strips **every** `id` attribute
inside `journal-meta` unconditionally (via the existing, already-generic
`strip_attribute()` helper), not just UUID-pattern matches — a direct,
narrowly-scoped extension of BR-054's own stated intent ("internal
noise ids"), confirmed safe because nothing ever references them.

**Result**: 0 "Syntax of value for attribute id ... is not valid"
errors (was 4, all in this 1 article).

## Diagnostics added for visibility

Every auto-fix (this milestone's 2, plus the prior milestone's
duplicate-footnote-id fix, which had none before) now logs a
`GeneratorDiagnostic` describing exactly what was dropped/stripped and
why — visible in `ConversionReport.generator_findings` and counted by
the dashboard as "Engine Defects Fixed." `drop_duplicate_children_by_attribute()`
(`generators/xml/helpers.py`) now returns the ids it removed instead of
nothing, so `_copy_author_notes()` can log each one.

## Verification

- `pytest tests/`: 1135 passed (10 new: 9 classifier tests, 1 fixture
  update), 3 pre-existing unrelated failures (see
  `Final_DTD_Compliance_Summary.md`).
- Full batch, `Input/` (37 articles), re-run 4 times across this
  milestone as fixes were corrected: **package generation identical
  every time** (37/37 generated, same 3/30/4/0/0 status breakdown, 213
  recoveries, 0 warnings, 0 failures).
- 574 total "Engine Defects Fixed" diagnostics logged across the
  corpus (duplicate-footnote-id drops, aff-stub drops, journal-meta
  id-strips combined).

## A correction made mid-milestone

The first implementation of the aff-stub fix only scanned
article-meta's *direct* children and left the "ID already defined"
count completely unchanged (16/37, no improvement) on re-run. Investigating
why found the real structure: every duplicate `aff` is nested one level
deeper, inside a per-contributor `<contrib-group>`, not a top-level
article-meta sibling as first assumed from the earlier, single-article
investigation. The fix was rewritten as a whole-tree walk
(`_drop_duplicate_empty_aff_stubs()`) that catches both cases; re-running
the full corpus confirmed the count actually dropped, 16 → 7, exactly
matching the pre-classified safe/unsafe split. This is why this
report's own final batch id is `spec-alignment-final-4`, not the first
attempt — the discipline of re-validating the *entire* corpus after
every change, not just trusting the code, is what caught it.
