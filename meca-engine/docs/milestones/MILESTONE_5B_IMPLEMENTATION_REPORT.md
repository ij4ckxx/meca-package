# Milestone 5B Implementation Report — Metadata → ICAM Transformation

Baseline: Milestones 1 (Foundation), 2 (Input & Staging Layer), 3 (XML
Parsing Layer), 4 (Metadata Extraction Layer), and 5A (ICAM Domain Model),
all approved. Scope: consuming Milestone 4's `ExtractionBundle` (plus,
where the LLD requires raw structural access, Milestone 3's
`ParsedDocument` directly) and producing a fully populated, frozen
`ArticleModel`. **No XML generation, no package generation, no publishing
output, no DOI generation, and no business-rule transformation that
modifies values was implemented** — see §9 for what remains deferred and
why.

---

## 1. Directory Tree Changes

```
src/meca_engine/extraction/                [EXTENDED — completes this package's LLD-designated scope]
├── round_resolver.py                      [NEW] resolve_rounds — reads <article-version> directly (BR-010)
├── custom_meta_classifier.py              [NEW] classify — CustomMetadata -> CustomMetaStore (BR-071/075)
├── file_resolver.py                       [NEW] resolve_files — FileEntry -> ResolvedFile (BR-011/013/016/017)
├── article_metadata_extractor.py          [MODIFIED] + display_channel_subject, heading_subjects,
│                                           copyright_statement/year, keywords, funding_statements,
│                                           word/ref/fig_count (evidence-based Milestone 4 extensions)
├── journal_metadata_extractor.py          [MODIFIED] + journal_id, abbrev_titles
├── custom_metadata_extractor.py           [MODIFIED] + attributes (the <custom-meta> element's own
│                                           attributes — the actual classification signal source)
├── metadata_models.py                     [MODIFIED] corresponding field additions to
│                                           ArticleMetadata/JournalMetadata/CustomMetaEntry
└── __init__.py                            [MODIFIED] re-exports every new name

src/meca_engine/transform/                 [was an empty stub — fully implemented]
├── __init__.py                            re-exports every public name
├── coordinator.py                         TransformationCoordinator.build_model(...)
├── identity_transformer.py                build_identity
├── journal_transformer.py                 build_journal_meta
├── contributor_transformer.py             build_contributors_and_affiliations
├── workflow_transformer.py                build_workflow_log
└── body_fragment_builder.py               build_body_fragment (parsed-tree -> XML text, not "generation")

config/media-types.yaml                    [NEW] standard extension->MIME table (ADR-008/009) — operational,
                                            not business-value, config; needed for File Resolution to run
src/meca_engine/config/loader.py           [MODIFIED] + load_media_type_config()

golden_baseline/*/03_icam.json             [NEW] populated (was a placeholder since Milestone 4)

tests/
├── unit/extraction/                       [EXTENDED] test_round_resolver.py, test_custom_meta_classifier.py,
│                                           test_file_resolver.py (all new); extended tests for every
│                                           modified extractor
├── unit/transform/                        [NEW] test_identity_transformer.py, test_journal_transformer.py,
│                                           test_contributor_transformer.py, test_workflow_transformer.py,
│                                           test_body_fragment_builder.py, test_coordinator.py
├── unit/config/test_loader.py             [EXTENDED] + load_media_type_config test
└── golden/                                [NEWLY POPULATED — was an empty Milestone-1 stub]
    ├── conftest.py                        extracts the 3 real Input/*.zip samples into tmp_path
    ├── test_metadata_to_icam_golden.py     Metadata -> ICAM golden regression, parametrized ×3
    └── expected_output/*.icam.snapshot.json   checked-in golden snapshots (one per real sample)
```

**Stub packages left untouched**: every `generators.*` subpackage, `validation` (business-rule Validation Engine), `packaging`, `output`, `registry`, `retry`, `recovery`, `reporting`, `monitoring`. `model` (Milestone 5A) untouched — every ICAM type this milestone populates was already fully defined.

---

## 2. Transformation Services

| Service | Module | Responsibility | Package (per LLD placement) |
|---|---|---|---|
| Round Resolution | `round_resolver.resolve_rounds` | `<article-version>`/`vocab-identifier` → `RoundIndex` (BR-010) | `extraction` (§4.4) |
| Custom-Meta Classification | `custom_meta_classifier.classify` | Flat `CustomMetadata` → typed `CustomMetaStore` (BR-071/075) | `extraction` (§4.3) |
| File Resolution | `file_resolver.resolve_files` | `FileEntry` → physical file + checksum/size/media-type (BR-011/013/016/017) | `extraction` (§4.5) |
| Identity Transformation | `identity_transformer.build_identity` | `ArticleIdentity`; no DOI generation | `transform` (new) |
| Journal Transformation | `journal_transformer.build_journal_meta` | Verbatim `JournalMeta` mapping | `transform` (new) |
| Contributor Transformation | `contributor_transformer.build_contributors_and_affiliations` | Authors/affiliations/model-internal keys/corresponding emails | `transform` (new) |
| Workflow Transformation | `workflow_transformer.build_workflow_log` | Pass-through `WorkflowLog` (see §9) | `transform` (new) |
| Body Fragment Construction | `body_fragment_builder.build_body_fragment` | `<body>` subtree → XML text (verbatim copy, not generation) | `transform` (new) |

