# Remaining Validation-Only Findings (Category E) — Quality Improvement Milestone

The DTD requires something that cannot be safely produced without
fabricating data. XML is never modified to force a pass; each is
documented here.

## Empty `reviews.xml` — 47/97 articles

`reviews-1.0.dtd` requires `review-group` to contain `(review)+` — one
or more. 47 articles have zero review/decision history in source
(confirmed genuine absence, not an extraction failure), so the engine
emits an empty, technically DTD-invalid `<review-group/>` rather than
inventing a review that never happened. **This has an already-approved
product decision pending implementation** (Option B: omit `reviews.xml`
and its `manifest.xml` entry when no review data exists) — see
`Product_Decision_Recommendations.md` from the prior milestone; not
implemented under this milestone's defect-fixing scope.

## `award-id-type` — 26 articles, 55 occurrences

`<award-id>` carries a real `award-id-type="doi"` attribute this DTD
variant doesn't declare. No rename target exists — the same element
already carries a valid, different `award-type` attribute; renaming
would overwrite real data.

## `fn` content model + `<list>` — 8 articles

`<fn>` requires `(label? , p+)`; some source footnotes contain a
`<list>` inline. Flattening the list into plain paragraph text would
change the semantic structure of the source's own formatting — a
content decision, not a syntax fix.

## `<contrib>`/`<string-name>` (reviews.xml) — 6 articles

Reviewer names fall back to an unstructured `<string-name>` when no
matching structured contributor identity exists elsewhere in the same
source document. This is BR-163's own documented partial-coverage
boundary (structured names are used whenever a match exists) — a
remaining `<string-name>` means no match exists, and inventing a
surname/given-names split would be fabrication.

## `ext-link`/`target`, `p`/`dir` — 4 + 3 articles

Attributes present in source verbatim, not declared by this JATS DTD
variant. No equivalent attribute exists to map them to.

## `award-group`/`award-desc` DTD-version mismatch — 2 articles

See `Remaining_Source_Data_Issues.md` — classified as a DTD limitation
(the target DTD predates these JATS constructs), documented only.

## Dangling `bibr` references — 4 articles

No reference-list extraction exists in this engine's scope — see
`Remaining_Source_Data_Issues.md`.
