# Milestone 4 Implementation Report — Metadata Extraction Layer

Baseline: Milestones 1 (Foundation), 2 (Input & Staging Layer), and 3 (XML
Parsing Layer), all approved. Scope: extracting structured information out
of a Milestone 3 `ParsedDocument` into seven independent, typed metadata
groupings (Article, Contributor, Journal, Workflow, Custom, Assets,
Cross-References). **No ICAM construction, no MECA XML generation, no
business-rule transformation beyond identifying and extracting values, no
DOI generation, no validation engine, no packaging, no review
reconstruction was implemented** — see §9 for what remains deferred and
why.

---

## 1. Directory Tree Changes

```
src/meca_engine/extraction/                [existing package, extended]
├── __init__.py                             [MODIFIED] re-exports every new name
├── parsed_model.py                         [MODIFIED] DiagnosticCategory + DUPLICATE_ID,
│                                           MISSING_REQUIRED_VALUE (additive)
├── diagnostics.py                          [MODIFIED] + find_duplicate_ids,
│                                           find_malformed_references
├── metadata_models.py                      [NEW] every Milestone 4 output type (see §3)
├── article_metadata_extractor.py           [NEW] extract_article_metadata
├── contributor_metadata_extractor.py       [NEW] extract_contributor_metadata
├── journal_metadata_extractor.py           [NEW] extract_journal_metadata
├── workflow_metadata_extractor.py          [NEW] extract_workflow_metadata
├── custom_metadata_extractor.py            [NEW] extract_custom_metadata
├── asset_metadata_extractor.py             [NEW] extract_asset_metadata
├── cross_reference_extractor.py            [NEW] extract_cross_references
└── metadata_extraction.py                  [NEW] extract_all_metadata (orchestrator + logging)

tests/
├── unit/extraction/                        [EXTENDED]
│   ├── test_diagnostics.py                 [MODIFIED] + find_duplicate_ids/find_malformed_references cases
│   ├── test_parsed_model.py                [MODIFIED] DiagnosticCategory value-set assertion updated
│   ├── test_article_metadata_extractor.py  [NEW]
│   ├── test_contributor_metadata_extractor.py [NEW]
│   ├── test_journal_metadata_extractor.py  [NEW]
│   ├── test_workflow_metadata_extractor.py [NEW]
│   ├── test_custom_metadata_extractor.py   [NEW]
│   ├── test_asset_metadata_extractor.py    [NEW]
│   ├── test_cross_reference_extractor.py   [NEW]
│   ├── test_metadata_extraction.py         [NEW] orchestrator + logging integration
│   ├── test_metadata_golden_snapshots.py   [NEW]
│   └── _metadata_snapshot_utils.py         [NEW] test-only ExtractionBundle -> JSON-safe dict serializer
└── fixtures/extraction/                    [EXTENDED]
    ├── metadata_sample.xml                 [NEW] purpose-built synthetic fixture exercising every extractor
    └── snapshots/metadata_sample.snapshot.json  [NEW] checked-in golden snapshot

golden_baseline/                            [NEW top-level directory]
├── README.md                               structure, regeneration, and size notes
├── CS-2025-6808/{01_parsed_object.json, 02_extracted_metadata.json, 03_icam.json (placeholder),
│                 04_raw.xml..08_transfer.xml (placeholders)}
├── CS-2025-8493_C/  (same shape)
└── cs-2025-8827/    (same shape)
```

**Stub packages left untouched**: `model/` (the ICAM itself), `transform/`, `generators/*`, `validation/*`, `packaging/`, `output/`, `registry/*`, `retry/`, `recovery/`, `reporting/`, `monitoring/`. `input/`, `checkpoint/`, `orchestrator/` (Milestone 2) also untouched.

---

## 2. Extractor Classes / Functions

Seven pure functions, one per named area, each `(document: ParsedDocument) -> tuple[Model, tuple[ParseDiagnostic, ...]]`:

