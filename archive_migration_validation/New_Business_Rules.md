# New Business Rules — Quality Improvement Milestone

**Zero new Business Rules and zero new Recovery Rules proposed this
milestone.** This is a valid, deliberate outcome, not a gap in effort —
see the methodology below.

## What was checked

Every one of the 12 distinct DTD finding patterns currently occurring
across the 97-article corpus was independently re-derived from first
principles (not just re-reading last milestone's conclusions):

| Pattern | Articles | Re-confirmed category |
|---|---|---|
| `ID con<N> already defined` | 34 | Source Data Issue (D) |
| `award-id-type` undeclared attribute | 26 | Validation Only (E) |
| Empty `reviews.xml` (`review-group` cardinality) | 47 | Validation Only (E) — pending product decision |
| `fn` content model + `<list>` | 8 | Validation Only (E) |
| `ID aff<N> already defined` | 7 | Source Data Issue (D) |
| Dangling `rid` IDREFs (`bibr`, one `aff`) | 5 | Validation Only (E) / Source Data Issue (D) |
| `<contrib>`/`<string-name>` (reviews.xml) | 6 | Validation Only (E) — BR-163 already covers the recoverable subset |
| `No declaration for element string-name` | 6 | Validation Only (E) |
| `ext-link`/`target`, `p`/`dir` undeclared attrs | 4 + 3 | Validation Only (E) |
| `award-group`/`award-desc` DTD-version mismatch | 2 | Validation Only (E) — DTD limitation |

For each, the question asked was: *"Is there a deterministic
transformation of data already present in source that would resolve
this without inventing anything?"* In every case, the answer remains
no:

- **`con`/`aff` id collisions**: the repeated id's two occurrences carry
  genuinely *different* real content (different role text, different
  institution text) in every case checked — there is no way to tell
  which occurrence is "correct" or to renumber one without risking
  mis-attributing it to the wrong contributor/footnote, since the
  cross-references pointing at that id are themselves indistinguishable
  in source.
- **`award-id-type`**: re-confirmed the same `<award-id>` already
  carries a different, valid `award-type` attribute — a rename would
  silently overwrite real data with a different meaning.
- **Empty `reviews.xml`**: the fix (omitting the file when no review
  data exists) is a structural/packaging change, not a data
  transformation — already correctly filed as a product decision, not
  a Business/Recovery Rule.
- **Everything else**: either the DTD requires an element/attribute this
  target DTD variant doesn't declare at all (no rename target exists),
  or the finding traces to a genuine gap in source data with nothing
  present to deterministically derive it from.

## Recovery Rule opportunities considered

Reviewed all `missing_files`/`missing_metadata` patterns in the fresh
corpus run for a safe, deterministic recovery not yet implemented.
None found: every "missing" case already goes through an existing
Recovery Rule (RR-001 filename-from-path, RR-002 skip-and-continue,
RR-004 tolerant filename matching — now with the corrected extension
guard), and no new category of recoverable gap was observed.

## Conclusion

The absence of new rules this milestone is itself a signal: three prior
milestones' worth of rule-book development (163 Business Rules, 7
Recovery Rules) already covers every deterministic, lossless pattern
present in the current 97-article corpus. What remained to find — and
was found — was a genuine **engine defect** (see
`Engine_Defects_Fixed.md`), not a missing rule.
