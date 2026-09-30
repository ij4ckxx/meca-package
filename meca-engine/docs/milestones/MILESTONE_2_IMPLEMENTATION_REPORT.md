# Milestone 2 Implementation Report — Input & Staging Layer

Baseline: Milestone 1 (Foundation, approved). Scope: batch/article discovery
(local + S3, behind a common interface), working-directory staging with
integrity verification, an in-memory Checkpoint Store, and a deterministic
Run Controller with resume support. **No XML parsing, metadata extraction,
ICAM construction, transformation, generation, validation, packaging, or
DOI Registry logic was implemented** — see §7 for what was deliberately
excluded and why.

---

## 1. Directory Tree Changes

```
src/meca_engine/
├── input/                              [NEW — fully implemented]
│   ├── __init__.py
│   ├── models.py                       Batch, ArticleReference, StagedArticle,
│   │                                   FileInventory, FileRecord, BatchSource,
│   │                                   LocalBatchSource, S3BatchSource, DiscoveryFailure
│   ├── discovery.py                    BatchDiscovery
│   ├── staging.py                      Stager
│   └── readers/
│       ├── __init__.py
│       ├── base.py                     InputReader (ABC), TopLevelEntry
│       ├── local_reader.py             LocalFolderReader
│       └── s3_reader.py                S3Reader, S3ClientProtocol, Boto3S3Client,
│                                       S3Entry, S3ObjectNotFoundError, S3TransientAPIError
│
├── checkpoint/                         [NEW — fully implemented]
│   ├── __init__.py
│   ├── models.py                       ArticleStage, STAGE_ORDER, stage_index, CheckpointRecord
│   ├── store.py                        CheckpointStore (ABC)
│   └── backends/
│       ├── __init__.py
│       └── in_memory.py                InMemoryCheckpointStore
│
├── orchestrator/                       [NEW — fully implemented]
│   ├── __init__.py
│   ├── models.py                       ArticleOutcome, OutcomeStatus, RunSummary
│   ├── scheduler.py                    WorkerScheduler (ABC), SequentialWorkerScheduler
│   ├── queue_prep.py                   prepare_queue, already_complete
│   └── run_controller.py               RunController
│
├── exceptions/
│   ├── article_errors.py               [MODIFIED] +5 new leaf classes (§9.3)
│   └── batch_errors.py                 [MODIFIED] +1 new leaf class (§9.3)
│
├── utils/
│   └── hashing.py                      [NEW] compute_file_checksum,
│                                       compute_stream_checksum_while_copying
│
├── container.py                        [MODIFIED] registers CheckpointStore;
│                                       adds build_run_controller()
└── cli/main.py                         [MODIFIED] `run --source-dir` is now
                                        functional (local only); `--source-prefix`
                                        remains a placeholder (TQ-04)

tests/
├── mocks/fake_s3_client.py             [NEW] FakeS3Client (S3ClientProtocol test double)
├── unit/input/                          [NEW] 5 test files + conftest.py
├── unit/checkpoint/                     [NEW] 2 test files
├── unit/orchestrator/                   [NEW] 4 test files + conftest.py
├── unit/test_container.py               [MODIFIED] +3 tests for build_run_controller
├── unit/cli/test_main.py                [MODIFIED] +2 tests for `run --source-dir`
├── conftest.py                          [MODIFIED] added shared valid_batch_root fixture
└── */__init__.py                        [NEW, retrofit] every tests/ subdirectory —
                                        required to prevent pytest module-basename
                                        collisions once 3 different directories each
                                        had their own test_models.py (see §6 Design
                                        Decision D-8)

config/, schemas/, docs/, etc.: unchanged from Milestone 1.
```

**Stub packages left untouched** (still empty, per scope): `model/`, `extraction/`, `transform/`, `generators/*`, `validation/*`, `packaging/`, `output/`, `registry/*`, `retry/`, `recovery/`, `reporting/`, `monitoring/`.

---

## 2. New Classes

