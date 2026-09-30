# Proposed Business Rules

**Status: All 3 approved and implemented** (Business Rule Completion
milestone) as BR-161 (`data-type`→`content-type`), BR-162 (comma-separated
`xref/@rid` normalization), and BR-163 (structured reviewer names in
reviews.xml) — see `01_BUSINESS_RULE_BOOK.md` §K for the final rule
text and `Final_DTD_Compliance_Summary.md`'s update for corpus-wide
before/after results. The original proposals below are preserved
as-written for the record.

Three candidates, all Category C (the source contains enough
information; the Business Rule Book has no rule for the
transformation). Each is deterministic and lossless; each required
explicit approval before any code changes, per the DTD-compliance
milestone's instructions — approval was given in the Business Rule
Completion milestone.

---

## Proposed BR — `data-type` → `content-type` rename on `<p>`

**Where**: article.xml, `<p>` elements copied from raw.xml's
`author-notes`/`fn` content (data-availability statements, figshare
statements, declarations).

**Corpus evidence**: 202 occurrences across all 37 articles — every
single article. Confirmed present verbatim in the original source XML
(Kriyadocs' own attribute-naming convention), faithfully copied
through raw.xml into article.xml unchanged.

**Why deterministic**: `data-type` is always used the same way in this
corpus — as a sub-classification label on `<p>` (e.g.
`data-type="figshare-statement"`, `data-type="declaration"`,
`data-type="statement"`). JATS's own `<p>` attribute list declares
`content-type` (CDATA, `#IMPLIED`) for exactly this purpose — a
general-purpose sub-type label with no value constraints. The rename
is 1:1: same attribute *position*, same *value*, only the *name*
changes to the one the DTD actually declares.

**Why safe**: no value is invented, altered, or dropped. No
interpretation of the sub-type label itself is required — it passes
through unchanged. Confirmed no other JATS-declared attribute is
already named `data-type` on `<p>` that this would collide with.

**Before**:
```xml
<p data-type="figshare-statement">No, I have no data where it is mandated...</p>
```

**After**:
```xml
<p content-type="figshare-statement">No, I have no data where it is mandated...</p>
```

**Recommendation**: Approve. This is the highest-impact, lowest-risk
candidate (resolves 202/951 remaining findings, 21% of the total) and
requires touching only the attribute-copy step already established in
`_copy_author_notes`/verbatim-copy helpers.

---

## Proposed BR — Normalize comma-separated `xref/@rid` to whitespace

**Where**: article.xml, `<xref ref-type="aff" rid="...">` elements
copied verbatim from source's `contrib`/`contrib-group` content.

**Corpus evidence**: 88 remaining findings (37 "syntax of value...not
valid" + 51 "unknown ID") across 20/37 articles. Confirmed present
verbatim in the original source XML — e.g. bcj-2025-3298's source
literally has `rid="aff1, aff2"` and `rid="aff2, aff4"`.

**Why deterministic**: XML's `IDREFS` attribute type is defined as a
whitespace-separated list of `IDREF` tokens — a comma is never a valid
separator or part of a valid token. `"aff1, aff2"` unambiguously means
"references aff1 and aff2" (each already exists as a real affiliation
in the same document); replacing `, ` with a single space
(`"aff1 aff2"`) is the only interpretation consistent with the
existing, unambiguous author-numbering already visible in the
rendered text (e.g. the xref's own display text is literally "1,2").

**Why safe**: no reference target is added, removed, or reinterpreted
— both `aff1` and `aff2` already exist and are already the intended
targets. This is a pure delimiter-syntax correction, not a
content/semantic change.

**Before**:
```xml
<xref rid="aff1, aff2" ref-type="aff">1,2</xref>
```

**After**:
```xml
<xref rid="aff1 aff2" ref-type="aff">1,2</xref>
```
(the xref's own display text, "1,2", is untouched — only the
whitespace-vs-comma separator inside the `rid` attribute value changes)

**Recommendation**: Approve. Second-highest impact (88/951, 9%),
same low-risk profile as the `data-type` rename — a mechanical,
regex-safe normalization (`re.sub(r",\s*", " ", rid_value)`).

---

## Proposed BR — Capture structured reviewer names in reviews.xml

**Where**: reviews.xml, `<contrib contrib-type="reviewer">` /
`<contrib contrib-type="decline">` elements, currently built by
`generators/reviews_xml/review_builder.py`'s `add_reviews_contrib()`.

**Corpus evidence**: 319 occurrences (37/37 articles) of `<string-name>`
— not a valid MECA `reviews-1.0.dtd` element at all (its `contrib`
model only allows `(name | name-alternatives)?`, both requiring
mandatory `surname` + `given-names`). Checked source directly for
**every one of the 37 articles**: **100% have a genuinely structured
`<name><surname>/<given-names></name>` for their reviewer contrib in
source** (e.g. cs-2025-6619's source: `<name><surname>Bennett</surname>
<given-names>...` — plus a `data-reviewer-message` recommendation
signal, also currently discarded). This is a stronger, more complete
evidence base than the prior milestone's single-article sample
suggested.

**Why deterministic**: `ReviewerScorecard`/`DeclineReason` currently
carry only a single flattened `reviewer_name: str` field — the
structured `surname`/`given-names` split exists in source but is never
extracted at all. Capturing it (when present) requires no guessing:
read the already-structured `<surname>`/`<given-names>` elements
directly, exactly as extraction already does for author contributors
elsewhere in this pipeline.

**Why safe**: no name-splitting heuristic is involved — the source
already provides pre-split fields; this only means *reading* them
instead of *not reading them*. When a source genuinely lacks
structured names (not observed in this corpus but plausible for future
articles), the existing `<string-name>` fallback stays exactly as it
is today — this proposal adds a capture path, it doesn't remove the
current one.

**Before**:
```xml
<contrib contrib-type="reviewer">
  <string-name>Simone Brixius-Anderko</string-name>
  <email>...</email>
</contrib>
```

**After**:
```xml
<contrib contrib-type="reviewer">
  <name><surname>Brixius-Anderko</surname><given-names>Simone</given-names></name>
  <email>...</email>
</contrib>
```

**Recommendation**: Approve, with the explicit fallback behavior
above preserved for the (currently unobserved, but foreseeable) case
where source truly has no structured name. Highest single-message
impact (319/951, 34% of all remaining findings) and directly resolves
reviews.xml's only current DTD-invalid element.
