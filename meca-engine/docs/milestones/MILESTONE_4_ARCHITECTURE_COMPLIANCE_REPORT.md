# Milestone 4 Architecture Compliance Report — Metadata Extraction Layer

Companion to `MILESTONE_4_IMPLEMENTATION_REPORT.md`. Checks Milestone 4's
implementation against the Business Rule Book, the ADRs, the HLD, and the
LLD, and verifies no architectural boundary was crossed. Every claim below
is either a direct code citation, a `grep`-based structural check, or a
result observed by actually running the pipeline — not an assertion.

---

## 1. Business Rule Book Compliance

| Rule | Requirement | Milestone 4 Implementation | Status |
|---|---|---|---|
| BR-007 | Custom-meta is the audit-trail-of-record; must be parseable | `extract_custom_metadata` reads every `custom-meta` entry, unfiltered and unclassified — verified against real data: `golden_baseline/CS-2025-6808/02_extracted_metadata.json` contains 395 extracted entries from the real sample package. Deciding which entries are business-significant (the deny-list logic) is explicitly deferred to Milestone 5's classifier, per this module's docstring. | **Precondition satisfied; classification correctly deferred** |
| BR-010 | `vocab-identifier` snapshot number is the round-ordering key | Not applicable to Milestone 4 — `WorkflowMetadata`/`extract_workflow_metadata` flatten workflow/log elements generically; no code in this milestone reads or interprets `vocab-identifier` or performs round-ordering. | **Correctly deferred, not violated** |
| BR-011/BR-014 | Custom-meta file-manifest entries are the authoritative file list; structural href/src scanning is not trusted for business purposes | `extract_asset_metadata` reuses Milestone 3's `discover_file_references`, scoped per JATS structural tag (`fig`, `table-wrap`, etc.) — explicitly documented (module docstring) as a schema-level fact, not the BR-011/BR-014 business file list. `AssetMetadata` and `CustomMetadata` are two separate, un-merged models; no code path in this milestone presents asset-derived file references as the authoritative manifest. | **Correctly scoped, not violated** |
| (Data fidelity principle, implicit across A-J) | Source values must not be silently transformed or reinterpreted | Every extractor's docstring and every model's field documentation states values are preserved verbatim (e.g. `contrib_type`, `asset_tag`, `id_type` stored exactly as source-written; sorting authors/editors relies only on the literal `contrib_type` string, never reinterpreted). No `.lower()`/`.strip()`/renaming is applied to any extracted business value anywhere in the seven extractors (verified by inspection — the only `.strip()` calls in the `extraction` package are inside Milestone 3's already-approved `navigation.as_int/as_float/as_bool` numeric/boolean coercion helpers, untouched this milestone). | **Fully compliant** |

**No Business Rule Book rule was violated.** Every rule with any overlap with Milestone 4's scope is either a satisfied precondition for a later milestone's classification/interpretation step, or correctly, documentedly deferred.

---

## 2. ADR Compliance

| ADR | Decision | Milestone 4 Implementation | Status |
|---|---|---|---|
| (General architecture principle, 10_LLD_01 §2.1: extraction responsibility is layered, not monolithic) | Metadata extraction should not be one monolithic parser | Implemented as **seven independent, pure extractor modules** rather than a single `kriyadocs_parser.py` — directly resolving the open design question flagged at the end of Milestone 3's report ("whether `extraction.kriyadocs_parser` should be a genuinely separate module... a design detail for Milestone 4 to settle"). Each extractor has zero dependency on any sibling extractor's internals (the one exception — `journal_metadata_extractor` calling `extract_article_metadata` once for `doi_related_ids` — is a documented, read-only convenience call, not a coupling of internal state). | **Compliant; resolves Milestone 3's open question** |
| ADR-031 (defect-replication policy) | Never replicate a hand-built-sample defect as if it were a business rule | Not directly applicable — no XML generation occurs in Milestone 4, so there is no generated output to compare against the 3 real sample packages. The Golden Baseline Repository's `02_extracted_metadata.json` snapshots are themselves the reference for later milestones to compare against, not a defect-prone hand-built sample. | N/A |
| (Diagnostics-not-exceptions principle, established Milestone 3) | Non-fatal observations are diagnostics, not raised exceptions | Every extractor follows this exactly: a missing title, a duplicate id, an empty reference attribute — all become `ParseDiagnostic` entries via the additively-extended `DiagnosticCategory` enum (`DUPLICATE_ID`, `MISSING_REQUIRED_VALUE`), never a raised exception. Zero new exception classes were introduced this milestone (verified, §5). | **Fully compliant** |

**No ADR was violated.** Milestone 4 additionally resolves the one open architectural question Milestone 3 explicitly left for it.

---

## 3. HLD Compliance (System Module Breakdown + Data Flow Document)

- **Metadata Extractor module** (`05_SYSTEM_MODULE_BREAKDOWN.md` §4): "Parses the staged Kriyadocs XML into a single, complete, typed internal article model." Milestone 4 still does not build that "complete, typed internal article model" (the ICAM) — `ExtractionBundle` is a distinct, non-ICAM intermediate grouping, exactly as the current task's scope required ("does NOT normalize data into the ICAM"). The HLD's module responsibility is honored incrementally: this milestone builds the extraction half; Milestone 5 builds the ICAM-construction half on top of it.
- **Data Flow Document, Stage 2** (`06_DATA_FLOW_DOCUMENT.md`, "Metadata Loading"): this milestone implements the actual field-level extraction this stage describes, using Milestone 3's parsing primitive as its only input. The Data Flow Document's stage-2 failure paths remain Milestone 3's concern (malformed XML); this milestone's failure mode is diagnostics-only, by design — a missing or malformed metadata field is never a pipeline-halting condition at this layer.

**No HLD module's stated responsibility was contradicted, duplicated elsewhere, or silently dropped** — Milestone 4 is additive groundwork underneath the Metadata Extractor module's eventual full (ICAM-producing) implementation.

---

## 4. LLD Compliance

- **Package structure** (`10_LLD_01_STRUCTURE_AND_PACKAGES.md` §2.1): all new modules were added inside the existing `extraction/` package at the LLD-designated path — no new top-level package was created. As with Milestone 3, the LLD's own illustrative sketch (`kriyadocs_parser.py`, `custom_meta_classifier.py`) is more business-specific than what this milestone needed; the established precedent of implementing at a different, justified granularity (documented per-module) continues.
- **ICAM boundary** (`11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md` §3): completely untouched. Verified: `grep -rn "ArticleModel\|ArticleModelBuilder" src/meca_engine/extraction` returns no matches. `metadata_models.py`'s module docstring explicitly states these types are "a distinct, intermediate layer between the generic Parsed Object Model... and the eventual Internal Canonical Article Model (ICAM, Milestone 5+)."
- **Exception Framework** (`12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md` §7): zero new exception classes introduced. Verified: `grep -c "^class.*Error"` on both exception modules is unchanged from Milestone 3's count (22 article-level + 7 batch-level = 29). Every extraction gap is a `ParseDiagnostic`, never a new exception.
- **Logging** (`12_LLD_03...` §6): logging is concentrated in the one orchestrator (`metadata_extraction.extract_all_metadata`), injected via a `StructuredLogger` parameter — no individual extractor holds a logger reference. Verified: `grep -rn "print(\|logging.getLogger" src/meca_engine/extraction` returns no matches.
- **Coding Standards** (`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §13): full type hints throughout (verified: `mypy --strict` clean on both `src/` and `tests/`, 154 source files), Google-style docstrings on every public class/function, `ruff check`/`ruff format --check` clean, one test file per source module mirroring `src/` exactly.

**No LLD-specified class responsibility, dependency rule, or module boundary was altered.**

---

## 5. Verified Structural & Behavioral Checks

Run directly against the final Milestone 4 codebase:

```
$ grep -rnE "^(from|import) meca_engine\.(model|transform|generators|validation|packaging|output|registry|retry|recovery|reporting|monitoring|orchestrator|input|checkpoint)\b" \
    src/meca_engine/extraction --include="*.py"
NONE FOUND — extraction/ still imports nothing from any other package (depends only on
meca_engine.exceptions and meca_engine.logging_, both foundation-layer).

$ grep -rlE "^(from|import) meca_engine\.extraction" src/meca_engine --include="*.py" | grep -v "^src/meca_engine/extraction/"
NONE FOUND — no other package imports extraction/ yet (correct: not wired into container.py this
milestone, since there is no ICAM-building consumer yet — that wiring is Milestone 5's job).

$ grep -rn "print(\|logging.getLogger" src/meca_engine/extraction
NONE FOUND — every log emission goes through meca_engine.logging_, and only in metadata_extraction.py.

$ grep -c "^class.*Error" src/meca_engine/exceptions/article_errors.py src/meca_engine/exceptions/batch_errors.py
article_errors.py: 22   batch_errors.py: 7   (both unchanged from Milestone 3 — zero new exceptions)

$ grep -rn "ArticleModel\|ArticleModelBuilder" src/meca_engine/extraction
NONE FOUND — ICAM boundary untouched.
```

**Real-data verification** (running the actual pipeline against all 3 real sample packages, never a synthetic fixture, per the Golden Baseline Repository seeding in `golden_baseline/`):

```
CS-2025-6808:   parsed diagnostics=32   metadata diagnostics=50   authors=7   assets=17 (14 with file refs)   custom-meta entries=395
CS-2025-8493_C: parsed diagnostics=15   metadata diagnostics=11   authors=2
cs-2025-8827:   parsed diagnostics=94   metadata diagnostics=119  authors=6
```

All 3 real packages parsed and extracted without a single fatal error — every diagnostic is a non-fatal `ParseDiagnostic` observation (missing fields, duplicate ids, malformed references), exactly the "identify and extract, never validate business semantics" behavior this milestone was scoped to.

---

## 6. Test Evidence Cross-Reference

| Compliance claim | Verifying test(s) |
|---|---|
| No normalization/reclassification of `contrib_type` when sorting authors/editors | `test_sorts_contributors_by_contrib_type` |
| Corresponding-author detection is structural only (attribute or xref), not a business judgment | `test_detects_corresponding_via_attribute`, `test_detects_corresponding_via_xref` |
| Custom-meta extraction is unfiltered (no deny-list applied) | `test_includes_every_entry_unfiltered` |
| Asset recognition is a JATS structural fact, configurable, not hard-coded | `test_recognizes_every_default_asset_tag`, `test_custom_asset_tag_names` |
| Cross-reference extraction preserves relationships only (no target validation folded in) | `test_extracts_reference_with_ref_type_and_target_ids` |
| New diagnostics are additive to Milestone 3's existing mechanism, not a parallel system | `test_diagnostic_category_values` (updated in place, not replaced) |
| `journal_metadata_extractor`'s reuse of `extract_article_metadata` is a convenience, not double extraction | `test_doi_related_ids_reuses_article_metadata_identifiers` |
| Logging concentrated in the orchestrator only | `test_logs_start_and_completion_for_every_extractor`, `test_emits_a_performance_event_per_extractor` |
| Full-bundle structural fidelity protected end-to-end | `test_metadata_sample_matches_golden_snapshot` |
| Real-sample-package pipeline runs end-to-end without fatal error | Golden Baseline Repository seeding run (§5 above; not a pytest test, a direct pipeline execution against `Input/*.zip`, documented in `golden_baseline/README.md`) |

---

## 7. Conclusion

Milestone 4 implements the Metadata Extraction Layer entirely within the
architectural boundaries established by the Business Rule Book, the ADRs,
the HLD, and the LLD. It introduces zero new exception categories, touches
no ICAM concept, imports from no not-yet-implemented package, and resolves
the one open design question Milestone 3 explicitly deferred to it (seven
independent extractors, not one monolithic parser). Every rule/decision/
module whose scope overlaps this milestone is either fully implemented or
explicitly, documentedly deferred with a stated reason. The Golden
Baseline Repository recommendation was actioned this milestone and
confirms, against real data, that the implementation extracts non-trivial
business content (up to 395 custom-meta entries, 7 authors, 17 assets in
a single real package) without a single fatal error.

**No architectural boundary was violated. Milestone 4 is ready for review.**