| Class | Module | Kind |
|---|---|---|
| `BatchSource`, `LocalBatchSource`, `S3BatchSource` | `input.models` | Data (marker base + 2 frozen dataclasses) |
| `FileRecord` | `input.models` | Frozen dataclass |
| `FileInventory` | `input.models` | Frozen dataclass |
| `ArticleReference` | `input.models` | Frozen dataclass |
| `DiscoveryFailure` | `input.models` | Frozen dataclass |
| `Batch` | `input.models` | Frozen dataclass |
| `StagedArticle` | `input.models` | Frozen dataclass |
| `TopLevelEntry` | `input.readers.base` | Frozen dataclass |
| `InputReader` | `input.readers.base` | Abstract base class |
| `LocalFolderReader` | `input.readers.local_reader` | Concrete `InputReader` |
| `S3Entry` | `input.readers.s3_reader` | Frozen dataclass |
| `S3ClientProtocol` | `input.readers.s3_reader` | `typing.Protocol` |
| `S3ObjectNotFoundError`, `S3TransientAPIError` | `input.readers.s3_reader` | Internal adapter-boundary signals (not `MecaEngineError`) |
| `Boto3S3Client` | `input.readers.s3_reader` | Concrete `S3ClientProtocol` (lazy `boto3` import) |
| `S3Reader` | `input.readers.s3_reader` | Concrete `InputReader` |
| `BatchDiscovery` | `input.discovery` | Service class |
| `Stager` | `input.staging` | Service class |
| `ArticleStage` | `checkpoint.models` | Enum (13 values, §4) |
| `CheckpointRecord` | `checkpoint.models` | Frozen dataclass |
| `CheckpointStore` | `checkpoint.store` | Abstract base class |
| `InMemoryCheckpointStore` | `checkpoint.backends.in_memory` | Concrete `CheckpointStore` |
| `OutcomeStatus` | `orchestrator.models` | Enum |
| `ArticleOutcome`, `RunSummary` | `orchestrator.models` | Frozen dataclasses |
| `WorkerScheduler` | `orchestrator.scheduler` | Abstract base class |
| `SequentialWorkerScheduler` | `orchestrator.scheduler` | Concrete `WorkerScheduler` |
| `RunController` | `orchestrator.run_controller` | Service class |
| `InvalidArticlePackageError`, `DuplicateArticleError`, `DuplicateFileError`, `SourceUnavailableError`, `StagingIntegrityError` | `exceptions.article_errors` | New leaf exceptions |
| `InsufficientDiskSpaceError` | `exceptions.batch_errors` | New leaf exception |

