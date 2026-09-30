# Service Architecture

## Flow

```
ConfigLoader.load_runtime_config()
        │
        ▼
build_processing_service()  (service_factory.py — constructs everything once)
        │
        ▼
ProcessingService.run()
        │
        ├─ InputProvider.list_articles() ──► one Job per article ──► JobQueue (FIFO)
        │
        └─ while queue not empty:
                dequeue Job
                    │
                    ▼
                Worker.process(job)
                    │
                    ├─ run_with_retry( _process_once, RetrySettings )   ◄── new: operational resilience
                    │        │
                    │        ▼
                    │   InputProvider.stage_article(article_id)   (existing, unchanged)
                    │        │
                    │        ▼
                    │   XmlLoader → extract_all_metadata → TransformationCoordinator
                    │   → GeneratorContext                          (existing, unchanged)
                    │        │
                    │        ▼
                    │   PackageBatchRunner.run([context])            (existing, unchanged)
                    │        │  (checkpoint claim/skip/resume, calls PackageBuilder)
                    │        ▼
                    │   PackageOutcome: SUCCEEDED | FAILED | SKIPPED
                    │        │
                    │        ▼
                    │   build_conversion_report / embed / write_certification_report
                    │                                                (existing, unchanged)
                    ▼
                ConversionReport | None  (None = skipped, already complete)
                    │
                    ▼
                OutputProvider already used inside _process_once for the
                package's output_root — no separate "publish" step
                    │
                    ▼
                ProgressTracker.complete_job() + build_status_view(job, report)

        ▼
ProcessingService writes corpus-level reports (Migration Summary, CSVs,
analytics, dashboard JSON, intelligence reports) — existing, unchanged —
and prints the final summary.
```

## Retry boundary (new)

`run_with_retry` (in `meca_engine/retry/`) wraps the *entire* per-article
attempt (staging through the `PackageBatchRunner` call). On a transient
failure (`MecaEngineError.retryable is True`, or an unwrapped transient
`OSError`/`ConnectionError`/`TimeoutError`), the whole attempt is redone
after an exponential backoff, up to `RetrySettings.max_attempts`. On a
deterministic failure (a Business Rule violation, missing source file,
malformed metadata, XML error — every `MecaEngineError` with
`retryable = False` by class default), it is raised immediately, exactly
as before this phase. `PackageBatchRunner`'s own checkpoint semantics
("redo from scratch, never resume mid-way") make retrying the whole
attempt safe.

## Object responsibilities

| Component | Owns |
|---|---|
| `service_factory.build_processing_service` | Constructs every dependency once per batch run |
| `ProcessingService` | Job creation, queue draining, corpus-level reporting, final summary |
| `JobQueue` | Pure in-memory FIFO |
| `Worker` | One article's full pipeline + retry wrapping |
| `ProgressTracker` | Console progress only |
| `status.build_status_view` / `PackageStatusView` | Dashboard-ready view, built from existing `ConversionReport`/`Job` fields — no new computation |
| `meca_engine.retry` | Transient/permanent classification + backoff |

## What never changed

`PackageBuilder`, all 5 XML generators, Business Rules, Recovery Rules,
ICAM, `TransformationCoordinator`'s business logic, reporting
calculations, certification logic, intelligence logic. The Worker calls
into all of them exactly as the old batch script did.
