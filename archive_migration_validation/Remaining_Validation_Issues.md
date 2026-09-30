# Remaining Validation Issues

Every DTD finding still present after the Category A fixes
(`DTD_Fix_Summary.md`), classified as Category B (Source Data Issue),
C (Business Rule Candidate — see `Proposed_Business_Rules.md`), D
(Recovery Rule Candidate — see `Proposed_Recovery_Rules.md`), or E
(Validation Only). None of these were changed in code. All are
surfaced in `ConversionReport.validation_report`, the standalone
validation report, and the dashboard, tagged with their category
(`meca_engine.validation.dtd_issue_classifier`).

## Category E — Validation Only (cannot safely repair)

| Finding | File | Corpus impact | Why it can't be safely auto-fixed |
|---|---|---|---|
| `<fn>` containing a `<list>` directly (DTD requires `label?, p+`) | article.xml | 7/37 articles | Flattening list items into sibling `<p>` elements would satisfy the DTD but discards the list's own structure (ordered vs. unordered, item grouping) — a semantic change, not a syntax fix. |
| `ext-link/@target` not declared | article.xml | 4/37 articles | Presentational (browser tab behavior), but stripping it is still an assumption that it's safe to discard — not made unilaterally. |
| `p/@dir` not declared | article.xml | 3/37 articles | Same reasoning as `target` — `dir="ltr"` may be redundant boilerplate or may matter for bidi text elsewhere in the corpus; not assumed. |
| `award-id/@award-id-type` not declared, no equivalent attribute exists in this JATS DTD variant (checked: only `rid`, `award-type`, `specific-use`, `xml:lang` are declared) | article.xml | 1 article, 2 occurrences | No rename target exists (unlike `data-type`→`content-type`); there is nothing deterministic to propose. |
| `xref[@ref-type="bibr"]` pointing to a bibliography entry (e.g. `rid="R64"`) that doesn't exist anywhere in the generated article.xml | article.xml | 4/37 articles | **New finding, flagged for separate investigation** — article.xml has no `<ref-list>`/`<back>` section at all in the current corpus; in-text citations that survive (via verbatim `author-notes`/`fn` copying) point at nothing. This looks like a real gap in bibliography/reference-list generation, not a small spec-alignment tweak — likely a substantially larger effort than this milestone's scope (`Do not rewrite generators unnecessarily`). Recommended as a separate, dedicated investigation, not attempted here. |

## Category B — Source Data Issue

| Finding | File | Corpus impact | Why it's the source, not the engine |
|---|---|---|---|
| Duplicate `aff` id where the second occurrence carries a genuinely *different* institution's address (not a content-free stub) | article.xml | 7/37 articles (`bst-2025-3107_C`, `bst-2025-3127`, `bst-2025-3131`, `ebc-2025-3045_C`, `ebc-2025-3048_C`, `ebc-2025-3050_C`, `ebc-2025-3057_C`) | Confirmed per-article: e.g. `bst-2025-3127`'s two `aff1` blocks are "Department of Physics and Astronomy, University of Wisconsin-..." and "University of Wisconsin–Milwaukee, Milwaukee, ...". Both are real, non-redundant addresses — the source itself assigned the same id to two different facts. Dropping either would delete real data; renaming risks orphaning one from any `xref` that points at "aff1". See `Proposed_Recovery_Rules.md` for why an automatic fix isn't recommended. |

## Category C — Business Rule Candidates

See `Proposed_Business_Rules.md` for full write-ups (deterministic
reasoning, before/after examples, recommendation). Summary:

| Finding | File | Corpus impact |
|---|---|---|
| `<p data-type="...">` — JATS declares `content-type`, not `data-type` | article.xml | 202 occurrences, 37/37 articles |
| `xref/@rid="aff1, aff2"` — comma-separated IDREFS (XML requires whitespace only) | article.xml | 88 occurrences (37 "syntax invalid" + 51 "unknown ID"), 20/37 articles |
| `<string-name>` (not a valid MECA element) instead of structured `<name>` | reviews.xml | 319 occurrences, 37/37 articles — **100% of sampled reviewer contribs have structured surname/given-names available in source** |

## Category totals (corpus-wide, this milestone's final batch)

| Category | Finding count |
|---|---|
| Business Rule Candidate | 924 |
| Validation Only | 20 |
| Source Data Issue | 7 |
| Recovery Rule Candidate | 0 (the one candidate considered — duplicate-aff renumbering — was evaluated and explicitly **not** recommended; see `Proposed_Recovery_Rules.md`) |

manifest.xml and transfer.xml remain 37/37 DTD-valid with zero
remaining findings of any category.