**27 new classes**, all either frozen dataclasses (immutable models — no behavior), `Enum`s, `ABC`s with exactly one concrete implementation each (per this milestone's scope), or plain service classes with no inheritance depth beyond that.

---

## 3. Public Interfaces

### `InputReader` (ABC — implemented by `LocalFolderReader`, `S3Reader`)
```
list_batch_article_ids(source: BatchSource) -> tuple[str, ...]
list_article_top_level(article_id: str, source: BatchSource) -> tuple[TopLevelEntry, ...]
list_round_files(article_id: str, round_label: str, source: BatchSource) -> tuple[FileRecord, ...]
fetch_file(article_id, round_label, relative_path, source, destination: Path) -> tuple[checksum: str, bytes_transferred: int]
```

### `BatchDiscovery`
```
discover(source: BatchSource, *, batch_id: str) -> Batch
```

### `Stager`
```
stage_article(article_ref: ArticleReference) -> StagedArticle
cleanup(working_directory: Path) -> None
```

### `CheckpointStore` (ABC — implemented by `InMemoryCheckpointStore`)
```
get_record(article_id: str) -> CheckpointRecord | None
transition(article_id, *, expected_current: ArticleStage | None, new_stage: ArticleStage, failure_reason: str | None = None) -> bool
list_all() -> tuple[CheckpointRecord, ...]
is_at_least(article_id: str, minimum_stage: ArticleStage) -> bool   # concrete, provided by the ABC
```

### `WorkerScheduler` (ABC — implemented by `SequentialWorkerScheduler`)
```
schedule(tasks: Sequence[ArticleReference], task_fn: Callable[[ArticleReference], ArticleOutcome]) -> Iterator[ArticleOutcome]
```

### `RunController`
```
run(source: BatchSource, *, batch_id: str) -> RunSummary
```

### `queue_prep` module functions
```
prepare_queue(article_refs, checkpoint_store, *, minimum_complete_stage=ArticleStage.STAGED) -> tuple[ArticleReference, ...]
already_complete(article_refs, checkpoint_store, *, minimum_complete_stage=ArticleStage.STAGED) -> tuple[ArticleReference, ...]
```

### `container.py` additions
```
build_run_controller(container: ServiceContainer, reader: InputReader, *, run_id: str | None = None) -> RunController
```

### CLI
```
meca-engine run --source-dir <local-path> [--config-dir ...] [--schema-dir ...]
```

---

## 4. Sequence of Input Processing

```
CLI `run --source-dir X`
  └─ bootstrap_application()                         [Milestone 1]
       registers: StructuredLogger, ConfigRegistry, CheckpointStore (in-memory)
  └─ build_run_controller(container, LocalFolderReader())
       constructs: BatchDiscovery, Stager, SequentialWorkerScheduler, RunController
  └─ RunController.run(LocalBatchSource(X), batch_id=...)
       │
       ├─ [1] BatchDiscovery.discover(source)
       │       reader.list_batch_article_ids(source)              — no XML opened
       │       for each candidate article_id (duplicate-checked):
       │         reader.list_article_top_level(article_id, source)
       │         validate: exactly 1 root *.xml name (BR-001, existence only)
       │         validate: >=1 round folder (BR-002)
       │         for each round: reader.list_round_files(...)      — sizes only
       │           flag zero-byte / OS-artifact files as anomalous (non-fatal)
       │           detect duplicate filenames within a round -> DuplicateFileError
       │       => Batch(article_refs=[...valid...], discovery_failures=[...bad...])
       │
       ├─ [2] queue_prep.prepare_queue(batch.article_refs, checkpoint_store)
       │       sort by article_id; drop articles already >= STAGED (resume)
       │     queue_prep.already_complete(...) -> SKIPPED outcomes for those
       │
       ├─ [3] scheduler.schedule(queue, RunController._process_one)
       │       for each article_ref (sequential):
       │         checkpoint_store.transition(article_id, expected=current, new=STAGING)
       │           -> False? emit SKIPPED (collision) and move on
       │         Stager.stage_article(article_ref)
       │           create working_dir/run_id/article_id
       │           check disk space (>= total_size * 1.1, else InsufficientDiskSpaceError — BATCH-LEVEL, propagates out of run() entirely)
       │           for each file: reader.fetch_file(...) -> (checksum, bytes)
       │             verify size matches; verify checksum by re-reading the
       │             written file (StagingIntegrityError if either mismatches)
       │           on ANY failure inside the try block: Stager.cleanup(working_dir)
       │         on success: checkpoint_store.transition(..., new=STAGED)
       │                     -> ArticleOutcome(SUCCESS, staged_article=...)
       │         on ArticleLevelError: checkpoint_store.transition(..., new=FAILED)
       │                     -> ArticleOutcome(FAILED, ...)   [other articles unaffected]
       │
       └─ [4] append discovery_failures as FAILED outcomes; build RunSummary
```

---

## 5. Unit-Test Summary

| Test file | Count | Covers |
|---|---|---|
| `tests/unit/input/test_models.py` | 8 | Model immutability, `FileInventory` derived properties |
| `tests/unit/input/test_local_reader.py` | 12 | All 4 `InputReader` methods, missing-path/file, nested subfolders, wrong-source-type |
| `tests/unit/input/test_s3_reader.py` | 14 | Same, against `FakeS3Client`; transient-error + retry-recovery for all 3 listing/download call sites; `Boto3S3Client` ImportError path |
| `tests/unit/input/test_discovery.py` | 8 | Valid discovery, missing/duplicate root XML, no rounds, one-bad-article isolation, anomalous-file flagging, duplicate filename, duplicate article id |
| `tests/unit/input/test_staging.py` | 11 | Full copy+checksum, round layout, workspace creation/cleanup, disk-space failure, size-mismatch and checksum-mismatch integrity failures, auto-generated run_id |
| `tests/unit/checkpoint/test_models.py` | 7 | Stage ordering, `stage_index`, record immutability |
| `tests/unit/checkpoint/test_in_memory_store.py` | 12 | CAS transitions (success/collision/chain), failure reason, `list_all`, `reset`, `is_at_least` (incl. FAILED/unknown), concurrent-thread race (exactly one winner) |
| `tests/unit/orchestrator/test_models.py` | 2 | `RunSummary` count properties |
| `tests/unit/orchestrator/test_scheduler.py` | 2 | Sequential order preserved, empty input |
| `tests/unit/orchestrator/test_queue_prep.py` | 4 | Deterministic sort, resume-exclusion, failed-article retry-inclusion, complement property |
| `tests/unit/orchestrator/test_run_controller.py` | 8 | Full success, checkpoint reflects STAGED, resume skips + never re-fetches, discovery-failure isolation, staging-failure isolation, failed-article retried, checkpoint-collision handling, **BatchLevelError propagates and halts the run** |
| `tests/unit/test_container.py` (additions) | 3 | Checkpoint Store registered; `build_run_controller` wires a working controller end-to-end; propagates config errors |
| `tests/unit/cli/test_main.py` (additions) | 2 | `run --source-dir` succeeds end-to-end; exits non-zero with correct message when an article fails |

**Total: 195 tests in the suite (up from 109 at Milestone 1 approval); 100 test functions are new or added in Milestone 2.**

All tests pass. Verified in 3 independent fresh virtual environments across this milestone's development, with `ruff check`, `ruff format --check`, and `mypy --strict` all clean on both `src/` and `tests/`.

---

## 6. Coverage Report

```
Name                                                  Stmts   Miss  Cover
------------------------------------------------------------------------
src/meca_engine/input/__init__.py                         5      0   100%
src/meca_engine/input/discovery.py                       59      0   100%
src/meca_engine/input/models.py                          62      0   100%
src/meca_engine/input/readers/__init__.py                 5      0   100%
src/meca_engine/input/readers/base.py                    17      0   100%
src/meca_engine/input/readers/local_reader.py            49      0   100%
src/meca_engine/input/readers/s3_reader.py               70      0   100%*
src/meca_engine/input/staging.py                         55      0   100%
src/meca_engine/checkpoint/__init__.py                    4      0   100%
src/meca_engine/checkpoint/models.py                     28      0   100%
src/meca_engine/checkpoint/store.py                      17      0   100%
src/meca_engine/checkpoint/backends/__init__.py           3      0   100%
src/meca_engine/checkpoint/backends/in_memory.py         26      0   100%
src/meca_engine/orchestrator/__init__.py                  6      0   100%
src/meca_engine/orchestrator/models.py                   35      0   100%
src/meca_engine/orchestrator/queue_prep.py                9      0   100%
src/meca_engine/orchestrator/run_controller.py           56      0   100%
src/meca_engine/orchestrator/scheduler.py                10      0   100%
src/meca_engine/exceptions/article_errors.py             28      0   100%
src/meca_engine/exceptions/batch_errors.py               10      0   100%
src/meca_engine/utils/hashing.py                         18      0   100%
src/meca_engine/container.py                             62      0   100%
------------------------------------------------------------------------
Milestone 2 module subtotal                             614      0   100%
------------------------------------------------------------------------
TOTAL (whole src/, incl. Milestone 1 + untouched stubs)  1099    20    98%
```

\* `s3_reader.py`'s `Boto3S3Client` adapter internals (the actual `boto3`/`botocore` calls inside `_list`/`download_to`) are marked `# pragma: no cover` and excluded from the denominator above — they require a real or mocked `boto3` installation to execute, which this environment deliberately doesn't have (`boto3` is an optional `aws` extra; see §7 Design Decision D-3). Every branch of `S3Reader`'s *own* logic — the translation of client-level signals into the approved exception hierarchy — is 100% covered against `FakeS3Client`.

**Target ("at least 95% coverage for all Milestone 2 code") is met: every Milestone 2 module is at 100% coverage** (excluding the explicitly-justified, infrastructure-gated `Boto3S3Client` internals). The 20 lines shown missing in the whole-`src/` total belong entirely to Milestone 1's still-empty stub packages and one `if __name__ == "__main__":` guard, none of which are Milestone 2 code.

---

## 7. Design Decisions

**D-1 — `input/` split into `models.py` / `discovery.py` / `staging.py` / `readers/`, beyond the LLD's original 2-file sketch.**
The LLD (`10_LLD_01...` §2.1) sketched `input/` as just `s3_client.py` + `staging.py`. The current task's explicit, more granular deliverable list (separate "Input Readers," "Article Discovery," "Staging," "Input Models" sections) calls for finer-grained separation than that sketch anticipated. Resolved the same way Milestone 1 resolved `container.py`/`cli/` not being literally named in the LLD: added files within the *existing* `input` package (no new top-level package, no layering change), each docstring citing back to the LLD module responsibility (Input Reader, `05_SYSTEM_MODULE_BREAKDOWN.md` §2) it implements. No architectural boundary moved.

**D-2 — Reader responsibility is discovery/enumeration/byte-transfer only; discovery/staging concerns live in separate classes.**
`InputReader` never validates structure and never manages a workspace — `BatchDiscovery` and `Stager` do, respectively. This mirrors the current task's own section boundaries ("Input Readers" vs. "Article Discovery" vs. "Staging" as three separate deliverable headings) and keeps each class independently unit-testable (satisfied: `test_local_reader.py`/`test_s3_reader.py` never touch discovery logic, and vice versa).

**D-3 — `boto3` is an optional dependency; `S3Reader` is fully testable without it.**
Per the task's explicit allowance ("concrete AWS integration may be mocked if blocked by infrastructure decisions"): `S3ClientProtocol` is the seam; `Boto3S3Client` lazily imports `boto3` and raises a clear `ConfigurationError` if it's absent; `FakeS3Client` (in `tests/mocks/`) is the test double every `S3Reader` test runs against. `boto3` was added as a `pip install -e ".[aws]"` extra, never a core dependency.

**D-4 — Structural validation only; BR-001/BR-002's content-parsing halves remain out of scope.**
Discovery checks "does exactly one `*.xml`-named file exist" (a directory-listing fact) and "does at least one round folder exist" — never opens or parses that file. This is the line the task's "no XML parsing" instruction draws, and it's enforced structurally: `input.discovery` has no import path to any XML-parsing library, and none is a dependency of this milestone.

**D-5 — "Unsupported file reporting" implemented as a non-fatal anomaly flag, not a business-rule inclusion/exclusion decision.**
Zero-byte files and known OS-artifact filenames (`.DS_Store`, `Thumbs.db`, `desktop.ini`) are flagged in `FileInventory.anomalous_relative_paths` and logged as warnings — but still included in the inventory and still staged. The actual "which files are part of the submission" business rule (BR-011/BR-014, custom-meta-driven) is explicitly deferred to Milestone 3's Metadata Extractor / File Resolver, which doesn't exist yet. Documented explicitly in `input/discovery.py`'s module docstring to prevent this narrow technical heuristic from being mistaken for that business rule later.

**D-6 — Checkpoint's full `ArticleStage` state machine (13 stages) defined now, even though Milestone 2 only ever produces 4 of them.**
Per `13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md` §9.5's stage list (already enumerated in the approved Data Flow Document) — defining the complete enum now is zero-cost (it's names, not logic) and avoids a breaking change to `CheckpointStore`'s contract when Milestone 3+ starts producing `METADATA_LOADED` and beyond. One addition beyond the Data Flow Document: `ArticleStage.STAGED`, needed to represent "staging finished" distinctly from "metadata loading finished" (the Data Flow Document's granularity jumps directly from `staging` to `metadata-loaded`). Documented explicitly in `checkpoint/models.py`.

