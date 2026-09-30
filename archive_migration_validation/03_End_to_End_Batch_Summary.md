# End-to-End Batch Summary

Full 37-package corpus (6 journals), same dataset as the prior production-validation round, re-run through `scripts/archive_migration_batch.py` after the Recovery + Warning framework changes. Batch never stopped on a failure; every package was attempted.

## Headline result

| Metric | Before this milestone | After |
|---|---|---|
| Packages generated | 30/37 (81%) | **37/37 (100%)** |
| PASS | 30 | 0 |
| PASS WITH WARNINGS | 0 | 3 |
| PASS WITH RECOVERY | — (status didn't exist) | 34 |
| FAILED | 7 | 0 (0 FAILED_ENGINE, 0 FAILED_FATAL) |

`PASS` dropping to 0 is expected, not a regression: `generator_findings` (the pre-existing per-generator diagnostics — round-label mismatches, missing reviewer recommendations, etc.) are near-universal in this corpus (611 total across 37 packages, confirmed in the prior validation round) and now correctly influence `PackageStatus`, which they did not before. Every package that used to report `PASS` now correctly reports `PASS_WITH_WARNINGS` or `PASS_WITH_RECOVERY` once those pre-existing findings are counted — nothing about the underlying packages changed, only what status now reflects.

## The 7 previously-failing packages — all recovered

| Article | Old result | New result | Recovery applied |
|---|---|---|---|
| `bcj-2025-3378` | FAIL (missing supplement) | PASS_WITH_RECOVERY | Missing file skipped (BR-011), 2 files resolved via tolerant match (BR-016) |
| `bcj-2025-3400` | FAIL (34 duplicate round versions) | PASS_WITH_RECOVERY | Duplicate snapshot events deduplicated to 1 round (BR-010) |
| `bst-2025-3127` | FAIL (license file "missing") | PASS_WITH_RECOVERY | Resolved via the tier-3 tolerance bug fix (BR-016) — the file was never actually missing |
| `cs-2024-5238` | FAIL (embedded-image reference) | PASS_WITH_RECOVERY | 4 files skipped (embedded/unresolvable figures, BR-011), 6 filename fallbacks (BR-013), 5 tolerant matches (BR-016) |
| `cs-2025-6619` | FAIL (cover letter "missing") | PASS_WITH_RECOVERY | Resolved via the tier-3 tolerance bug fix, plus 5 more tolerant matches |
| `cs-2025-6682` | FAIL (license form missing) | PASS_WITH_RECOVERY | 4 genuinely-missing files skipped (BR-011), 15 tolerant matches (BR-016) |
| `etls-2025-3020` | FAIL (license file missing) | PASS_WITH_RECOVERY | 1 genuinely-missing file skipped (BR-011) |

## Recovery statistics across the batch

| Recovery code | Count | Meaning |
|---|---|---|
| `BR016_TOLERANT_FILE_MATCH` | 189 | File resolved via a non-exact tolerance tier (stem/prefix/normalized) — now surfaced, previously silent |
| `BR013_FALLBACK_FILENAME_FROM_PATH` | 12 | Filename derived from `declared_path_hint` (Milestone 10 mechanism, unchanged) |
| `BR011_FILE_ENTRY_SKIPPED` | 11 | Non-manuscript file entry with no matching physical file, skipped rather than failing the package |
| `BR010_DUPLICATE_SEQUENCE_DEDUPED` | 1 | Duplicate round-version snapshot events collapsed |
| **Total recoveries** | **213** | |

No package required more than one category of recovery to stack into a failure the engine couldn't handle — every recovery path terminated in a complete, valid package.

## Confidence scores

Average confidence score across the batch: **38/100**. This is intentionally a blunt, high-sensitivity signal (documented in `conversion_report.py`): it penalizes every recovery and every pre-existing generator finding, including the near-universal ones (round-label mismatches, missing reviewer dates) already known from the prior validation round to be normal for this data. Several busy packages (e.g. `CS-2025-6808`, `cs-2024-5238`) floor at 0 — this reflects a high finding *count*, not necessarily a quality problem, and is intentionally left simple pending real dashboard usage to tune it, per this milestone's "don't over-build" scope.

## No fabrication

Every one of the 213 recoveries is independently traceable to a specific, quoted source-data value or a specific, cited resolver decision (see `conversion_reports.json`). No filename, reviewer name, editor name, date, or DOI was invented anywhere in this run — every recovery either (a) derived a value that already existed verbatim in the source data, (b) matched two already-existing pieces of data together via a documented tolerance rule, or (c) omitted something rather than guessing at it.

## No new engine defects discovered

No `FAILED_ENGINE` or `FAILED_FATAL` occurred anywhere in this batch. See `04_New_Defects_Found.md`.
