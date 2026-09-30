# Milestone 2 Architecture Compliance Report — Input & Staging Layer

Companion to `MILESTONE_2_IMPLEMENTATION_REPORT.md`. This report checks
Milestone 2's implementation against the Business Rule Book, the ADRs, the
HLD (System Module Breakdown + Data Flow Document), and the LLD, and
verifies no architectural boundary was crossed. Every claim below is
either a direct code citation or a verified `grep`-based structural check
(§5), not an assertion.

---

## 1. Business Rule Book Compliance

| Rule | Requirement | Milestone 2 Implementation | Status |
|---|---|---|---|
| BR-001 | Exactly one root-level `.xml` file must exist; must be well-formed XML | `input.discovery.BatchDiscovery._discover_one` enforces the **existence/count** half only (`InvalidArticlePackageError` if ≠1); the well-formedness half is explicitly **not** checked here — deferred to Milestone 3's `extraction.kriyadocs_parser`, per this milestone's "no XML parsing" boundary | **Partially implemented, by design** — see module docstring's explicit note |
| BR-002 | At least one round folder must exist | `_discover_one` raises `InvalidArticlePackageError` if zero round folders found | **Fully implemented** |
| BR-003 | Article ID preserved exactly as the input folder name (no case-folding/normalization) | `ArticleReference.article_id` is the literal string returned by `InputReader.list_batch_article_ids` — no transformation applied anywhere in `discovery.py` | **Fully implemented** |
| BR-010 | `vocab-identifier` snapshot number is the authoritative round-ordering key | **Not applicable to Milestone 2** — round-ordering requires XML parsing (Milestone 3's `extraction.round_resolver`). Milestone 2's round handling is purely structural (folder names, no ordering imposed) | **Correctly deferred**, not violated |
| BR-011 | Custom-meta file-manifest entries are the authoritative file list; directory listing is not trusted | **Not applicable to Milestone 2** — custom-meta doesn't exist without XML parsing. `FileInventory` in this milestone is a directory-listing-derived enumeration only, explicitly **not** claimed to be the BR-011 authoritative list (see `FileInventory.anomalous_relative_paths` docstring's explicit disclaimer) | **Correctly deferred**, not violated |
| BR-012/BR-023 | Files copied byte-identical, no format conversion | `Stager.stage_article` copies via `InputReader.fetch_file` (stream copy, `compute_stream_checksum_while_copying`) with no transformation of any kind; verified by checksum re-read (`_verify_integrity`) | **Fully implemented** |
| BR-013 | Original filenames preserved exactly | `FileRecord.relative_path` is never slugified/renamed anywhere in `discovery.py`/`staging.py` | **Fully implemented** |
| BR-015 | Round subfolder name copied verbatim into output | `Stager.stage_article` writes to `working_directory / file_record.round_label / ...` — `round_label` is the literal folder name from `list_article_top_level`, untransformed | **Fully implemented** (for staging destination naming; final package assembly is Milestone 4+) |
| BR-016/BR-017 | File-path resolution tolerates leading-slash / staging-path variance | **Not directly applicable** — Milestone 2 resolves files by directory listing, not by a `path` hint field (that field belongs to custom-meta, Milestone 3+). No leading-slash-sensitive logic exists in this milestone to be inconsistent | N/A, not violated |
| BR-018/BR-019 | A file category can recur per round; category vocabulary is open, not a fixed enum | `FileInventory.by_round`/`round_labels` group by round without assuming any fixed round set; `_KNOWN_OS_ARTIFACT_FILENAMES` in `discovery.py` is an open, extensible set, not a closed enum | **Consistent with the open-vocabulary principle**, though the actual BR-019 category *mapping* (to manifest item-types) is Milestone 3+ scope |
| BR-021 | Declared size available for integrity cross-check | `Stager._verify_integrity` compares `expected_size` (from listing) against `actual_size` (bytes transferred) — implements exactly the validation BR-021 recommended | **Fully implemented** |

