# DTD Compliance Summary

Basic MECA DTD-guideline compliance for `article.xml`, `reviews.xml`,
`manifest.xml`, `transfer.xml`, validated against the real, vendored
DTDs referenced by the NISO MECA project — not well-formedness alone.

## Source of truth

- **MECA DTDs** (`manifest-1.0.dtd`, `reviews-1.0.dtd`,
  `transfer-1.0.dtd`): vendored verbatim from
  https://github.com/niso-standards/meca (`schema/`), MIT License,
  Copyright (c) 2022 NISO (Z39).
- **JATS Archiving 1.2 DTD Suite** (`JATS-archivearticle1.dtd` + ~40
  module/entity files): vendored from
  https://public.nlm.nih.gov/projects/jats/archiving/1.2/
  (`JATS-Archiving-1-2-MathML2-DTD.zip`) — the exact DTD the NISO MECA
  project's own reference `article.xml` declares in its `DOCTYPE`
  (`https://github.com/niso-standards/meca/blob/main/examples/article.xml`).
  Public-domain US government work.
- **`tests/fixtures/dtd_examples/`**: the 4 official NISO MECA example
  files, used as known-good regression fixtures — all 4 validate PASS
  against the vendored DTDs (confirms correct vendoring, independent of
  this engine's own output).

No DTD content was authored or modified — every file under
`schemas/dtd/` is an unmodified vendor artifact. See each directory's
`README.md` for exact provenance.

## Corpus-wide result (37/37 articles, `Input/`, batch `dtd-compliance-verify-3`)

| File | Well-formed | DTD-valid |
|---|---|---|
| manifest.xml | 37/37 PASS | **37/37 PASS** |
| transfer.xml | 37/37 PASS | **37/37 PASS** |
| article.xml | 37/37 PASS | 0/37 PASS (confirmed defects below) |
| reviews.xml | 37/37 PASS | 0/37 PASS (confirmed defect below) |

Every file in the corpus is well-formed XML. manifest.xml and
transfer.xml are also fully DTD-valid with no changes needed.
article.xml and reviews.xml have confirmed DTD violations, classified
below — two are fixed engine defects, the rest are source-data issues
or missing Business Rules requiring an explicit decision before any
code changes them.

## Fixed — confirmed engine defects

### 1. Duplicate footnote IDs in article.xml author-notes

**Finding**: bcj-2025-3130's source repeats the same CRediT-role `<fn>`
block (e.g. `fn-type="con" id="con2"`) up to 4 times inside
`author-notes`, each repeat byte-identical in content. The source
itself gives each repeat a different UUID `id` plus a separate
`data-id="con2"` marker; raw.xml's own generation already promotes
`data-id` to the literal `id` attribute, and the article.xml generator
copied every repeat verbatim — producing 4 elements sharing one XML
`id`, which is illegal (XML `ID`-typed attributes must be
document-unique).

**Classification**: Engine defect. The needed information (each
element already had a real, unique id) was available; the fix removes
nothing — every repeat is byte-identical, so keeping only the first is
lossless.

**Fix**: `generators/xml/helpers.py` — new `drop_duplicate_children_by_attribute()`
(keeps the first child with a given attribute value, drops exact
duplicates by id). Wired into `_copy_author_notes()` in
`generators/article_xml/generator.py`.

**Result**: 0 "ID already defined" errors for `con*` footnote ids
across the corpus (was present in ≥1 article before the fix).

### 2. article-meta child ordering violated the DTD for several articles

**Finding**: `JATS-archivearticle1.dtd` requires a strict sequence
inside `<article-meta>` (e.g. `volume` before `fpage`/`lpage` before
`history`; `abstract` before `kwd-group` before `funding-group`/`counts`).
The generator copied these tags in whatever order raw.xml happened to
have them — which mirrors the *source's* own order, not the DTD's. This
worked by coincidence for most articles but produced a DTD-invalid
`article-meta` for 4 real articles (`bst-2025-3098_C`, `bst-2025-3107_C`,
`bst-2025-3131`, `ebc-2025-3054_C`) where the source's own tag order
didn't match.

**Classification**: Engine defect. All the data was already present
and already reaching article.xml — only the emission order was wrong.

**Fix**: `generators/article_xml/generator.py` — `_build_article_meta()`
now buckets raw.xml's article-meta children by tag first
(`_bucket_article_meta_children()`), then emits every tag in a fixed,
DTD-mandated order (`_ARTICLE_META_TAGS_BEFORE_CONTRIB`/
`_ARTICLE_META_TAGS_AFTER_CONTRIB`) instead of raw.xml's own order.
contrib-group/aff/author-notes keep their existing, already-correct
special handling (from the earlier Conversion Quality milestone),
repositioned to the correct DTD slot.

**Result**: 0 "article-meta content does not follow the DTD" errors
across the corpus (was 4/37 before the fix).

## Confirmed, classified, **not** fixed — require an explicit decision

| Finding | File | Scope | Classification | Why not fixed now |
|---|---|---|---|---|
| `<string-name>` is not a valid MECA `contrib` child (only `<name>` or `<name-alternatives>`, both requiring `surname`+`given-names`) | reviews.xml | 37/37 | Missing Business Rule | `ReviewerScorecard`/`DeclineReason` carry only one flattened raw name string — splitting it would fabricate a surname/given-names split never evidenced. Already flagged in the prior Business Rule Recommendations analysis as a scope decision, not a code bug. Omitting the name entirely would satisfy the DTD but silently drop real reviewer-identity data — also not done without approval. |
| `data-type` attribute on `<p>` (JATS declares `content-type`, not `data-type`) | article.xml | 202 occurrences across the corpus | Missing Business Rule | Renaming an attribute changes the document's declared semantics even though the value itself is untouched — a real interpretive decision, not a mechanical fix. Already flagged in the prior Business Rule Recommendations analysis. |
| Duplicate `aff` elements sharing `id="aff1"` | article.xml | 16/37 articles | Source Data Issue / Missing Business Rule | **Not uniform**: in some articles the second `aff1` is an empty stub (safe to drop); in others (`bst-2025-3127` confirmed) it carries a *different, real* institution's address under the same id. Blindly keeping-first would silently delete real source content in the second case — this needs a business decision (renumber vs. merge vs. flag for manual review), not a blind code fix. |
| `xref rid="aff1, aff2"` — comma-separated IDREFS (XML requires whitespace-only separators) | article.xml | 37/37 (every multi-affiliation xref) | Source Data Issue | Confirmed present verbatim in the original source XML, not introduced by any generator. A syntax-only reformat (comma+space → space) would be lossless and fix DTD compliance, but it does modify a publisher-supplied attribute value — recommended as a new Recovery Rule, not implemented without approval. |
| `<fn>` containing a `<list>` directly (DTD requires `label?, p+`) | article.xml | 7/37 articles | Source Data Issue | Source content is structured as a list at that position; flattening list items into sibling `<p>` elements might be lossless but is a structural transformation, not evaluated in this milestone. |
| `id` attribute value starts with a digit (`journal-meta`, `journal-title-group`, `abbrev-journal-title`, `issn`) | article.xml | 1/37 articles (`cs-2025-5853_C`) | Engine anomaly, narrow — flagged for follow-up | The value is a corrupted/mangled UUID-like string (contains non-hex characters in UUID positions), so it doesn't match `_UUID_ID_PATTERN` and isn't stripped by BR-054. Root cause (why this one id got corrupted) needs its own investigation; isolated to one article, so out of this milestone's "minimum needed" scope. |
| Minor undeclared attributes (`ext-link/@target`, `p/@dir`, `award-id/@award-id-type`) | article.xml | ≤4 occurrences each | Source Data Issue | Verbatim from source; no rule authorizes stripping or renaming them. |

None of the above were changed. No publisher value was invented,
cleaned, or silently dropped.

## Verification

- `pytest tests/`: 1125 passed, 3 pre-existing failures unrelated to
  this work (see `Final_Implementation_Summary.md`).
- Full batch, `Input/` (37 articles), 3 successive re-runs
  (`dtd-compliance-verify`, `-2`, `-3` — the middle run caught and
  fixed an ordering regression in my own first attempt at the
  article-meta fix before it shipped): package generation identical
  across all 3 runs (37/37 generated, same 3/30/4/0/0 status
  breakdown, 213 recoveries, 0 warnings, 0 failures) — confirming the
  DTD-compliance work changed only internal XML structure/validity,
  never package outcomes.
