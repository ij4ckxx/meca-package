# Milestone 13 — Archive Migration Certification & Production Reporting

Reporting-only milestone: no generator, Business Rule, or Recovery Rule behavior changed. Everything below reads an already-built `ConversionReport` and reshapes it.

## What was built

**New module:** `src/meca_engine/reporting/` (aggregation, certification_report, migration_summary, csv_reports, analytics, dashboard, package_embed).

1. **Per-article Certification Report** — `MECA_<ArticleID>_Certification_Report.html`, plain semantic HTML (no JS, no external assets, no tracebacks). Written next to each generated package.
2. **Executive Summary** — `Migration_Summary.html` — status/confidence distribution, Recovery/Business Rule usage, failure reasons, journal breakdown.
3. **Package Manifest** — `conversion-report.json` embedded into every generated MECA zip as a post-processing step (`embed_conversion_report`) — no `PackageBuilder` change, since the Conversion Report can only be built after the zip already exists.
4. **Customer Audit Log** — `Archive_Audit.csv`, one row per article, Excel-importable.
5. **Recovery Analytics** — `Recovery_Analytics.md` — most common/rarest recoveries, per-journal recovery load, lossless-vs-content-affecting trend.
6. **Business Rule Statistics** — `Business_Rule_Statistics.md` — Triggered/Recovered/Warning/Fatal per rule, computed from this batch's actual findings against all 160 BR IDs (unreferenced ones counted as Unused, not re-audited).
7. **Confidence Calculation, formalized** — `_confidence_score` in `conversion_report.py` now sums 5 explicit, documented penalty categories instead of two generic ones: lossless recovery (RR-001/004/005, small), missing metadata (RR-003/006/007, moderate), skipped asset (RR-002, largest), unresolved warning, and generator-layer ERROR findings.
8. **Manual Review Queue** — `Manual_Review.csv`, only articles with `PARTIAL_CERTIFICATION`/failure status, low overall confidence, or a low-confidence individual recovery — sorted by priority.
9. **Dashboard JSON** — `migration_dashboard.json` — aggregate stats plus a compact per-article record. No dashboard built.
10. **`ConversionReport` extended** (not rewritten): added `journal`, `missing_metadata`, `overall_confidence` bucketing already existed from the prior milestone.

## Verification

- Full existing regression suite: **1024/1024 passed** (11 new targeted tests for the reporting layer; everything else unchanged).
- `ruff`/`mypy --strict`: clean across `src/`, `tests/`, `scripts/`.
- One full end-to-end batch (37/37 `Input/` packages): identical status distribution to the pre-milestone run (0 certified, 3 certified-with-warnings, 30 certified-with-recovery, 4 partial-certification, 0 engine/fatal failures) — confirms package generation is unchanged.
- Spot-checked: `conversion-report.json` present inside a real generated zip; per-article HTML reports readable with no Python internals; `Manual_Review.csv` correctly surfaces exactly the 4 partial-certification articles plus low-confidence ones, sorted by priority; `Business_Rule_Statistics.md` matches the batch's real BR references (7 used, 153 unused).
- Golden test suite: same 3 pre-existing, unrelated failures as before this milestone — untouched.