**No Business Rule Book rule was violated.** Rules requiring XML content (BR-010, BR-011, BR-016–019's file-category semantics) are correctly and explicitly deferred, not approximated or guessed at.

---

## 2. ADR Compliance

| ADR | Decision | Milestone 2 Implementation | Status |
|---|---|---|---|
| ADR-009 | Isolate failures per article; don't block the batch | `BatchDiscovery.discover` catches `InvalidArticlePackageError`/`DuplicateFileError`/`SourceUnavailableError` per-article and continues; `RunController._process_one` catches `ArticleLevelError` per-article and continues scheduling the rest | **Compliant** — verified by `test_one_bad_article_does_not_block_discovery_of_others`, `test_discovery_failure_recorded_without_blocking_other_articles`, `test_staging_failure_isolated_to_one_article` |
| ADR-013 | Multi-round generalization: design for N rounds, not just 2 | `discovery.py`/`staging.py`/`input.models` never assume a fixed round count or fixed round names anywhere — round labels are discovered dynamically from whatever folders exist | **Compliant** (structurally; full round-*ordering* generalization is Milestone 3's BR-010, correctly deferred) |
| ADR-014 | Round-folder naming is fully generic — no hard-coded pattern | `BatchDiscovery` treats every subfolder under an article root as a round candidate; no `"Original"`/`"R\d+"` pattern matching anywhere | **Fully compliant** |
| ADR-016 | Unreferenced physical files should be logged, not silently dropped | Implemented as the closest available Milestone-2 analog: anomalous files (zero-byte, OS artifacts) are logged at WARN and recorded in `FileInventory.anomalous_relative_paths` rather than silently staged without a trace. The literal ADR-016 scenario (custom-meta-unreferenced files) requires XML parsing and is Milestone 3's to fully implement | **Compliant with available scope**; module docstring flags the distinction explicitly |
| ADR-017 | Package atomicity: never leave a partial artifact | Applied one layer down, to staging: `Stager.stage_article` wraps the whole copy loop in `try/except BaseException: self.cleanup(...); raise` — a partially-staged working directory is always removed before the exception propagates | **Compliant**, extended consistently to this milestone's scope (full package atomicity is Milestone 4+) |
| ADR-019 | S3 input model: batch-pull primary, event-driven path not precluded | `S3BatchSource`/`S3Reader` implement the batch-pull shape (`list_batch_article_ids` = one listing call); nothing in the design assumes a specific dispatch mechanism, leaving an event-driven path open later | **Compliant** |
| ADR-020 | Working-folder staging strategy: full local staging, one subdirectory per article | `Stager._create_workspace` creates exactly `working_dir_root / run_id / article_id`; binary content is streamed disk-to-disk, never fully buffered in memory (`compute_stream_checksum_while_copying`) | **Compliant** |
| ADR-021 | Per-article parallelism as the scaling axis; sequential first, swappable later | `WorkerScheduler` ABC + `SequentialWorkerScheduler` (the only concrete implementation, per this milestone's explicit "no parallel execution yet" instruction) — `RunController` depends only on the ABC, so a future parallel scheduler requires no `RunController` change | **Compliant** |
| ADR-022 | Per-article, per-stage checkpointing; restart-without-reprocessing | `CheckpointStore.transition` is a compare-and-set keyed by `ArticleStage`; `queue_prep.prepare_queue` filters out articles already `>= STAGED`; verified by `test_resume_skips_already_staged_articles` (and confirms **zero re-fetch**, not just a skipped outcome) | **Compliant** |
| ADR-023 | Retry policy: transient vs. permanent classification | Not yet exercised (no `retry.decorators` calls in Milestone 2 — the Retry Manager module remains a stub, correctly out of scope). However, every I/O-fallible operation in this milestone raises the *correctly classified* exception (`ArticleTransientError` subclasses `S3ReadTransientError`/`StagingIntegrityError` vs. non-retryable `SourceUnavailableError`/`InvalidArticlePackageError`), so a future Retry Manager can wrap these calls with zero changes to this milestone's code | **Groundwork compliant**; full retry behavior correctly deferred |
| ADR-031 | Never replicate a sample-package defect as a business rule | Not directly applicable to this milestone (no XML generation occurs) — no risk of this violation existing in Milestone 2's code | N/A |

**No ADR was violated.** Every ADR whose scope touches Milestone 2 is either fully implemented or correctly, explicitly deferred with a documented reason.

---

## 3. HLD Compliance (System Module Breakdown + Data Flow Document)

- **Input Reader module** (`05_SYSTEM_MODULE_BREAKDOWN.md` §2): "Locates and stages one article's complete input... verifying basic integrity... Classifies S3-level failures as transient/permanent." → Implemented as `InputReader` (discovery/enumeration/fetch) + `Stager` (staging/integrity) — a deliberate two-class split of one HLD module's stated responsibility, justified in the Implementation Report's Design Decision D-1/D-2, with no responsibility dropped or added beyond what the HLD module description already covers.
- **Checkpoint Store module** (`05_SYSTEM_MODULE_BREAKDOWN.md` §11): "Durable, queryable record of every article's processing state... atomic compare-and-set semantics." → `CheckpointStore.transition`'s `expected_current`/`new_stage` signature *is* that compare-and-set contract; `InMemoryCheckpointStore` satisfies it exactly (verified by the concurrent-thread race test, §6).
- **Orchestrator / Run Controller module** (`05_SYSTEM_MODULE_BREAKDOWN.md` §1): "Determines the batch of articles to process, dispatches each article to a worker... consults the Checkpoint Store to skip already-completed articles, aggregates final run status." → `RunController.run` performs exactly this sequence (§4 of the Implementation Report); "Not responsible for any article-content transformation logic" is honored — `RunController` never touches file content, only `ArticleReference`/`StagedArticle` metadata.
- **Data Flow Document, Stage 1** (`06_DATA_FLOW_DOCUMENT.md`, "Amazon S3 → Working Folder / Staging"): the described failure paths — "S3 object missing → permanent failure," "S3 throttled → transient, retried," "Truncated/corrupted download → detected via size/checksum check" — map directly to `SourceUnavailableError`, `S3ReadTransientError`, and `StagingIntegrityError` respectively. The document's checkpoint stage name `staging` is used verbatim (`ArticleStage.STAGING`).
- **Data Flow Document's cross-cutting concerns**: "Checkpoint Store: consulted/updated at every stage transition" — verified in `RunController._process_one` (transition to `STAGING` before staging, to `STAGED`/`FAILED` after). "Retry Manager: wraps every stage's externally-fallible operations" — correctly not yet wired (Retry Manager remains a stub); this milestone only ensures the *exceptions* the future Retry Manager will react to are already correctly classified.

**No HLD module's stated responsibility was contradicted, duplicated elsewhere, or silently dropped.**

---

## 4. LLD Compliance

- **Package structure** (`10_LLD_01_STRUCTURE_AND_PACKAGES.md` §2.1): `input/`, `checkpoint/`, `checkpoint/backends/`, `orchestrator/` all populated at exactly the paths the LLD specifies; `utils/hashing.py` implemented at the exact path the LLD names ("checksum helpers used by input/ and output/").
- **Import-direction rules** (`10_LLD_01...` §2.3): verified by direct `grep` (§5 below) — foundation layer (`model`/`config`/`exceptions`/`utils`) unchanged and still depended-on-by-nothing-else; no `generators.*`/`validation`/`packaging`/`output`/`registry` package is imported by any real (non-docstring) statement anywhere in the codebase, since none has been implemented yet; `orchestrator` is imported only from `container.py` (the composition root), never the reverse.
- **ICAM** (`11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md` §3): completely untouched. `input.models`' docstring explicitly states these are "input-layer models only, entirely separate from the ICAM" — no class in `input/` is named, shaped, or documented as if it were (or could substitute for) the ICAM.
- **Exception Framework** (`12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md` §7): the `MecaEngineError` → `ArticleLevelError`/`BatchLevelError` → `ArticleTransientError` hierarchy is used exactly as specified, extended only with new *leaves* (§9.3, no new branch/category); every new exception carries `article_id`/`stage`/`rule_id` per the base class contract.
- **Logging** (`12_LLD_03...` §6): every Milestone 2 class logs exclusively through `meca_engine.logging_.get_logger`/`StructuredLogger` — verified: `grep -rn "logging.getLogger\|print(" src/meca_engine/input src/meca_engine/checkpoint src/meca_engine/orchestrator` returns nothing. `PerformanceTimer` is used in `Stager.stage_article`, matching the LLD's per-stage performance-logging convention.
- **Pipeline & Scalability** (`13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md` §8-9): the single-article execution flow (§8.2's numbered steps 1-2) is implemented for stages 1 ("stage") and the checkpoint transitions around it; §9.1's process-pool-vs-sequential deferral is honored (ADR-021 above); §9.4's disk-space design ("escalate to batch-pause... rather than confusing per-article errors") is implemented verbatim as `InsufficientDiskSpaceError(BatchLevelError)`; §9.5's compare-and-set checkpoint design is implemented exactly.
- **Coding Standards** (`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §13): full type hints, Google-style docstrings on every public class/function, `ruff`/`mypy --strict` clean (§6), one test file per source module mirroring `src/`.

**No LLD-specified class responsibility, dependency rule, or module boundary was altered.**

---

## 5. Verified Structural Checks (no architectural boundary violated)

Run directly against the final Milestone 2 codebase:

```
$ grep -rnE "^(from|import) meca_engine\.(model|extraction|transform|generators|validation|packaging|output|registry|retry|recovery|reporting|monitoring)\b" \
    src/meca_engine/input src/meca_engine/checkpoint src/meca_engine/orchestrator \
    src/meca_engine/container.py src/meca_engine/cli/main.py
NONE FOUND — Milestone 2 code never imports any not-yet-implemented package.

$ grep -rnE "^(from|import) meca_engine\.orchestrator" src/meca_engine --include="*.py" | grep -v "^src/meca_engine/orchestrator/"
src/meca_engine/container.py:42: from meca_engine.orchestrator.run_controller import RunController
src/meca_engine/container.py:43: from meca_engine.orchestrator.scheduler import SequentialWorkerScheduler
— the ONLY external imports of orchestrator/, both from the composition root (container.py), as expected.

$ grep -rn "meca_engine.orchestrator" src/meca_engine/input src/meca_engine/checkpoint
NONE FOUND — input/ and checkpoint/ never import orchestrator/ (correct direction: orchestrator depends on
them, never the reverse).

$ grep -rn "logging.getLogger\|print(" src/meca_engine/input src/meca_engine/checkpoint src/meca_engine/orchestrator
NONE FOUND — every log emission goes through meca_engine.logging_, per Coding Standards §13.5.
```

(All docstring cross-references such as `:mod:`meca_engine.registry.doi_registry.DoiRegistry`` in exception docstrings were manually inspected and confirmed to be documentation-only Sphinx-style references, not executable imports — they exist to tell a future implementer which not-yet-built module will raise/consume a given exception, per the pattern already established in Milestone 1.)

---

## 6. Test Evidence Cross-Reference

| Compliance claim | Verifying test(s) |
|---|---|
| ADR-009 (per-article isolation) | `test_one_bad_article_does_not_block_discovery_of_others`, `test_discovery_failure_recorded_without_blocking_other_articles`, `test_staging_failure_isolated_to_one_article` |
| ADR-017 (atomicity, applied to staging) | `test_disk_space_failure_raises_and_cleans_up`, `test_size_mismatch_raises_staging_integrity_error_and_cleans_up`, `test_checksum_mismatch_raises_staging_integrity_error_and_cleans_up` |
| ADR-022 (resume support, no reprocessing) | `test_resume_skips_already_staged_articles` (asserts **zero** re-fetch calls, not merely a skipped status) |
| §7.3 article-level vs. batch-level distinction (12_LLD_03) | `test_batch_level_error_propagates_and_halts_the_run` |
| Checkpoint compare-and-set correctness under concurrency | `test_concurrent_transitions_are_serialized_and_exactly_one_wins` |
| Failed articles are retried, not permanently skipped | `test_failed_article_is_retried_not_skipped_on_next_run` |
| BR-001 structural half only (not content) | `test_missing_root_xml_recorded_as_discovery_failure`, `test_duplicate_root_xml_recorded_as_discovery_failure` — both operate purely on filenames, no XML content is ever constructed in the fixtures |

---

## 7. Conclusion

Milestone 2 implements the Input & Staging Layer entirely within the
architectural boundaries established by the Business Rule Book, the ADRs,
the HLD, and the LLD. Every rule/decision/module whose scope overlaps this
milestone is either fully implemented or explicitly, documentedly
deferred — none was approximated, guessed at, or silently skipped. No
import-direction rule was violated (verified by direct inspection, §5),
no not-yet-implemented package was given real logic, and the ICAM and
exception-hierarchy boundaries were left exactly as Milestone 1 defined
them, extended only by justified new leaves.

**No architectural boundary was violated. Milestone 2 is ready for review.**
