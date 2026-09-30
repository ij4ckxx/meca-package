# Remaining Source Data Issues (Category D) — Quality Improvement Milestone

The publisher's own data is internally inconsistent or incomplete in
these cases. The engine never modifies source content and never
fabricates a correction — each is surfaced as a finding, not repaired.

## `ID con<N> already defined` — 34 articles, ~388 occurrences

Source repeats the same CRediT contribution-role code (`con1`..`con14`)
across separate editorial rounds, each with genuinely different role
text. `raw_xml`'s cleanup step promotes that role code to the document's
literal XML id (required, since the source's own `<xref ref-type="fn"
rid="con1">` already references the role code, not a UUID) — so a
source-side collision becomes a literal duplicate-ID DTD error. Every
occurrence is kept (never dropped), since dropping any repeat would
risk deleting a real, distinct contribution statement. No safe
disambiguation exists: the `xref`s pointing at `rid="con1"` are
themselves indistinguishable between rounds in source.

## `ID aff<N> already defined` — 7 articles

Two `<aff>` elements share an id but carry genuinely different
institution text (confirmed per-article, e.g. `ebc-2025-3050_C`: one
`aff1` has a full department + university address, the other has a
shorter university-only address — not a duplicate, two different real
affiliations that happen to share a source-assigned id). Neither is
dropped.

## Dangling `bibr` xrefs, no `<ref-list>` — 4 articles

Body text cites a reference (e.g. `<xref ref-type="bibr" rid="R66">66</xref>`)
but the source carries no bibliography/reference-list data for this
engine to extract at all — confirmed, not an extraction gap: this
engine's scope has never included reference-list generation.

## Dangling affiliation xref — `bsr-2025-3807`

`<xref ref-type="aff">` references an affiliation id that is never
defined anywhere in the document — confirmed present verbatim in the
original source export; the engine faithfully reproduces the publisher's
own broken link rather than inventing a plausible-looking fix.

## `award-group`/`award-desc` — `bst-2025-3027`, `etls-2025-3007`

Source funding metadata uses a newer JATS funding profile
(`award-desc` element, `award-id-type` attribute) than the target
archiving DTD variant (`jats-archiving-1.2`) declares — a genuine
schema-version mismatch between the source production system and this
package's target DTD, not an engine defect (confirmed: the engine
copies `funding-group` byte-for-byte, by design).
