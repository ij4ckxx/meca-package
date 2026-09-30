# Product Decision Recommendations — Production Stabilization Milestone

No code was changed for any item in this document — investigation and
recommendation only, per this milestone's scope.

## Work Item 5 — Empty reviews.xml

**Problem**: articles with zero review/decision history in source still
get a `reviews.xml` with an empty `<review-group/>`, which
`reviews-1.0.dtd` forbids (`review-group` requires `(review+)` — one or
more). Affects 43/60 articles in the latest batch, all confirmed
genuinely having zero review data in source (not an extraction gap).

**Options evaluated**

- **A — Always generate the empty file (status quo)**: zero code
  change, but ships a permanently DTD-invalid file for the majority of
  the current corpus and forces a standing "known issue" carve-out
  forever.
- **B — Skip reviews.xml entirely when no review/decision data exists**
  (and correspondingly omit `item-reviews` from `manifest.xml`): DTD-
  valid in both cases, no fabrication, semantically honest ("no review
  history" → "no review artifact"). Confirmed the manifest DTD only
  requires `item+` — never specifically 3 fixed items — so this is not a
  spec violation, only an engine-convention change. Requires making
  `PackageBuilder`'s currently-fixed 5-generator sequence conditional for
  this one file, and giving `ManifestXmlGenerator` the same "has review
  content" check `ReviewsXmlGenerator` already computes (a duplicated
  read, not a new generator-to-generator dependency — preserves the
  existing "no cross-generator dependency" architecture). Downstream
  systems that assume a fixed 5-file package shape would need to be
  confirmed tolerant of a 4-file package.
- **C — Generate only when data exists**: functionally identical to B.
- **D — A DTD-valid empty placeholder**: checked the vendored DTD
  directly — no legal empty `<review>` or alternate "no reviews" root
  exists. Any placeholder would require inventing review content that
  never happened, directly conflicting with this project's own
  established no-fabrication principle.

**Recommendation**: **Option B.** It is the only option that is both
DTD-compliant and fabrication-free. Implementation is bounded (two
generator-layer touch points) but is a real code change, not a
config flag — deliberately not implemented in this milestone per its
"recommendation only" scope.

## Work Item 6 — award-group DTD ordering (`bst-2025-3027`, `etls-2025-3007`)

**Root cause, confirmed by direct comparison of source XML, generated
article.xml, and the vendored DTD**: both articles' source XML already
contains an `<award-desc>` element and an `award-id-type` attribute in
exactly the order/shape that ends up in the generated package — the
engine copies `funding-group`/`award-group` verbatim, byte-for-byte, by
design (documented "identify, don't interpret" boundary; no
award-group-specific code exists anywhere in the engine). The target
DTD (`jats-archiving-1.2`) simply predates these constructs — `award-desc`
isn't a declared element at all in this DTD variant, and `award-id`
doesn't declare an `award-id-type` attribute. The reported "content does
not follow the DTD" error is the generic symptom of an undeclared
element appearing mid-sequence, not evidence of the engine emitting
`funding-source`/`award-id`/`principal-award-recipient` out of order —
those three are already in the DTD's expected relative order.

**Verdict**: **source data issue (schema-version mismatch)** — the
source production system emits a newer/richer JATS funding profile than
this MECA package's target DTD supports. **Not an engine defect.** No
fix proposed, per this work item's "investigation only" scope.

**One process note worth flagging**: neither the "award-group content
does not follow the DTD" message nor "no declaration for element
award-desc" currently has an explicit pattern in
`validation/dtd_issue_classifier.py` — both land in `VALIDATION_ONLY`
only via the default fallback, which happens to be correct here, but is
incidental rather than deliberate. Worth adding explicit patterns in a
future pass so the classification is intentional, not a side effect.

## Work Item 7 — award-id-type classification review

**Re-verified independently against the vendored DTD**: `award-id-atts`
declares only `rid`, `award-type`, `specific-use`, `xml:lang` —
`award-id-type` is genuinely undeclared, confirming the existing
classification's basis. Additionally confirmed a new fact that
strengthens the case: in both affected real articles, the *same*
`<award-id>` already carries a valid `award-type="grant"` **alongside**
the undeclared `award-id-type="doi"` — these are not synonyms, so a
rename-based fix would silently overwrite a different, already-correct
attribute with a different meaning, corrupting real data. This rules
out a rename-style Business Rule entirely (unlike the earlier, now
already-implemented BR-161 `data-type`→`content-type` rename, which had
no such collision risk).

**Recommendation**: **keep `award-id-type` classified as
`VALIDATION_ONLY`.** It fails the bar for both a Business Rule (no
lossless, collision-free rewrite exists) and a Recovery Rule (nothing is
missing — the data is fully present, just expressed in an attribute this
DTD variant doesn't define). Do not introduce a new "Validation Warning"
taxonomy value for it either: `SpecAlignmentCategory` is a closed,
`@unique` enum whose 4 values are consumed by the classifier, dashboard,
and every report that renders a category — adding a 5th value is a
taxonomy change touching all of those, not a lightweight one, and the
underlying reasoning (no safe fix exists) doesn't change whether this
shows up in 1 article or 25. If dashboard visibility is genuinely
insufficient at the new volume, the lighter-weight fix is to make the
existing `VALIDATION_ONLY` category's presentation impact-count-aware,
not to fork a new category for one finding.