| Function | Module | Model returned |
|---|---|---|
| `extract_article_metadata` | `article_metadata_extractor` | `ArticleMetadata` |
| `extract_contributor_metadata` | `contributor_metadata_extractor` | `ContributorMetadata` |
| `extract_journal_metadata` | `journal_metadata_extractor` | `JournalMetadata` |
| `extract_workflow_metadata` | `workflow_metadata_extractor` | `WorkflowMetadata` |
| `extract_custom_metadata` | `custom_metadata_extractor` | `CustomMetadata` |
| `extract_asset_metadata` | `asset_metadata_extractor` | `AssetMetadata` |
| `extract_cross_references` | `cross_reference_extractor` | `CrossReferenceMap` |

Each is independently importable, independently unit-tested (no shared mutable state, no logger dependency), and takes zero position on business semantics beyond identifying/grouping source values. `extract_all_metadata(document, logger)` in `metadata_extraction.py` is the one orchestrating entry point — see §4.

**No new exception types were introduced.** Every extraction gap (missing element, empty value) is reported as a `ParseDiagnostic`, never raised — consistent with this layer's "identify and extract, do not validate business semantics" boundary. `metadata_models.py` contributes 15 new frozen dataclasses (see §3); no new `MecaEngineError` subclass was justified.

---

## 3. Metadata Models

```
ExtractionBundle
├── article: ArticleMetadata
│     ├── identifiers: tuple[ArticleIdentifier(id_type, value), ...]
│     ├── title, subtitle, article_type, publication_status, language: str | None
│     ├── history_dates: tuple[DateRecord(date_type, year, month, day), ...]
│     └── pub_dates: tuple[DateRecord, ...]
├── contributors: ContributorMetadata
│     ├── authors / editors / other_contributors: tuple[ContributorRecord, ...]
│     │     (contrib_type, surname, given_names, orcid, emails, affiliation_ref_ids, is_corresponding)
│     └── affiliations: tuple[AffiliationRecord(element_id, institution, country, raw_text), ...]
├── journal: JournalMetadata
│     (journal_title, issns, publisher_name, volume, issue, fpage, lpage, elocation_id, doi_related_ids)
├── workflow: WorkflowMetadata
│     └── events: tuple[WorkflowEventRecord(event_tag, fields, raw_element), ...]
├── custom: CustomMetadata
│     └── entries: tuple[CustomMetaEntry(name, value_text, named_content), ...]
├── assets: AssetMetadata
│     └── assets: tuple[AssetRecord(asset_tag, element_id, label, file_references), ...]
├── cross_references: CrossReferenceMap
│     ├── id_index: tuple[(id_value, tag), ...]        (compact — not full ParsedElement trees)
│     └── references: tuple[ReferenceRecord(referencing_tag, referencing_ref_type,
│                                           attribute_name, target_ids), ...]
└── diagnostics: tuple[ParseDiagnostic, ...]            (every extractor's diagnostics, flattened)
```

Every type is a frozen dataclass, consistent with Milestones 2 and 3. Field values are preserved verbatim from source — **no normalization, no renaming of content, no classification** (e.g. `contrib_type`/`asset_tag`/`id_type` are stored exactly as the source wrote them; sorting authors from editors relies only on that verbatim value, never reinterpreted).

**Two documented, non-blocking open questions** (flagged rather than guessed at):
- `ArticleMetadata.publication_status` — no confirmed source-system convention was identified during analysis; the field is populated best-effort from a `publication-status` attribute if present, `None` otherwise.
- `WorkflowMetadata` event tag names — workflow/processing-log data is not a standard JATS structure; `extract_workflow_metadata` defaults to `("event", "log-entry", "stage")` and accepts a caller-supplied override once the actual source convention is confirmed. Running the real pipeline against all 3 sample packages (see §8) found `<event>` elements matching the default in every case that carried processing-history data.

---

## 4. Extraction Flow

```
extract_all_metadata(document: ParsedDocument, logger: StructuredLogger) -> ExtractionBundle
  │
  ├─ for each of the 7 extractors, in a fixed order (article, contributor,
  │  journal, workflow, custom, asset, cross-reference):
  │    logger.info("Starting ... extraction")
  │    with PerformanceTimer(logger, "extraction.metadata.<name>"):
  │        model, diagnostics = extract_<name>_metadata(document)
  │    diagnostics.extend(...)
  │    logger.info("Completed ... extraction", context={"diagnostic_count": ...})
  │
  └─ return ExtractionBundle(..., diagnostics=tuple(all diagnostics))
```

