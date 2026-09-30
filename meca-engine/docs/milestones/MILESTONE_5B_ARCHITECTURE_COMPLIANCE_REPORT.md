# Milestone 5B Architecture Compliance Report — Metadata → ICAM Transformation

Companion to `MILESTONE_5B_IMPLEMENTATION_REPORT.md`. Checks Milestone 5B's
implementation against the Business Rule Book, the ADRs, the HLD, and the
LLD, and verifies no architectural boundary was crossed. Every claim below
is either a direct code citation, a `grep`-based structural check, or a
result observed by running the pipeline against real reference-package
data — not an assertion.

---

## 1. Business Rule Book Compliance

| Rule | Requirement | Milestone 5B Implementation | Status |
|---|---|---|---|
| BR-003 | The exact input-folder string is the article's identity | `identity_transformer.build_identity` takes `article_id` as a caller-supplied parameter, never derived from XML content. | **Fully compliant** |
| BR-010 | `vocab-identifier` snapshot number is the round-ordering key | `round_resolver.resolve_rounds` reads `<article-version>`/`vocab-identifier` directly and parses the documented `"snapshots/<N>_..."` format; never guesses on a malformed/missing value (raises `RoundResolutionError` instead, per ADR-013). | **Fully implemented** |
| BR-011/BR-014 | Custom-meta file-manifest entries are the authoritative file list | `file_resolver.resolve_files` takes `CustomMetaStore.file_entries` (custom-meta-derived) as its sole file-list input — never scans the staged directory for "extra" files as if they were the manifest (ADR-016's separate, logged-only "unreferenced physical file" check is additive, not a competing file-list source). | **Fully compliant** |
| BR-013 | Original filenames preserved exactly, byte-identical | `ResolvedFile`/`FileEntry.original_filename` are never touched by any matching-tolerance logic in `file_resolver` — the 4-tier matching (§4 of the Implementation Report) only decides *which physical file's bytes* to check/hash, never rewrites the declared name itself. | **Fully compliant** |
| BR-016/BR-017 | File-path leading-slash and staging-path-style variance must be tolerated | Confirmed on real data (3 tolerance tiers beyond exact match, all real-sample-evidenced) — see Implementation Report §5. | **Fully implemented, extended with 2 additional real-evidenced tiers** |
| BR-058 | DOI is generated, never copied | Explicitly **not implemented** — `ArticleIdentity.doi_article_id_value` is the verbatim source field only; no formula logic exists anywhere in Milestone 5B. | **Correctly out of scope** |
| BR-066–071 | article.xml custom-meta pruning is a deny-list | Explicitly **not implemented** — `custom_meta_classifier.classify` preserves every entry (in `form_answers` if nothing more specific applies); no pruning logic of any kind exists in this milestone. | **Correctly deferred to generation-time (Milestone 7)** |
| BR-075 | Any `QN_` key is a reviewer-scorecard field, prefix-matched | `custom_meta_classifier` groups by the `specific-use="question"` signal (confirmed on real data to co-occur with every `QN_*` key observed) rather than a hard-coded prefix string match — a stronger, structural signal that happens to be equivalent on all evidence seen; documented as the chosen mechanism in the module's own docstring. | **Fully compliant** |

**No Business Rule Book rule was violated.** Every rule with any overlap with this milestone's scope is either fully implemented (verified against real data) or explicitly, documentedly out of scope pending a later milestone.

---

## 2. ADR Compliance

| ADR | Decision | Milestone 5B Implementation | Status |
|---|---|---|---|
| ADR-008/009 | Media-type mapping is config-driven; unmapped extensions get a soft `application/octet-stream` fallback with a warning, batch continues | `config/media-types.yaml` (newly populated — operational, not business-value, config; see §3) + `MediaTypeConfig.unmapped_extension_policy`/`.unmapped_extension_default`, read via the new `ConfigLoader.load_media_type_config()`. `file_resolver._resolve_media_type` implements exactly this fallback. | **Fully compliant** |
| ADR-013 | Multi-round generalization beyond 2 rounds must work without hard-coding "2 rounds" | `round_resolver.resolve_rounds` is round-count-agnostic by construction (a loop over however many `<article-version>` elements exist) — confirmed against real data with a genuine 3-round-signal result (CS-2025-8493_C). | **Fully compliant, confirmed against real (not just synthetic) evidence** |
| ADR-014 | Round labels are generic, opaque strings | Every `round_label` field remains a plain `str`, sourced either from `article-version-type` (verbatim) or from a staged directory name (verbatim) — no enum, no fixed vocabulary, no interpretation of what a label "means" anywhere in this milestone. | **Fully compliant** |
| ADR-016 | Unreferenced physical files: log, don't silently drop | `file_resolver._log_unreferenced_physical_files` emits one WARNING per unmatched physical file after all `file_entries` are resolved — confirmed exercised against real data (52 warnings on CS-2025-6808's real staged folder, expected: many round-duplicate manuscript files aren't independently referenced). | **Fully compliant** |
| ADR-028 | Multi-tenancy: journal/publisher identifiers are config lookup keys, not hard-coded | `ArticleIdentity.journal_id` is computed generically (`.lower()` on the raw source value) — no per-journal table anywhere in `identity_transformer`. The full `JournalConfig`/`PublisherConfig` objects (DOI prefix, acronym, etc.) are deliberately *not* fetched by this milestone — see §1 below for why that is correct, not a gap. | **Compliant; scope correctly bounded** |
| (11_LLD_02... §4.6, TransformationCoordinator's own error-handling spec) | Propagate typed errors unchanged, never re-wrap | Verified directly: `TransformationCoordinator.build_model` contains no `except` clause of any kind — `RoundResolutionError`/`FileReferenceMissingError`/`ModelBuildError` all propagate straight through, confirmed by 3 dedicated tests asserting the exact exception type. | **Fully compliant, empirically verified** |

**No ADR was violated.**

---

## 3. HLD Compliance (System Module Breakdown + Data Flow Document)

- **Transformation Engine module** (`05_SYSTEM_MODULE_BREAKDOWN.md` / `11_LLD_02...` §4.6): "builds the finalized ICAM instance ready for generators." `TransformationCoordinator.build_model` does exactly this and nothing more — it does not generate any output document, does not validate business rules, does not package.
- **Data Flow Document, Stage 4** (Transformation): this milestone's coordinator is the literal implementation of this stage. Its documented failure paths (propagate the originating stage's typed error) are exactly what was implemented and tested.
- **File Resolver / Metadata Extractor modules** (`05_SYSTEM_MODULE_BREAKDOWN.md` §4): "resolves custom-meta file-entries to staged physical files." `file_resolver.resolve_files` implements this exactly, including the module's anticipated round-ordering/file-manifest authority split from `custom_meta_classifier`.

**No HLD module's stated responsibility was contradicted, duplicated elsewhere, or silently dropped.**

---

## 4. LLD Compliance

- **Package placement** (`10_LLD_01_STRUCTURE_AND_PACKAGES.md` §2.1): `round_resolver.py`, `custom_meta_classifier.py`, `file_resolver.py` placed in `extraction/`, exactly matching the LLD's own package sketch (`extraction/kriyadocs_parser.py`, `custom_meta_classifier.py`, `file_resolver.py`, `round_resolver.py`). `coordinator.py` and the 5 new transformer modules placed in `transform/`, matching the LLD's `transform/coordinator.py` designation — the LLD's own sketch shows only `coordinator.py` inside `transform/`, so the 5 additional transformer modules are a finer-grained decomposition within the *same designated package*, not a placement violation; each is independently justified in its own docstring (matching the established, Milestone-4-set precedent of "each service performs one responsibility only").
- **`FileResolver` signature** (`11_LLD_02...` §4.5): `resolve(file_entries, staged_root: str, media_type_config: MediaTypeConfig) -> ResolvedFileList` — implemented with this exact parameter shape (plus optional `article_id`/`logger` for error-context/observability, additive, non-breaking). Verified: `file_resolver.py` contains no import of `meca_engine.input` — `staged_root` stays a plain string throughout, exactly avoiding the cross-layer dependency the LLD's own signature choice (as opposed to `§4.6`'s `StagedArticle`-typed sketch) implies.
- **Foundation-layer / layering rules** (`10_LLD_01...` §2.3): Verified directly (§5 below) — `transform/` imports only `extraction` and `model` (plus foundation-layer `exceptions`/`logging_`/`config`); `extraction/`'s 3 new modules import only `model` (plus the same foundation-layer set) — neither imports `input`, `generators`, `validation`, `packaging`, `output`, `registry`, `retry`, `recovery`, `reporting`, `monitoring`, `orchestrator`, or `cli`.
- **No consumer yet** (correct per the LLD's own stage ordering): `grep` finds zero imports of `meca_engine.transform` from any other package — expected, since Milestone 6's `generators.raw_xml.RawXmlGenerator` (the first real consumer) does not exist yet.
- **Exception Framework** (`12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md` §7): zero new exception classes introduced. `RoundResolutionError`, `FileReferenceMissingError`, `ModelBuildError` (all already present since Milestone 1's upfront exception framework) are reused unmodified — verified: `grep -c "^class.*Error"` on both exception modules is unchanged from Milestone 5A (22 article-level + 7 batch-level = 29).
- **Logging** (`12_LLD_03...` §6): every new transformation service accepts an optional injected `StructuredLogger`; `TransformationCoordinator` logs start/completion and times the whole transformation with `PerformanceTimer` (a `contextlib.nullcontext()` substitute when no logger is supplied, so logging remains strictly additive/optional, never required for correctness). Verified: `grep -rn "print(\|logging.getLogger"` across every new/modified module in `transform/` and the 3 new `extraction/` modules returns no matches.
- **Coding Standards** (`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §13): full type hints throughout (verified: `mypy --strict` clean on 188 source files), Google-style docstrings on every public class/function, `ruff check`/`ruff format --check` clean, one test file per source module mirroring `src/` exactly.

**No LLD-specified class responsibility, dependency rule, or module boundary was altered.**

---

## 5. Verified Structural & Behavioral Checks

Run directly against the final Milestone 5B codebase:

```
$ grep -rnE "^(from|import) meca_engine\.(generators|validation|packaging|output|registry|retry|recovery|reporting|monitoring|orchestrator|checkpoint|input|cli)\b" \
    src/meca_engine/transform --include="*.py"
NONE FOUND — transform/ imports nothing from any package above it in the layering.

$ grep -rnE "^(from|import) meca_engine\.(transform|generators|validation|packaging|output|registry|retry|recovery|reporting|monitoring|orchestrator|checkpoint|input|cli)\b" \
    src/meca_engine/extraction --include="*.py"
NONE FOUND — extraction/'s 3 new modules stay within the LLD's model-and-below dependency allowance.

$ grep -rlE "^(from|import) meca_engine\.transform\b" src/meca_engine --include="*.py" | grep -v "^src/meca_engine/transform/"
NONE FOUND — no other package imports transform/ yet (correct: no Milestone 6 consumer exists).

$ grep -rn "print(\|logging.getLogger" src/meca_engine/transform src/meca_engine/extraction/{round_resolver,file_resolver,custom_meta_classifier}.py
NONE FOUND.

$ grep -c "^class.*Error" src/meca_engine/exceptions/article_errors.py src/meca_engine/exceptions/batch_errors.py
article_errors.py: 22   batch_errors.py: 7   (both unchanged from Milestone 5A — zero new exceptions)
```

**Real-data pipeline verification** (running the actual coordinator against all 3 real sample packages, never a synthetic fixture, per `tests/golden/`):

```
CS-2025-6808:   0 structural issues   7 contributors   5 affiliations   1 round     21 resolved files
CS-2025-8493_C: 0 structural issues   2 contributors   2 affiliations   3 rounds     8 resolved files
cs-2025-8827:   0 structural issues   6 contributors   5 affiliations   1 round    17 resolved files
```

Every real package produced a **structurally sound** `ArticleModel` (`model.validation.validate_structural_integrity` returns `()` for all 3) — no dangling affiliation reference, no duplicate model-internal key, no round-consistency violation, on real data, not just hand-built fixtures.

---

## 6. Test Evidence Cross-Reference

| Compliance claim | Verifying test(s) |
|---|---|
| No DOI is ever generated, only the source field copied | `test_does_not_generate_a_doi_only_copies_source_field` |
| `journal_id` computed generically, no per-journal table | `test_journal_id_is_lower_cased_per_adr_028` |
| Round resolution never guesses a sequence number or label | `test_missing_vocab_identifier_raises`, `test_malformed_vocab_identifier_raises`, `test_missing_article_version_type_raises`, `test_duplicate_sequence_number_raises` |
| Round resolution is round-count-agnostic (ADR-013) | `test_multiple_article_versions_ordered_by_sequence_and_latest_flagged` (2 rounds, synthetic) + `tests/golden/` (3-round real-data confirmation, CS-2025-8493_C) |
| Custom-meta entries are never dropped without classification | `test_unclassified_named_entries_fall_through_to_form_answers`, `test_repeated_key_form_answers_are_grouped_multi_valued` |
| Unclassifiable no-name/no-text entries are honestly not mapped (not force-fit) | `test_entries_with_no_name_and_no_specific_classification_are_not_in_form_answers` |
| File matching tolerates real-evidenced name variance without touching the output name | `test_stem_match_when_declared_name_lacks_extension`, `test_prefix_match_when_declared_name_omits_suffix`, `test_normalized_match_when_underscores_replace_spaces`, `test_normalized_match_when_declared_name_has_stray_whitespace` |
| Round label is physically verified, not trusted from a possibly-wrong hint | `test_falls_back_to_other_round_when_declared_round_hint_is_wrong` |
| Unreferenced physical files are logged, never silently dropped (ADR-016) | `test_logs_warning_per_unreferenced_physical_file` |
| Dangling affiliation references are omitted (never included dangling) | `test_dangling_affiliation_reference_is_omitted_and_logged` |
| Coordinator propagates every typed error unchanged | `test_raises_round_resolution_error_unchanged`, `test_raises_file_reference_missing_error_unchanged` |
| Full real-pipeline structural soundness, end to end | `tests/golden/test_metadata_to_icam_golden.py::test_real_sample_produces_a_structurally_sound_icam` (×3, parametrized) |

---

## 7. Conclusion

Milestone 5B implements the Metadata → ICAM Transformation Layer entirely
within the architectural boundaries established by the Business Rule
Book, the ADRs, the HLD, and the LLD. It introduces zero new exception
categories, respects every layering rule (`transform` depends only on
`extraction`/`model`/foundation; `extraction`'s 3 new modules depend only
on `model`/foundation), and every module is placed exactly where the LLD
designates. No DOI is generated, no value is transformed by business
rule, and no XML/package/output is produced. All 3 real reference
packages were run through the complete pipeline and produced a
structurally sound ICAM with zero validation issues — not merely
asserted, verified by a dedicated, parametrized golden-regression test
suite. Several genuine real-data findings (multi-tier filename variance,
audit-trail entries with no free text, a 3-processing-snapshot round
result) were discovered, resolved with generic/structural — never
guessed or hard-coded — logic, and transparently documented rather than
silently smoothed over.

**No architectural boundary was violated. Milestone 5B is ready for
review — including the requested Architecture Review checkpoint before
XML generation begins.**