Each is independently importable and independently unit-tested (no shared mutable state); the LLD places the first 3 in `extraction` (since they need raw structural/filesystem access no Milestone 4 extractor provides) and reserves `transform` for the 5 that build directly from `ExtractionBundle` alone — see §4 for the full reasoning behind this split.

---

## 3. Coordinator Architecture

```
TransformationCoordinator(media_type_config, logger)
  .build_model(article_id, source_object_key, staged_root, parsed_document, extraction_bundle) -> ArticleModel
    │
    ├─ logger.info("Transformation started")
    ├─ with PerformanceTimer(...):                      # nullcontext() when no logger supplied
    │    ├─ builder.set_identity(build_identity(...))
    │    ├─ builder.set_journal_meta(build_journal_meta(...))
    │    ├─ builder.set_article_meta(_build_article_meta(...))   # calls build_contributors_and_affiliations
    │    ├─ builder.set_body_fragment(build_body_fragment(...))
    │    ├─ custom_meta_store = classify(...)
    │    ├─ custom_meta_store = replace(custom_meta_store, workflow_log=build_workflow_log(custom_meta_store))
    │    ├─ builder.set_custom_meta(custom_meta_store)
    │    ├─ builder.set_rounds(resolve_rounds(parsed_document, article_id=article_id))
    │    └─ builder.set_resolved_files(resolve_files(custom_meta_store.file_entries, staged_root, ...))
    │
    ├─ model = builder.freeze()                          # ModelBuildError propagates unchanged if incomplete
    └─ logger.info("Transformation completed")
    → return model
```

Every typed error (`RoundResolutionError`, `FileReferenceMissingError`, `ModelBuildError`) propagates unchanged — the coordinator never catches or re-wraps, per the LLD's exact "Error Handling" description of this class (§4.6).

---

## 4. Mapping Strategy