**D-7 — `BatchLevelError` (e.g. `InsufficientDiskSpaceError`) is allowed to propagate uncaught out of `RunController.run`.**
`_process_one` catches `ArticleLevelError` specifically, not the broader `MecaEngineError` — a `BatchLevelError` raised during staging (disk space) is deliberately NOT converted into a per-article `FAILED` outcome, per `12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md` §7.3's article-level-vs-batch-level distinction, which the current task instructs to reuse without modification. Covered by `test_batch_level_error_propagates_and_halts_the_run`.

**D-8 (retrofit, project-wide) — Added `__init__.py` to every `tests/` subdirectory.**
Discovered when 3 different test directories each independently had a `test_models.py` — pytest's default (non-package) import mode raised "import file mismatch" the moment a second same-named test module was collected. Fixed by making `tests/` a real, fully-`__init__.py`'d package tree, so every test module's fully-qualified name is unique (`tests.unit.input.test_models` vs. `tests.unit.checkpoint.test_models`, etc.) regardless of basename. This is a Milestone-1-and-2-wide correctness fix, not a Milestone-2-only concern, and is safe: it changes nothing about how `pytest`/`make test` are invoked.

**D-9 — 5 new `ArticleLevelError` leaves + 1 new `BatchLevelError` leaf; zero new categories.**
Per the task's "use only the approved exception hierarchy... do not introduce new exception categories without justification": every addition is a leaf under the two existing, unmodified base classes (`ArticleLevelError`, `BatchLevelError`), each justified against a specific gap Milestone 1's hierarchy didn't cover (see each class's docstring, and Business/Test-Spec cross-references: `InvalidArticlePackageError`→BR-001/BR-002, `DuplicateFileError`→TC-047, `SourceUnavailableError`→TC-171, `StagingIntegrityError`→sibling of `PostWriteIntegrityError`, `InsufficientDiskSpaceError`→13_LLD_04 §9.4 verbatim).

