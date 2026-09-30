# End-to-End Batch Result

Full run against every package in `Input/` (`scripts/archive_migration_batch.py`), never aborting on a failure.

| Metric | Value |
|---|---|
| Packages | 37 |
| Generated | **37/37** |
| Warnings (advisory, non-recovery) | 0 |
| Recoveries | 213 |
| Engine failures | 0 |
| Fatal failures | 0 |

## Status distribution

| Status | Count |
|---|---|
| CERTIFIED | 0 |
| CERTIFIED_WITH_WARNINGS | 3 |
| CERTIFIED_WITH_RECOVERY | 30 |
| PARTIAL_CERTIFICATION | 4 |
| ENGINE_FAILURE | 0 |
| FATAL_FAILURE | 0 |

The 4 `PARTIAL_CERTIFICATION` packages (`bcj-2025-3378`, `cs-2024-5238`, `cs-2025-6682`, `etls-2025-3020`) each have at least one declared file that could not be located and was skipped (RR-002) — every other package's recoveries were lossless (filename derivation, tolerance matching, round deduplication).

Batch never stopped early; every package was attempted and produced either a generated package or a classified failure. No fatal or engine-failure case occurred in this corpus.
