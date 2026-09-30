# Engine Defects Fixed — Quality Improvement Milestone

One confirmed Category A engine defect found and fixed this milestone —
the most serious content-fidelity defect found in this engagement to
date, since it silently substituted the wrong file's bytes under a
correct-looking declared filename, invisible to DTD validation entirely.

## Wrong physical file silently substituted for a declared figure

**File**: `meca-engine/src/meca_engine/extraction/file_resolver.py`,
`_safe_declared_stem()` (added last milestone to guard the "prefix"
tolerance tier against a different, narrower mis-parse).

**Confirmed real occurrence**: `bsr-2025-3821`. Source declares two
distinct figures, `"Fig.2"` and `"Fig.3a-f"`. The physical files present
are `Fig.1a-f.tif`, `Fig.1g-l.tif`, `Fig.2.tif`, `Fig.3g-l.tif`,
`Fig.4.tif`, `Fig.5.tif` — **no `Fig.3a-f.tif` exists**; it is genuinely
absent from the source's physical files (only its "g-l" companion panel
was ever uploaded).

**Root cause**: `_safe_declared_stem("fig.3a-f")` computed
`Path("fig.3a-f").suffix` = `".3a-f"` — 5 characters, no space — and the
existing guard (from last milestone's fix for a different case,
`"1.manuscript highlight yellow 1"`) accepted anything short and
space-free as "looks like a real extension." `".3a-f"` is not a real
extension (it's part of a figure-panel label, not a format suffix), so
the declared name was wrongly truncated to the stem `"fig"`. The
"prefix" tolerance tier then matched `"fig"` against `Fig.2.tif`
(stem `"fig.2"`, which does start with `"fig"`) — packaging `Fig.2`'s
actual image bytes under the `"Fig.3a-f"` declaration. The manifest
ended up with two `<item>` entries (11 declared) pointing at the same
physical file (10 real files) — a real file miscount invisible to
per-file DTD validation, since each file individually is still
well-formed and DTD-valid; the defect is in *which* bytes ended up
attributed to *which* declared entry.

**Fix**: tightened `_safe_declared_stem()`'s "looks like a real
extension" check to also require the tail be purely alphabetic
(`tail.isalpha()`) — `.docx`, `.tif`, `.pdf` pass; `.3a-f` (contains a
digit and a hyphen) does not. With the fix, `"Fig.3a-f"`'s stem is the
whole label; no physical file's stem matches it via "prefix" or
"normalized" tolerance either, so it now correctly falls through to the
existing RR-002 skip — an honest "file missing" recovery instead of a
silent wrong substitution.

**Verified impact, scoped precisely**: re-ran the full 97-article
corpus before/after. Exactly one status change:
`bsr-2025-3821`: `certified_with_recovery` → `partial_certification`
(a real file is now honestly reported as missing, rather than the
package looking complete while actually containing a misattributed
image). Checked all 37 real "prefix"-tier tolerance matches across the
corpus individually — this was the only genuinely wrong one; every
other prefix match (e.g. `"Table 1"` → `"Table 1 (1).docx"`,
`"Figure 2.pdf"` → `"Figure 2.jpg"`) is a legitimate disambiguating or
extension-normalizing match, unaffected by this fix. DTD `pass`/`error`
counts unchanged (91 error / 4 pass, both runs) — this defect was
invisible to DTD validation by construction, which is exactly why the
source-vs-generated comparison this milestone required was necessary to
find it.

## Regression test

`tests/unit/extraction/test_file_resolver.py::test_pseudo_extension_never_causes_a_wrong_figure_substitution`
— reproduces the exact `bsr-2025-3821` shape (a `"Fig.3a-f"` declaration
with `Fig.1a-f.tif`/`Fig.2.tif`/`Fig.3g-l.tif` physically present, no
`Fig.3a-f.tif`) and asserts it is skipped, not wrongly resolved. All 35
tests in this file (34 pre-existing + 1 new) pass.

## Everything else checked, found correct

Programmatic, corpus-wide (not sampled) checks performed across all 95
real generated packages, none of which surfaced a further defect:

- Cross-file `id` uniqueness (article.xml + reviews.xml + manifest.xml +
  transfer.xml combined, per article) — 0 collisions.
- `manifest.xml` `xlink:href` resolution against the zip's real `files/`
  contents — 0 missing targets.
- `manifest.xml` file-item count vs. physical file count — exactly 1
  mismatch found (the defect above); 0 after the fix.
- Duplicate `id` attributes within a single file, beyond the
  already-documented `con`/`aff` source-collision pattern — 0 found.
- Dangling `rid`/IDREF references — 5 articles, all already-documented
  (either the known `bsr-2025-3807` verbatim-source dangling
  affiliation reference, or a `bibr`-type citation reference with no
  `<ref-list>` in source — this engine doesn't extract/generate a
  reference list at all, a pre-existing, documented characteristic, not
  new).
- Content-fidelity spot checks (ORCID ids, keywords, permissions,
  corresponding-author emails, history dates, funding groups, equal-
  contribution footnotes): source counts fully preserved in generated
  output for every article carrying that data — 0 loss found in any of
  these dimensions.
