# Migration Audit Implementation

Audit and reporting layer only — no conversion logic, generator, Business
Rule, Recovery Rule, `PackageBuilder`, validator, certification, or
routing code was modified. Every new module reads an already-built
`ConversionReport` (plus one new, purely additive field on it) and
writes additional reports; nothing about package generation changed.

## What was added

### Per-package (written in `service/worker.py`, before the package is
routed to its final category — same point `write_certification_report`/
`write_validation_report` already run)

- **`MECA_<id>_Migration_Audit_Report.html`** — `reporting/migration_audit.py`.
  Package Status, Certification Status, Confidence, Generated Time,
  Engine Version, Business Rule states (Passed/Applied/Warning/Recovery/
  Skipped/Failed), Recovery Rules Applied (rule/confidence/reason),
  Warnings, Fatal Issues, Remaining Source Problems, Remaining DTD
  Problems, Files Generated/Missing, Validation Summary, and a Rule
  Traceability table.
- **`migration-audit.json`** — same module, `write_migration_audit_json`.
  Built from the identical `build_migration_audit_data()` function the
  HTML report uses, so the two can never drift apart.
- **`MECA_<id>_Transformation_Summary.html`** — `reporting/transformation_summary.py`.
  Source → Extraction → Transformation → Generation → Validation →
  Certification, each stage's Success/Warnings/Recoveries/Failures.

### Per-batch (written in `service/processing_service.py`'s existing
`_write_intelligence_reports`, right after the intelligence stats it
already computes)

- **`Batch_Audit_Report.html`** — `reporting/batch_audit_report.py`.
  Consolidates already-computed `business_rule_statistics`,
  `recovery_statistics`, `confidence_statistics`, `journal_statistics`,
  and `csv_reports.build_manual_review_rows` into one page, plus one
  genuinely new aggregation: DTD pass/warning/error/not-checked counts
  per generated file type (from each report's own `validation_report`).
- **`Operator_Checklist.html`** — `reporting/operator_checklist.py`.
  Buckets every article into Ready to Upload / Ready for Manual Review /
  Needs Investigation / Failed — mapped directly from the real
  `PackageStatus` values `service/router.py` already routes on (see
  that module's own docstring for the exact mapping and reasoning).

### New model field

`ConversionReport.reproducibility: ReproducibilityInfo | None` —
additive, defaults to `None`, mirrors exactly how `validation_report`
was added in the DTD-compliance milestone. Built once per package
(`reporting/reproducibility.py`) via `dataclasses.replace()`, same
pattern `worker.py` already used for attaching `validation_report`.

## Reproducibility metadata — what's real vs. what's newly computed

| Field | Source |
|---|---|
| `engine_version` | `meca_engine.__version__` (already existed) |
| `business_rule_book_version` | New constant, manually kept in sync with `01_BUSINESS_RULE_BOOK.md`'s own rule count — same maintenance convention `reporting.aggregation.ALL_BUSINESS_RULE_IDS` already uses |
| `recovery_rule_version` | `len(ALL_RECOVERY_RULES)` (already existed, just counted) |
| `dtd_version` | The two vendored DTD suite names (already existed as directory names) |
| `config_checksum` | **New**: SHA-256 of a deterministic JSON snapshot of `RuntimeConfig`+`FeatureFlagsConfig` — deliberately excludes `AppConfig.environment_settings` (`.env`-sourced, may carry secrets/paths) |
| `generation_timestamp` | **New**: UTC ISO-8601, captured at build time |
| `python_version` / `operating_system` | **New**: `platform.python_version()` / `f"{platform.system()} {platform.release()}"` — no hostname, user, IP, or MAC address |

## Deliberate honesty about what the engine does *not* track

Investigated first, before writing any code, exactly what data already
exists (see this milestone's own investigation). Two things the
milestone asked for have no real signal anywhere in the engine today,
and are represented honestly rather than fabricated:

- **Business Rule "Skipped" state** — no engine concept exists. Always
  reported as an empty list, never a fabricated zero pretending to be
  an observation.
- **Input/Output XML location per Business Rule finding** — no XPath or
  element-location tracking exists for Business Rule findings anywhere
  in the engine (the only real XPath in the system is on DTD validation
  findings, an unrelated signal). Both columns in the Rule Traceability
  table are always left blank, exactly as instructed ("if unavailable,
  leave blank — never invent XPath values").
- **"Business Rules Passed"** is real but limited to the 6-rule subset
  `ConversionReport.business_rules_passed` already tracked before this
  milestone — labeled as such in the report, not implied to cover all
  163 rules.
- **Transformation Summary's per-stage attribution** is derived from
  each Recovery Rule's own already-documented module provenance (every
  `RecoveryRule.description` names its source module) and from the fact
  that all current `GeneratorDiagnostic`s originate in generators — not
  a separately-instrumented per-stage counter, which does not exist.

## Dashboard (additive only — see `Dashboard_Audit_Guide.md`)

New "Migration Audit" page + 2 new download buttons + 2 new filter
params (`validation`, `dtd_result`) on the existing `/api/articles`
route. No existing page redesigned; `App.tsx`'s nav/route list gained
exactly 2 lines plus one new `<Route>`.

## Deviations from the requested scope

- **Rule Traceability's "Input/Output XML location"** columns are
  always blank (see above) — the milestone itself anticipated and
  authorized this ("if unavailable, leave blank; never invent XPath
  values").
- **Business Rule Book/Recovery Rule/DTD "version"** are new,
  manually-maintained constants (no machine-readable version existed
  anywhere to read automatically) — documented as such in code
  comments, following the exact precedent `ALL_BUSINESS_RULE_IDS`
  already set.
- **Transformation Summary's per-stage breakdown** is a best-effort
  categorization built from real rule/finding provenance, not a
  separately-instrumented signal — documented in the module's own
  docstring.
