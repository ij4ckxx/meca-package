# Proposed Recovery Rules

**Status: Rejection preserved** (Business Rule Completion milestone) —
re-reviewed per that milestone's explicit instruction to preserve this
decision unless new evidence proves otherwise; no new evidence emerged,
so no Recovery Rule was added. The 7 affected articles remain
classified Source Data Issue.

Only one genuine Recovery Rule candidate emerged from this milestone's
full-corpus investigation. It is presented here, evaluated against the
"clearly deterministic" bar this milestone requires, and **not
implemented and not recommended for automatic implementation** — the
evaluation itself concluded the bar isn't met.

---

## Candidate — Renumber duplicate `aff` ids with distinct content

**Where**: article.xml, the 7 articles where a duplicate `<aff>` id
carries genuinely different institution text (see
`Remaining_Validation_Issues.md`'s Category B table —
`bst-2025-3107_C`, `bst-2025-3127`, `bst-2025-3131`, `ebc-2025-3045_C`,
`ebc-2025-3048_C`, `ebc-2025-3050_C`, `ebc-2025-3057_C`).

**The gap**: the source assigns the same id (e.g. "aff1") to two
different, real affiliations. XML IDs must be document-unique, so the
document is DTD-invalid as-is.

**The candidate fallback**: keep both `<aff>` elements, but give the
second occurrence a deterministic, mechanically-derived new id (e.g.
`aff1` → `aff1-2`), preserving both institutions' full text.

**Confidence: LOW. Not recommended as automatic.**

Two problems, both structural, neither solvable by the rule itself:

1. **Orphaning.** Every `<xref rid="aff1">` in the document was written
   assuming "aff1" resolves to *one* affiliation. Renaming the second
   occurrence to `aff1-2` doesn't fix which contributor's `xref`
   should now point at it — that mapping was never recorded anywhere
   in the source to begin with (both aff blocks arrived under the
   *same* id, with no signal linking either one to a specific
   contributor). The renamed block becomes valid XML but
   **unreachable from any `xref`** — arguably a worse outcome than
   today's DTD error, since it silently hides that a real affiliation
   is disconnected from every contributor.
2. **No signal to prefer renumbering over any other resolution.**
   Merging the two into one combined `<aff>`, or flagging the article
   for manual review instead, are equally plausible responses — and
   picking one over the others is a policy decision, not a technical
   one. "Clearly deterministic" fails here specifically because there
   is more than one reasonable, safe-looking answer with no way to
   choose between them from the data alone.

**What was ruled out and why:**
- *Drop the second occurrence* (as done for the 9 confirmed-empty
  stubs in `DTD_Fix_Summary.md`): unsafe here specifically because the
  content differs — this would delete a real, distinct affiliation.
- *Merge into one `<aff>`*: would require deciding how to combine two
  independent address structures (which department, which country) —
  an assumption, not a determination.
- *Fabricate a linking `xref` update*: explicitly forbidden — no
  information exists to say which contributor the "wrong" aff1 belongs
  to.

**Recommendation**: Do not implement. Surface these 7 articles as
Category B (Source Data Issue) findings for manual review instead —
already done in this milestone's reporting/dashboard. If this becomes
frequent enough to be worth automating, the right next step is a
targeted extraction-layer investigation (does the source ever carry a
distinguishing marker between the two "aff1" blocks that this
engine's ICAM simply isn't reading yet?), not a blind renumbering
rule.

---

## Why nothing else qualified as a Recovery Rule candidate

Every other remaining finding is either:
- **Category C** (`Proposed_Business_Rules.md`) — the source has a
  single, unambiguous correct answer requiring a rename or
  normalization, not a *fallback for missing data* (Recovery Rules are
  specifically for filling a gap deterministically, e.g. "filename
  from path" — none of the Category C findings involve anything
  missing; the data is fully present, just mis-labeled or
  mis-formatted).
- **Category E** (`Remaining_Validation_Issues.md`) — genuinely
  requires an assumption or semantic judgment call, which by
  definition rules out "clearly deterministic."

No other case in this corpus fit the Recovery Rule shape (source
incomplete, deterministic fallback exists) at all.
