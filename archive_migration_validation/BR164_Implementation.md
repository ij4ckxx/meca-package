# BR-164 Implementation — Publisher Abbreviation Journal Title

Deterministic, lossless, config-driven — follows the existing
Business Rule / config-mapping architecture exactly (same shape as
`article-type-mapping.yaml`/`ArticleTypeMappingConfig`). No Recovery
Rule, PackageBuilder, Processing Service, or Dashboard code touched.

## What BR-164 does

`journal-title-group` sometimes has no
`<abbrev-journal-title abbrev-type="publisher">` at all, even though the
value is fully determined by `journal-id[@journal-id-type="publisher-id"]`
via a fixed, closed mapping. When missing, the engine now inserts it —
immediately after `<journal-title>`, before any other existing
`abbrev-journal-title` elements — using only a value from that closed
mapping, never a guess. An already-present publisher abbreviation is
never duplicated; an unrecognized publisher-id leaves the XML completely
unchanged and is recorded as a Validation Only finding instead.

## New files

- `meca-engine/config/publisher-abbreviation-mapping.yaml` — the mapping
  itself (`cs→CS, bcj→BCJ, bst→BST, bsr→BSR, etls→ETLS, ebc→EBC`), no
  default/fallback field by design (unlike `article-type-mapping.yaml` —
  an unrecognized key must never be guessed at).
- `meca-engine/schemas/config-schema/publisher-abbreviation-mapping.schema.json`
  — validates it, same pattern as every other mapping schema.

## Modified files

- `meca-engine/src/meca_engine/config/schema.py` — new
  `PublisherAbbreviationMappingConfig` dataclass (`mappings: Mapping[str, str]`).
- `meca-engine/src/meca_engine/config/loader.py` — new
  `load_publisher_abbreviation_mapping()`, same pattern as
  `load_article_type_mapping()`.
- `meca-engine/src/meca_engine/generators/xml/helpers.py` — new
  `insert_after_tag(parent, child, after_tag)`: a small, generic,
  reusable structural helper (matching the `rename_attribute_on_tag`/
  `normalize_idrefs_separator` precedent from BR-161/162) — repositions
  an already-appended element to right after a named sibling tag. Not
  BR-164-specific; usable by any future rule needing a deterministic
  insertion position.
- `meca-engine/src/meca_engine/generators/article_xml/generator.py` —
  `ArticleXmlGenerator.__init__` gained a `publisher_abbreviation_mapping`
  parameter (mirrors `article_type_mapping`/`license_templates`);
  `_copy_journal_meta()` now calls the new
  `_apply_publisher_abbreviation_rule()` after appending the copied
  `journal-meta` to the tree. No XML fragment is ever hardcoded — the
  new element is built with the existing `XmlDocumentBuilder.create_element`
  API, exactly like every other generator in this codebase.
- `meca-engine/src/meca_engine/service/service_factory.py` — wires
  `publisher_abbreviation_mapping=loader.load_publisher_abbreviation_mapping()`
  into the one `ArticleXmlGenerator(...)` construction site.
- `01_BUSINESS_RULE_BOOK.md` — added BR-164 to Section K, updated the
  Rule Count Summary (164 total, Confirmed 112, Medium priority 39).
- `meca-engine/src/meca_engine/reporting/reproducibility.py` — bumped
  `BUSINESS_RULE_BOOK_VERSION` to `"164 rules (BR-001-BR-164)"`.
- `VERSION.md` (repo root) — same version bump.
- Test fixtures/call sites updated for the new required constructor
  parameter: `tests/unit/generators/article_xml/conftest.py`,
  `tests/unit/generators/article_xml/test_generator.py`,
  `tests/golden/test_article_xml_golden.py`,
  `tests/golden/test_package_assembly_golden.py`,
  `tests/unit/config/test_loader.py`,
  `tests/fixtures/config/publisher-abbreviation-mapping.yaml` (new).

## One refinement made after seeing real data

The lookup is case-insensitive. Real corpus evidence
(`CS-2025-6808`, `bsr-2025-3516`, `bst-2025-3088`) shows
`journal-id[@journal-id-type="publisher-id"]` is sometimes uppercase
(`"CS"`) for the same journal a lowercase mapping key (`"cs"`) already
identifies — not a different, unrecognized publisher, just a casing
variant of a known one. Matching it is not a guess (the matched value is
still one of the six fixed, closed keys); this mirrors the identical
case-normalization fix already applied to the article-id-prefix lookup
in `service/worker.py` earlier this engagement. Genuinely unrecognized
values (e.g. `"bio"`, seen on `ebc-2024-3002`/`ebc-2025-3007`) still
correctly produce the Validation Only warning, case-insensitivity
notwithstanding.

## Reporting — zero additional code needed

BR-164's diagnostics (`"BR-164: generated publisher abbreviation ..."` /
`"BR-164: no publisher abbreviation mapping exists ..."`) are picked up
automatically by `packaging/conversion_report.py`'s existing
`_BUSINESS_RULE_ID_PATTERN = re.compile(r"BR-\d+")` regex — the exact
same mechanism BR-161/162/163 already use. This is why Business Rule
Timeline, Certification Report, Migration Audit, and
`conversion-report.json` all show BR-164 findings with no Dashboard or
reporting-layer code change at all.