Logging is concentrated entirely in this orchestrator — every extractor stays a pure function with no logger dependency, maximizing independent testability (Design Decision, this milestone: "logging is an orchestration concern, not baked into each extractor," matching the task's own phrasing that logging happens at "extractor start, completion and diagnostics"). `journal_metadata_extractor` internally re-invokes `extract_article_metadata` once to populate `doi_related_ids` as a convenience grouping — this is documented in its docstring as *not* a second independent extraction pass and does not double-log (the orchestrator only logs its own top-level call to each of the 7 functions).

---

## 5. Golden Snapshot Strategy

- **Fixture**: `tests/fixtures/extraction/metadata_sample.xml` — a small, purpose-built synthetic document (not a copy of any real sample package) exercising every extractor path in one file: dual article-ids (doi + publisher-id), title/subtitle, history + pub dates, three contributors (author with `corresp="yes"`, plain author, editor), two affiliations, journal title/ISSNs (epub+ppub)/publisher, volume/issue/pages/elocation-id, two custom-meta entries (one with `named-content`), three assets (`fig`/`table-wrap`/`supplementary-material`, two with file references), and cross-references (`aff`, `fig`, and multi-token `bibr` ref-types).
- **Serialization**: `tests/unit/extraction/_metadata_snapshot_utils.py`'s `extraction_bundle_to_snapshot_dict()` converts an `ExtractionBundle` into a JSON-safe, order-stable `dict` — mirrors Milestone 3's `_snapshot_utils.py` pattern one layer up.
- **Comparison**: `test_metadata_golden_snapshots.py` parses the fixture fresh (via `XmlLoader`) and runs `extract_all_metadata` on every test run, asserting structural equality against the checked-in `metadata_sample.snapshot.json`.
- **Governance**: identical to Milestone 3 — the snapshot JSON is checked in and only ever regenerated deliberately, reviewed in the same PR as the triggering code change, never auto-regenerated by a test run.

---

## 6. Test Summary

| Test file | Test functions | Covers |
|---|---|---|
| `test_diagnostics.py` (additions) | 8 new | `find_duplicate_ids`, `find_malformed_references` |
| `test_parsed_model.py` (update) | 1 updated | `DiagnosticCategory` value-set now includes the 2 new members |
| `test_article_metadata_extractor.py` | 5 | identifiers, title/subtitle, article-type, dates, missing-field diagnostics |
| `test_contributor_metadata_extractor.py` | 7 | author/editor/other sorting, corresp detection (both forms), orcid/emails/aff-refs, affiliations |
| `test_journal_metadata_extractor.py` | 5 | title/issn/publisher, volume/issue/pages, doi_related_ids reuse, missing-title diagnostic |
| `test_workflow_metadata_extractor.py` | 4 | flattening, default tag names, custom tag names, empty case |
| `test_custom_metadata_extractor.py` | 5 | name/value, named-content, unfiltered inclusion, empty case, missing-name fallback |
| `test_asset_metadata_extractor.py` | 5 | label/file-reference extraction, default tag set, custom tag set, no-reference case, empty case |
| `test_cross_reference_extractor.py` | 6 | id index, ref-type + multi-token targets, duplicate-id / malformed-reference diagnostics, skip-without-attribute, empty case |
| `test_metadata_extraction.py` | 4 | bundle assembly, diagnostic flattening, start/completion logging, performance-event count |
| `test_metadata_golden_snapshots.py` | 2 | full-bundle structural snapshot match; snapshot-file sanity guard |
| **Total new/modified** | **47** | |

Full suite (all 4 milestones combined): **347 passing tests**, verified in the same virtual environment used for Milestones 1-3, with `ruff check`, `ruff format --check`, and `mypy --strict` all clean on both `src/` and `tests/`.

---

## 7. Coverage Report

```
Name                                                           Stmts   Miss  Cover
------------------------------------------------------------------------------------
src/meca_engine/extraction/article_metadata_extractor.py          30      0   100%
src/meca_engine/extraction/asset_metadata_extractor.py             17      0   100%
src/meca_engine/extraction/contributor_metadata_extractor.py       46      0   100%
src/meca_engine/extraction/cross_reference_extractor.py            19      0   100%
src/meca_engine/extraction/custom_metadata_extractor.py            16      0   100%
src/meca_engine/extraction/diagnostics.py                          38      0   100%
src/meca_engine/extraction/journal_metadata_extractor.py           26      0   100%
src/meca_engine/extraction/metadata_extraction.py                  50      0   100%
src/meca_engine/extraction/metadata_models.py                     104      0   100%
src/meca_engine/extraction/workflow_metadata_extractor.py          10      0   100%
------------------------------------------------------------------------------------
Milestone 4 module subtotal                                       356      0   100%
------------------------------------------------------------------------------------
TOTAL (whole src/, incl. Milestones 1-3 + untouched stubs)        1762     19    99%
```

**Target ("at least 95% coverage for all new modules") is met: every Milestone 4 module is at 100% coverage.** The remaining 19 uncovered lines project-wide are entirely in still-unimplemented future-milestone stub packages, unchanged from Milestone 3.

---

## 8. Architecture Compliance Report

See the companion document: **`MILESTONE_4_ARCHITECTURE_COMPLIANCE_REPORT.md`** in this same directory.

**Golden Baseline Repository (additional recommendation, actioned this milestone)**: `golden_baseline/` was created at the project root, seeded from all 3 real sample packages (`Input/CS-2025-6808.zip`, `Input/CS-2025-8493_C.zip`, `Input/cs-2025-8827.zip`) by extracting only each package's main XML file (never modifying the source zips) and running it through the actual Milestone 3 `XmlLoader` and Milestone 4 `extract_all_metadata`. Both currently-achievable stages (`01_parsed_object.json`, `02_extracted_metadata.json`) are populated with real output; `03_icam.json` through `08_transfer.xml` are documented placeholders. All 3 real packages parsed and extracted cleanly (0 fatal errors); diagnostic counts (32/15/94 parse-level, 50/11/119 metadata-level across the three) are non-fatal observations, not failures — see `golden_baseline/README.md` for regeneration instructions and a size note (parsed-object snapshots run several MB per article, expected for an unfiltered full-tree reference artifact).

---

## 9. Deferred Work for Milestone 5

Per the current task's explicit exclusion list, all deferred:

- **Internal Canonical Article Model** (`model.article.ArticleModelBuilder`, `ArticleModel`) — this milestone's `ExtractionBundle` is exactly the kind of grouped, still-unnormalized input the ICAM builder is designed to consume next; no ICAM type or builder logic exists yet.
- **Custom-meta classification** (Business Rule Book deny-list logic) — `CustomMetadata.entries` includes every `custom-meta` entry found, unfiltered; deciding which entries are business-significant vs. noise is Milestone 5's classifier, built on top of this extraction.
- **MECA XML generation** (all 5 generators), **Validation Engine**, **Package Builder**, **Output Writer**, **DOI Registry/generation** — untouched stub packages, per scope, unaffected by this milestone.
- **File-manifest resolution** (BR-011/BR-014) — this milestone's `AssetMetadata` recognizes JATS structural tags and reuses Milestone 3's generic `discover_file_references`; real sample packages (see `golden_baseline/`) confirm both `graphic`/`xlink:href`-bearing assets *and* a large `custom-meta` volume (395 entries in one sample) carry file-relevant business data — reconciling the two into the business-rule-authoritative file manifest remains Milestone 5's job.
- **Round resolution** (BR-010) — this milestone's `WorkflowMetadata` flattens `event`/`log-entry`/`stage` elements generically; parsing/ordering by the actual `vocab-identifier`/snapshot-sequence convention remains deferred.

**Explicit dependency check before Milestone 5 begins**: `ExtractionBundle` (this milestone's output) is exactly the input the ICAM builder is designed to consume. Nothing left open in this milestone blocks that work. Two open questions worth flagging for Milestone 5 planning (documented, not blocking): (1) the exact `publication-status` source convention, and (2) whether `WorkflowMetadata`'s default event tag names need widening once more real samples are examined against the golden baseline.
