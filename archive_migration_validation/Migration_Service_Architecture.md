# Migration Service Architecture

## Flow

```
InputProvider.stage_article()
        │
        ▼
Extraction → Transformation → GeneratorContext        (existing, unchanged)
        │
        ▼
PackageBatchRunner.run([context])                      (existing, unchanged)
   (checkpoint claim/skip/resume, calls PackageBuilder)
        │
        ▼
ConversionReport built + embedded; Certification Report written
   at the neutral staging root: OutputProvider.article_output_root(id)
        │                                               (existing, unchanged)
        ▼
┌───────────────────── Decision (new) ─────────────────────┐
│  OutputRouter.decide_category(report.status)              │
│                                                             │
│  CERTIFIED / CERTIFIED_WITH_WARNINGS / CERTIFIED_WITH_RECOVERY │
│        → move staged_root  →  OutputProvider.category_root("uploaded")/<id>/
│                                                             │
│  PARTIAL_CERTIFICATION                                     │
│        → move staged_root  →  category_root("manual_review")/<id>/
│          + write conversion-report.json                    │
│                                                             │
│  ENGINE_FAILURE / FATAL_FAILURE  (no package was built)     │
│        → write Certification Report + conversion-report.json │
│          directly into  category_root("failed")/<id>/       │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
job.output_location = final destination
        │
        ▼
ProcessingService (unchanged): corpus-level reports written to
dashboard.reports_path — Migration Summary, CSVs, analytics,
dashboard JSON, intelligence reports.
```

## Output structure

```
<output.local_path>/
├── uploaded/<article_id>/          MECA_<id>.zip, Certification Report
├── manual_review/<article_id>/     MECA_<id>.zip, Certification Report, conversion-report.json
└── failed/<article_id>/            Certification Report, conversion-report.json  (no zip — none was built)
```
`reports/` (corpus-level) stays at `dashboard.reports_path`, a sibling
directory, unchanged from Phase 1/2.

## Why routing happens after build, not before

`PackageBuilder.build()` needs a concrete `output_root` before it knows
the package's outcome — `PackageStatus` is only computed once generation
completes. So `Worker` always builds at the same neutral staging root
(`article_output_root`, as before this phase), and `OutputRouter` moves
the completed, already-certified package to its decided category
afterward. This keeps `PackageBuilder`'s contract (an ``output_root`` it
writes into) completely unchanged.

## Object responsibilities (new/changed only)

| Component | Owns |
|---|---|
| `OutputProvider.category_root` | A named, provider-backed output folder (new capability, additive) |
| `OutputRouter` | Deciding + moving/writing each article's final artifacts |
| `Worker` | Calls the router once per job, after the report is built |
