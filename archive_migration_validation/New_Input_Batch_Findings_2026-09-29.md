# New Input Batch — Findings for Review

**Context**: 60 new source archives were added to the `Input/` folder
(97 total, up from the previous 37-article corpus). All 60 were run
through the existing, unmodified MECA conversion engine
(`archive_migration_batch.py --article-ids <the 60 new ids>`, batch id
`new-input-batch-1`). **No code was changed to produce this batch or
this analysis** — this is a read-only investigation of what the engine
already does with the new data. Every finding below is verified against
the actual generated files or the original source XML, not inferred.

## Batch result

```
Total: 60
  certified_with_warnings: 9
  certified_with_recovery: 40
  partial_certification: 5
  engine_failure: 5
  fatal_failure: 1

Packages generated: 54/60
Total recoveries: 227
```

The prior 37-article corpus never produced a single `engine_failure` or
`fatal_failure` across many verification runs. This batch produced 6 —
that is the headline change and the first 3 findings below explain
exactly why.

---

## Finding 1 — Engine defect: journal-prefix lookup is case-sensitive, crashes on uppercase prefixes

**Severity: High. Confirmed engine defect. Affects 4/60 articles outright, and any future uppercase-prefixed submission.**

`service/worker.py` derives a journal's display name/acronym from the
article id's leading alphabetic prefix, via a hardcoded dict:

```python
_JOURNAL_CONFIG_BY_PREFIX = {
    "CS": {...}, "cs": {...},
    "bcj": {...}, "bsr": {...}, "bst": {...}, "ebc": {...}, "etls": {...},
}
```

Only `CS`/`cs` has both cases covered (added earlier as a one-off fix
for a specific article). Every other prefix is lowercase-only. Four new
articles use uppercase prefixes and are **not in the dict at all**,
causing a raw `KeyError` that surfaces as an opaque `engine_failure`
whose message is just the missing key:

- `BCJ-2024-0504` → `KeyError: 'BCJ'`
- `BCJ-2024-0600` → `KeyError: 'BCJ'`
- `BST-2024-0679C` → `KeyError: 'BST'`
- `BST-2024-1703` → `KeyError: 'BST'`

Verified: all 4 archives have a completely normal structure with a
valid source XML present — the *only* blocker is this lookup. Verified
control case: `CS-2024-2165`/`CS-2024-2797` (also uppercase) succeeded,
because `"CS"` happens to already be in the dict.

**Recommended action**: make the lookup case-insensitive for every
prefix (e.g. normalize to one case before the dict lookup), not another
one-off key addition — the same defect will recur for any future
uppercase `BSR-`/`EBC-`/`ETLS-` submission.

---

## Finding 2 — Engine defect: multiple `<author-notes>` blocks silently collapse to just the last one (real data loss)

**Severity: High (silent data loss). Confirmed. 1/60 articles in this batch, but the underlying code pattern applies to any future article with this source shape.**

`cs-2024-5002` generates an `article.xml` with only one CRediT
contribution-role footnote (`con14`) even though 14 different
contributors' `<xref ref-type="fn" rid="conN">` references (con1
through con14) are all still present and expect 14 corresponding
footnotes.

Root cause, verified directly against `raw.xml`: this source represents
each contribution-role footnote as its **own separate `<author-notes>`
element** (14 distinct `<author-notes>` blocks, one per footnote) rather
than one `<author-notes>` containing 14 `<fn>` children (the shape every
article in the original 37-article corpus used, and the shape the
generator's internal bucketing (`_bucket_article_meta_children` in
`generators/article_xml/generator.py`) implicitly assumed). That
function stores at most one `author_notes` value and overwrites it on
each `<author-notes>` tag it encounters — so only the **last** one
survives; the other 13 are discarded with no warning, no diagnostic, no
recovery record.

This is a genuine "never silently discard information" violation: real,
present, correctly-authored source content (13 footnotes) disappears
from the output with zero trace in any report.

**Recommended action**: the bucketing logic needs to accumulate *every*
`<author-notes>` element's children (merging them, since MECA/JATS
article-meta only allows one `<author-notes>`) instead of keeping only
the last one seen.

---

## Finding 3 — High-volume DTD-compliance gap: empty `reviews.xml` violates the DTD's minimum cardinality

**Severity: Medium-High (DTD compliance), but likely correct behavior needing a policy decision, not a bug. Affects 43/60 articles (72%) in this batch.**

43 of the 60 new articles have **zero** peer-review history in source
(verified: no reviewer scorecards, no decline reasons, no decision
drafts, no reviewer contrib-groups anywhere in the original XML for a
sampled case, `bcj-2024-3001`). The engine correctly has nothing to
render — but it still always emits a `reviews.xml`, and an empty one:

```xml
<review-group ... content-version="1.0" />
```

`reviews-1.0.dtd` requires `review-group` to contain `(review)+` — one
or more — so every one of these 43 reviews.xml files is DTD-invalid
purely because it's empty, not because anything in it is wrong.

This is **not observed to be an engine defect** — the source genuinely
has no review data for these 43 articles (likely a different submission
type/stage than the original 37-article corpus, which apparently always
had at least one review recorded). The open question is a **product/
business decision**: should the engine omit `reviews.xml` from the
package entirely when there is zero review content (and adjust
`manifest.xml` accordingly), rather than emit a DTD-invalid empty
placeholder? This wasn't visible before because no article in the
original corpus ever had zero review content.

