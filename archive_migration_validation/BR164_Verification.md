# BR-164 Verification

Focused, as instructed — targeted unit tests plus one full corpus batch
run, no excessive evidence.

## Targeted unit tests

`tests/unit/generators/article_xml/test_generator.py` — 4 new tests:
generates the abbreviation and inserts it in the correct position when
missing; never duplicates when already present; leaves the XML
completely unchanged and records a Validation Only warning for an
unrecognized publisher-id; the lookup is case-insensitive for a known
key. `tests/unit/config/test_loader.py` — 1 new test confirming the new
config loads as a typed dataclass with all 6 real mappings.

Full suite: `pytest tests/` — **1168 passed, 3 failed** (the same 3
pre-existing, unrelated golden ICAM snapshot failures documented in
every prior milestone this session). `ruff check`, `ruff format --check`,
`mypy --strict` all clean across every modified file.

## One full corpus batch run

`Input/` (97 articles), all 7 checklist items confirmed directly against
the real output:

1. **BR-164 fired only for journals missing the publisher abbreviation**
   — 66 articles got a new `<abbrev-journal-title abbrev-type="publisher">`;
   2 articles (`ebc-2024-3002`, `ebc-2025-3007`, publisher-id `"bio"`,
   genuinely not in the mapping) correctly produced a Validation Only
   warning and were left unchanged; every other article already had one
   or belongs to a journal not among the 6.
2. **No duplicate publisher abbreviation exists** — checked all 95
   generated packages' real `article.xml` directly: 0 articles with more
   than one `abbrev-journal-title[@abbrev-type="publisher"]`.
3. **Every generated article.xml now contains the publisher abbreviation
   for the supported journals** — checked all 95 packages: 0 articles
   with a recognized publisher-id (`cs`/`bcj`/`bst`/`bsr`/`etls`/`ebc`,
   case-insensitive) still missing it.
4. **DTD validation still passes exactly as before** —
   `{'error': 91, 'pass': 4}`, identical before and after this change
   (expected: `abbrev-journal-title` is optional in the DTD either way).
5. **No package status changes** — identical distribution before/after:
   `certified_with_warnings: 14, certified_with_recovery: 71,
   partial_certification: 10, engine_failure: 0, fatal_failure: 2`.
6. **No Recovery Rule changes** — `model/recovery_rules.py`,
   `extraction/file_resolver.py` untouched.
7. **No Dashboard code changes required** — confirmed BR-164 findings
   flow through the existing, unmodified
   `_BUSINESS_RULE_ID_PATTERN` regex mechanism into
   `business_rule_findings`, the same field every dashboard/reporting
   surface already reads.

## Spot-checked real output

`BCJ-2024-0504` (previously had no publisher abbreviation at all):

```
<journal-title-group>
<journal-title>Biochemical Journal</journal-title>
<abbrev-journal-title abbrev-type="publisher">BCJ</abbrev-journal-title>
</journal-title-group>
```

`cs-2024-5133` (previously had one untyped `abbrev-journal-title`):

```
<journal-title-group>
<journal-title>Clinical Science</journal-title>
<abbrev-journal-title abbrev-type="publisher">CS</abbrev-journal-title>
<abbrev-journal-title>CS</abbrev-journal-title>
</journal-title-group>
```

Both match the required order (`journal-title` → publisher abbreviation
→ any remaining abbreviations) exactly.