- **Identity**: `article_id`/`source_object_key` are supplied by the *caller* (Milestone 2's staging output — never derivable from XML content, per BR-003). `publisher_id_value`/`doi_article_id_value` come from `ArticleMetadata.identifiers`, matched by `id_type`. `journal_id` is `JournalMetadata.journal_id.lower()` — a generic string operation (ADR-028's documented convention), never a per-journal lookup table; this transformer never calls `ConfigRegistry.get_journal_config()` (which would raise `ConfigurationError`, a *batch-level* failure, for any of the 3 real samples today, since `config/journals/` remains intentionally empty per Milestone 1's scope) — it only computes the lookup *key*, which is all `ArticleIdentity.journal_id: str` is documented to be.
- **Journal**: every `JournalMeta` field is copied verbatim from `JournalMetadata` — no config lookup at all (none of its fields are config-owned business values; see Architecture Compliance Report §1 for why this satisfies "no hard-coded values" by construction rather than vacuously).
- **Contributors**: `Affiliation.model_key` is assigned sequentially (1, 2, 3...) in document order, building an `element_id -> model_key` map; each author's `affiliation_ref_ids` are resolved through that map — an unresolvable reference is logged and omitted (never included dangling, which would otherwise trip `model.validation`'s own `DANGLING_AFFILIATION_KEY` check). Only `ContributorMetadata.authors` is mapped (editors/other_contributors are out of ICAM scope — see `ContribType`'s own single-member design, Milestone 5A). `Affiliation.institution` falls back to `AffiliationRecord.raw_text` when the source has no separately-tagged `<institution>` (true for all 3 real samples — see §5).
- **Round Resolution**: reads `<article-version>` directly from the `ParsedDocument`, never from `ExtractionBundle` (which never captured this — out of Milestone 4's 7 named areas). Sequence number parsed from `vocab-identifier`'s documented `"snapshots/<N>_..."` format; ambiguous/missing data raises rather than guesses (ADR-013).
- **Custom-Meta Classification**: driven primarily by the `<custom-meta>` element's own `specific-use` attribute (`"form-files"` → file entry, `"question"` → scorecard field, `"reviewer-decline"` → decline reason) — discovered, not assumed, by inspecting real sample data; `meta-name` exact match handles `"Decision Draft"` (no `specific-use` in the observed samples). Everything else falls through to `form_answers`, grouped by key (BR-071).
- **File Resolution**: `FileEntry.round_label` (a custom-meta hint) is tried first but the *authoritative* `ResolvedFile.round_label` is whichever staged subdirectory the file was actually found under — real evidence showed the hint is sometimes a per-file job UUID, not a round at all. Filename matching tries 4 tolerance tiers (exact → stem → prefix → whitespace/underscore-normalized) before raising `FileReferenceMissingError` — see §5 for the real mismatches each tier resolves.
- **Body Fragment**: the parsed `<body>` subtree is serialized back to XML text (tag/attribute/text/tail, escaped) — not literally byte-identical to the source (which Milestone 3 does not retain past parsing), a documented, flagged limitation for Milestone 6 to confirm against.

---

## 5. Golden Baseline Results

All 3 real reference packages run through the complete pipeline (parse → extract → transform) successfully, with **zero structural-integrity issues** (`model.validation.validate_structural_integrity(model) == ()` for every sample):

| Article | Contributors | Affiliations | Rounds | Resolved Files | Custom-meta entries classified |
|---|---|---|---|---|---|
| CS-2025-6808 | 7 | 5 | 1 (Original, seq 20) | 21 | 21 file / 4 scorecards / 2 decisions / 1 decline / 50 form-answers (of 395 raw) |
| CS-2025-8493_C | 2 | 2 | 3 (Original ×3, seq 9/13/17) | 8 | 8 file / 2 scorecards / 2 decisions / 3 declines / 33 form-answers (of 348 raw) |
| cs-2025-8827 | 6 | 5 | 1 (Original, seq 19) | 17 | 17 file / 3 scorecards / 2 decisions / 3 declines / 19 form-answers (of 103 raw) |

**Notable real-data findings, all evidence-driven, none guessed**:

1. **CS-2025-8493_C resolves to 3 rounds, all labeled "Original"** — 3 distinct `<article-version>` elements with distinct `vocab-identifier` sequence numbers, all sharing the label "Original". This reflects 3 processing/re-tagging snapshots within (apparently) the same editorial round, not 3 distinct editorial rounds — flagged as an open question for business confirmation before a later milestone treats `RoundIndex` as "the list of editorial rounds" without qualification (see §9).
2. **~65% of one real sample's custom-meta entries carry no `meta-name` and no free text** — Kriyadocs' internal audit-trail markers (`specific-use` = `history`/`lqc`/`query`/`summary`). These are intentionally not force-mapped into `WorkflowLog` (no text to synthesize from) nor into `form_answers` (no name to key by) — the raw data remains fully available, unmodified, in Milestone 4's own `ExtractionBundle.custom.entries`.
3. **File-matching required 2 additional tolerance tiers beyond BR-016/017's documented leading-slash variance**: one real declared filename omits its extension and a `" (1)"` disambiguating suffix the actual upload carries; another uses underscores where the actual upload uses spaces. Both real, both resolved generically (never hard-coded per-filename).
4. **Institution/country are unstructured in all 3 real samples** — `AffiliationRecord.institution`/`.country` are always `None`; `Contributor Transformation` falls back to `raw_text`, Milestone 4's own documented fallback field for exactly this case.

---

## 6. Test Summary

| Test file | Test functions | Covers |
|---|---|---|
| `test_round_resolver.py` | 8 | single/multiple `<article-version>`, ordering, `is_latest`, malformed/missing vocab-identifier, missing type attribute, duplicate sequence numbers, error context |
| `test_custom_meta_classifier.py` | 13 | file-entry classification, size parsing, multi-entry preservation, scorecard grouping (same reviewer/different rounds), decision-draft/decline-reason classification, form-answer fallback + multi-value grouping, unclassifiable-entry non-mapping, logging |
| `test_file_resolver.py` | 16 | exact/stem/prefix/normalized matching (4 tiers), media-type resolution + fallback, round-hint-is-actually-a-uuid correction, missing-file/missing-root errors, unreferenced-file warning, completion logging |
| `test_identity_transformer.py` | 5 | full mapping, journal_id lower-casing, missing-identifier empty-string defaults, no-DOI-generation confirmation, other-id-type exclusion |
| `test_journal_transformer.py` | 4 | verbatim mapping, missing-ISSN-type handling, empty-string defaults, `None`-typed abbrev-title filtering |
| `test_contributor_transformer.py` | 9 | model-internal key assignment, authors-only mapping, ref-id resolution, dangling-reference omission+logging, institution fallback, corresponding-email ordering, first-email selection, empty-input handling |
| `test_workflow_transformer.py` | 2 | pass-through identity, empty-store handling |
| `test_body_fragment_builder.py` | 6 | text, attributes, mixed-content/tail, escaping, self-closing empty elements, missing-body handling |
| `test_coordinator.py` | 10 | full happy path, history-date/count conversion (incl. unparseable/out-of-range), empty round index, error propagation (×2), independent repeated calls, start/completion logging, performance event |
| `test_loader.py` (extension) | 1 | `load_media_type_config` |
| Modified extractor tests | 12 | `journal_id`, `abbrev_titles`, `attributes`, `display_channel_subject`/`heading_subjects`, copyright/keywords/funding/counts extraction |
| `tests/golden/test_metadata_to_icam_golden.py` | 3 (parametrized) | full pipeline, structural soundness, and JSON-snapshot equality against all 3 real reference packages |
| **Total new/modified** | **89** | |

Full default suite (`testpaths`, all 5 milestones combined): **488 passing tests**. Golden suite (outside `testpaths`, run separately per its own established convention): **3 passing tests**, deterministic across repeated runs. `ruff check`, `ruff format --check`, and `mypy --strict` all clean on 188 source files.

---

## 7. Coverage Report

```
Name                                                           Stmts   Miss Branch BrPart  Cover
------------------------------------------------------------------------------------------------
src/meca_engine/extraction/round_resolver.py                      34      0     14      0   100%
src/meca_engine/extraction/custom_meta_classifier.py               75      0     26      0   100%
src/meca_engine/extraction/file_resolver.py                        67      0     38      2    98%
src/meca_engine/transform/coordinator.py                           59      0     10      0   100%
src/meca_engine/transform/identity_transformer.py                  15      0      6      0   100%
src/meca_engine/transform/journal_transformer.py                   13      0      6      1    95%
src/meca_engine/transform/contributor_transformer.py               27      0     14      2    95%
src/meca_engine/transform/workflow_transformer.py                   4      0      0      0   100%
src/meca_engine/transform/body_fragment_builder.py                 20      0      4      0   100%
------------------------------------------------------------------------------------------------
Milestone 5B module subtotal                                      314      0    118      5    99%
------------------------------------------------------------------------------------------------
TOTAL (whole src/, incl. Milestones 1-5A + untouched stubs)      2546     17    394      5    99%
```

**Target ("at least 95% coverage") is met: every Milestone 5B module is at 95%+ coverage** (the handful of sub-100% modules are partial-branch edge cases in matching-tier fallthrough loops, not uncovered lines). The remaining 17 uncovered lines project-wide are entirely in still-unimplemented future-milestone stub packages.

---

## 8. Architecture Compliance Report

See the companion document: **`MILESTONE_5B_ARCHITECTURE_COMPLIANCE_REPORT.md`** in this same directory.

---

## 9. Deferred Work for Milestone 6

Per the current task's explicit exclusion list, all deferred:

- **DOI generation** (BR-058's formula) — `ArticleIdentity.doi_article_id_value` remains the verbatim source field; `generators.article_xml.doi_builder` is Milestone 7's job.
- **Business-rule transformations that modify values** — every field this milestone populates is copied, classified, or structurally resolved, never reinterpreted (e.g. `CustomMetadata.entries` remains fully unfiltered in `form_answers`; the deny-list pruning BR-066–071 describes for *article.xml specifically* is a generation-time concern, not an ICAM-population one).
- **XML generation, Package Builder, Validation Engine** — untouched stub packages, per scope.
- **`WorkflowLog`/`CorrespondenceEvent` population from genuine free-text correspondence** — no real sample exhibited a custom-meta entry with both an actor/role/timestamp *and* non-empty text; `workflow_transformer.build_workflow_log` is a documented, honest pass-through today, not a placeholder pretending otherwise. If a future sample or business input surfaces such data, this is the module to extend.
- **Reconciling `RoundIndex`'s "processing snapshot" vs. "editorial round" semantics** — CS-2025-8493_C's 3-same-label-different-sequence result (see §5) is flagged, not resolved; needs business confirmation before any downstream consumer treats round count as "number of editorial rounds" without qualification.
- **Kriyadocs' internal production-pipeline telemetry** (`WorkflowMetadata.events`, Milestone 4's `<stage>`-based extraction) — confirmed by real-data inspection to be operational job tracking, not correspondence; has no ICAM slot (11_LLD_02... §3.2) and is not mapped by any Milestone 5B transformer.

**Explicit dependency check before Milestone 6 begins**: `ArticleModel` instances produced by `TransformationCoordinator` are exactly the frozen, structurally-sound input `generators.raw_xml.RawXmlGenerator` (11_LLD_02... §4.7) is designed to consume. Nothing left open in this milestone blocks that work — the one explicitly-flagged, non-blocking open item (`BodyFragment`'s reconstructed-not-byte-identical fidelity, §4) is exactly what the requested Architecture Review checkpoint (see the companion compliance report) should confirm before `raw_xml` generation relies on exact byte equality with the 3 real hand-built samples.