**Recommended action**: a business decision on whether "no review
history" should mean "omit reviews.xml" vs. some other DTD-compliant
representation. Not something to silently decide or implement.

Affected articles (43): CS-2024-2165, CS-2024-2797, bcj-2024-3001,
bcj-2024-3003, bcj-2024-3005, bcj-2024-3006, bcj-2024-3008,
bcj-2024-3010, bcj-2024-3019, bcj-2025-3023, bst-2024-3000,
bst-2025-3008, bst-2025-3027, bst-2025-3075, bst-2025-3093,
bst-2025-3095, bst-2025-3105, cs-2024-5002, cs-2024-5133, cs-2024-5143,
cs-2024-5144, cs-2024-5145, cs-2024-5146, cs-2024-5148, cs-2024-5193,
ebc-2024-3002, ebc-2025-3007, ebc-2025-3024, ebc-2025-3028,
ebc-2025-3029, ebc-2025-3030, ebc-2025-3049_C, ebc-2025-3051,
etls-2024-3000, etls-2024-3001, etls-2025-3006, etls-2025-3007,
etls-2025-3011, etls-2025-3016, etls-2025-3018, etls-2026-3001,
etls-2026-3002, etls-2026-3003.

---

## Finding 4 — Source data issue: completely empty source archive

**Severity: Correctly caught, but misclassified as `engine_failure` rather than a source-data failure. 1/60 articles.**

`ebc-2025-3025.zip` contains **one empty directory entry and zero
files** (verified via `unzip -l`, confirmed with the original file — not
a staging/extraction bug on this engine's side). The engine correctly
refuses to proceed ("No source XML found"), but this is a submission
that is empty/corrupt at the source, not an engine or code defect. It
currently surfaces as `ENGINE_FAILURE` (implying "our fault, investigate
the engine"), which is misleading for an empty-archive case.

**Recommended action**: no code fix implied for the missing content
itself (nothing to recover from an empty archive) — worth confirming
whether "source archive contains no files at all" should be classified
as a source-data/fatal failure rather than an engine failure, so
operators aren't misdirected to investigate the engine.

---

## Finding 5 — Source data issue: declared manuscript file missing

**Severity: Low. Standard, already-understood failure mode (BR-011). 1/60 articles.**

`ebc-2025-3021_C`: the source declares a manuscript file, `Conlan and
Charlet Rev v8.docx`, that has no matching physical file anywhere in
the staged submission. Correctly raised as `FATAL_FAILURE`
(`FileReferenceMissingError`, extraction/file_resolver.py) — this is
the existing, intentional "never fabricate a missing manuscript"
behavior working as designed. No action needed.

---

## Finding 6 — Source data issue: dangling affiliation reference (not an engine defect)

**Severity: Low. Confirmed present verbatim in the original source. 1/60 articles.**

`bsr-2025-3807`'s `article.xml` has two `<xref ref-type="aff">` elements
referencing an affiliation id (`aff2d2fc946-1a0a-4395-9726-3bb1543cbfb2`)
that is never defined as an `<aff>` element anywhere in the document.
Verified directly against the original source XML: the reference exists
there too, with no corresponding affiliation definition — the publisher's
own export already has this broken link. The engine faithfully
reproduces it (no fabrication attempted). No action recommended beyond
the existing DTD-validation report already surfacing it as an unresolved
reference.

---

## Finding 7 — Narrow DTD-structure mismatch: `award-group` content ordering

**Severity: Low, needs a closer look. 2/60 articles (`bst-2025-3027`, `etls-2025-3007`).**

Both articles' `<award-group>` blocks fail DTD validation with
"content does not follow the DTD, expecting ((funding-source* |
support-source*), award-id*, principal-award-recipient*, ...)". Not yet
root-caused to a specific element/ordering problem — flagged for a
follow-up look rather than fully investigated here, given the narrow
(2-article) scope.

---

## Finding 8 — Higher volume of an already-known, already-classified issue (not new)

The `award-id/@award-id-type` "not declared by this JATS DTD variant"
finding (already classified **Validation Only** in the DTD-compliance
milestone — no equivalent attribute exists to rename to) now appears in
25/60 articles, up from 1/37 previously. This is the same finding at
higher volume in this batch (more funded articles), not a new issue
type. No action changes.

---

## Finding 9 — Minor reporting-clarity gap

`bst-2025-3095` is `partial_certification` with an **empty**
`missing_files` list — because the 3 `RR-002` (missing file skipped)
recoveries that actually fired all have a blank filename/round/category
in the source's own custom-meta entry, so there's nothing to put in
`missing_files`. Not a data-loss issue (nothing fabricated, nothing
silently dropped) — just a report that can look contradictory
("partial certification" with "0 missing files") to an operator glancing
at it. Worth a cosmetic improvement (e.g. a placeholder note) if this
recurs.

---

## Suggested priority order for follow-up

1. **Finding 1** (journal-prefix case sensitivity) — small, clearly-scoped, safe fix; blocks 4 articles outright today.
2. **Finding 2** (multiple author-notes silently dropped) — real data loss; needs a careful fix to the bucketing logic, verify against the original 37-article corpus afterward to confirm no regression.
3. **Finding 3** (empty reviews.xml) — needs a product decision before any code changes.
4. Findings 4, 7, 9 — worth a decision/small look, not urgent.
5. Findings 5, 6, 8 — no action needed; existing behavior is already correct.