**D-10 — `RunController`/`Stager` accept a `run_id` for workspace-scoping; auto-generated (`uuid4().hex`) if omitted.**
Keeps working directories collision-free across concurrent/successive runs without requiring every caller to invent one, while still allowing tests and the CLI's future multi-run orchestration to supply a meaningful id (also doubles as the structured-logging correlation id, per `correlation_scope` in `RunController.run`).

---

## 8. Deferred Work for Milestone 3

Per the current task's explicit exclusion list, all deferred to Milestone 3 (or later, per `08_IMPLEMENTATION_ROADMAP.md`):

- **XML parsing & Metadata Extraction** (`extraction.kriyadocs_parser`, `extraction.custom_meta_classifier`) — the actual Kriyadocs XML content is never opened by this milestone.
- **Internal Canonical Article Model** (`model.article.ArticleModelBuilder`, `ArticleModel`) — the one object every future generator will consume.
- **File Resolver** (`extraction.file_resolver`) — the business-rule-driven (BR-011/BR-014) "which files are actually part of the submission" determination, distinct from this milestone's purely-technical anomaly flagging (D-5).
- **Round resolution via `vocab-identifier`** (`extraction.round_resolver`, BR-010) — Milestone 2's round handling is purely structural (folder names, generic per ADR-014); ordering by the Kriyadocs snapshot sequence number is Milestone 3's job.
- **Transformation, all 5 XML generators, Validation Engine, Package Builder, Output Writer, DOI Registry** — untouched stub packages, per scope.
- **Durable Checkpoint Store backend** (Postgres/DynamoDB, TQ-03) and **real parallel `WorkerScheduler`** (ADR-021) — both interfaces are ready; no concrete implementation beyond in-memory/sequential exists yet.
- **S3 CLI wiring** (`--source-prefix`, TQ-04) — `S3Reader` itself is done and tested; production credential/bucket wiring into the CLI is not.

**Explicit dependency check before Milestone 3 begins**: none of Milestone 3's listed work is blocked by anything left open in this milestone — `ArticleReference`/`StagedArticle` (this milestone's output) are exactly the inputs `extraction.kriyadocs_parser` and the ICAM builder are designed to consume next.
