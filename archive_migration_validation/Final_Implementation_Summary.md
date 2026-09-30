# Final Implementation Summary — MECA DTD-Guideline Compliance

## Scope delivered

1. Vendored the real MECA + JATS Archiving 1.2 DTD suites (source of
   truth: https://github.com/niso-standards/meca and the JATS DTD it
   references) — DTD validation now runs against real DTDs, not
   well-formedness alone.
2. DTD validation runs strictly after package generation; never blocks
   it (confirmed: identical 37/37 package outcomes across 3 successive
   batch runs spanning the whole change).
3. Every DTD finding classified: engine defect, source-data issue,
   missing/needed Business Rule, validation error, or warning (see
   `DTD_Compliance_Summary.md`).
4. Fixed exactly 2 confirmed engine defects where the source already
   had the needed information: duplicate footnote IDs in article.xml's
   `author-notes`, and article-meta child-ordering violations affecting
   4 real articles.
5. No missing value was fabricated anywhere.
6. Every DTD-non-compliant case that can't be resolved without
   inventing data, changing semantics, or risking silent data loss was
   left as-is and surfaced in `ConversionReport`, the standalone
   validation report, and the dashboard — never hidden.
7. The dashboard now shows well-formedness and DTD compliance as two
   separate results everywhere validation appears (Article Detail,
   Home, Analytics).

## What changed, in one paragraph

Real DTDs (MECA's own 3, plus the JATS Archiving 1.2 suite article.xml
declares) are now vendored under `schemas/dtd/`, sourced directly from
the NISO MECA GitHub repo and the JATS DTD it points to. The validator
now reports well-formedness and DTD conformance as two independent
results per file (`well_formed_result`/`dtd_result`, plus a package-level
`overall_dtd_result`) instead of one merged, DTD-not-actually-checked
"pass." Running this against the real corpus surfaced genuine defects:
two were confirmed engine bugs (duplicate ids, wrong element order) and
fixed with minimal, evidenced changes; the rest — an invalid MECA
element (`<string-name>`), a non-JATS attribute (`data-type`),
inconsistent duplicate affiliation ids, comma-separated ID references,
and a couple of narrower issues — are source-data issues or missing
Business Rules that require an explicit decision, not a silent code
change, so they were classified and left alone. The dashboard was
extended additively to show both results everywhere it already showed
validation.

## Batch execution summary

Full run against `Input/` (37 articles), 3 successive runs during this
milestone (`dtd-compliance-verify` → found the corpus-wide picture;
`-2` → after the duplicate-id fix, discovered and fixed an ordering
regression in the article-meta fix itself before it shipped; `-3` →
final, confirmed-clean run):

```
Total: 37
  certified: 0
  certified_with_warnings: 3
  certified_with_recovery: 30
  partial_certification: 4
  engine_failure: 0
  fatal_failure: 0

Packages generated: 37/37
Total warnings: 0
Total recoveries: 213
Engine failures: 0
Fatal failures: 0
```

Identical across all 3 runs — confirms package generation was never
affected by any DTD-compliance change.

**DTD validation results** (37/37 articles, 148 file-checks):

| File | Well-formed | DTD-valid |
|---|---|---|
| manifest.xml | 37/37 | 37/37 |
| transfer.xml | 37/37 | 37/37 |
| article.xml | 37/37 | 0/37 (see classified findings) |
| reviews.xml | 37/37 | 0/37 (`<string-name>` — Missing Business Rule) |

## Test suite

`pytest tests/`: **1125 passed, 3 failed** — the same 3 pre-existing,
unrelated golden ICAM snapshot failures documented in the prior
milestone's summary (affiliation `country`/`institution` fields; a
code path this milestone never touches). Not fixed here either, per
instruction not to perform unrelated regression work.

Dashboard: `tsc -b --noEmit` (web) / `tsc -p tsconfig.json` (server)
both clean; every changed/new endpoint verified live against the real
`dtd-compliance-verify-3` batch.

## Newly discovered issues

1. **article.xml — `data-type` attribute on `<p>`** (202 occurrences,
   every article): JATS declares `content-type`, not `data-type`.
   Renaming would fix DTD compliance losslessly but changes a declared
   attribute name — classified Missing Business Rule, not implemented.
2. **reviews.xml — `<string-name>` is not a valid MECA element**
   (37/37 articles): the DTD only allows a fully-structured `<name>`
   (mandatory surname + given-names) or nothing at all. The engine
   only ever has a single flattened name string — splitting it would
   fabricate data; omitting it would silently drop real reviewer
   identity. Classified Missing Business Rule, requires a product
   decision (already flagged once before, in the prior milestone's
   Business Rule Recommendations).
3. **article.xml — duplicate `aff` elements sharing `id="aff1"`**
   (16/37 articles): **not uniform** — some are empty stubs (safe to
   drop), but `bst-2025-3127` confirmed a case where the second
   `aff1` carries a genuinely different institution's address under
   the same id. A blind "keep first" fix would silently delete real
   data in that case. Classified Source Data Issue / Missing Business
   Rule — needs an explicit decision (renumber vs. merge vs. flag),
   not implemented.
4. **article.xml — `xref rid="aff1, aff2"`** (every multi-affiliation
   xref, confirmed present verbatim in the original source XML): XML
   IDREFS requires whitespace-only separators; the source uses
   comma+space. A syntax-only reformat would be lossless, but it edits
   a publisher-supplied attribute value — recommended as a new
   Recovery Rule, not implemented without approval.
5. **article.xml — `<fn>` containing a `<list>` directly** (7/37
   articles): the DTD only allows `label?, p+` inside `<fn>`; source
   content is structured as a list at that position. Not evaluated for
   a fix in this milestone.
6. **article.xml — one corrupted UUID-like `id`** (`cs-2025-5853_C`,
   1/37 articles): a mangled UUID (non-hex characters in UUID
   positions) starting with a digit fails XML's `Name` syntax and also
   fails BR-054's strip pattern (which requires pure hex). Narrow,
   single-article impact; root cause not investigated further in this
   milestone.

None of the above were changed in code. All are documented, classified,
and visible in `ConversionReport.validation_report`, the standalone
validation report, and the dashboard.

## Deliverables

1. `DTD_Compliance_Summary.md`
2. `Validation_Rule_Baseline.md`
3. `Dashboard_Validation_Alignment.md`
4. `Final_Implementation_Summary.md` (this document)

Stopping here per instruction — awaiting approval before any further
roadmap work (including the 6 newly discovered issues above, none of
which were acted on).
